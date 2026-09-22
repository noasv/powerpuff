"""Deterministic, concept-scoped recommendation ranking."""
from collections import defaultdict
from datetime import datetime, timezone

from ..analytics.scoring import performance


# Keep ranking policy in one place so changes can be reviewed and tested.
STATE_PRIORITY = {"AT_RISK": 70, "FRAGILE": 65, "OVERCONFIDENT": 55, "UNDERCONFIDENT": 30, "STABLE": 0, "MASTERED": -45, "UNKNOWN": 10}
WEIGHTS = {"gap_severity": 35, "calibration": 20, "recall_weakness": 18, "transfer_weakness": 18, "explanation_weakness": 12, "mastery_weakness": 15, "latest_unresolved_continuity": 20}
RECENCY_BOOSTS = ((1, 25), (7, 18), (30, 10), (90, 4))
WEAK_EVIDENCE = .55
CALIBRATION_MISMATCH = .20


def _state(value: str) -> str:
    return (value or "UNKNOWN").strip().upper().replace(" ", "_")


def _age_days(value: datetime, now: datetime) -> float:
    # SQLite commonly returns naive UTC timestamps.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, (now - value).total_seconds() / 86400)


def _recency(age_days: float) -> float:
    return next((boost for days, boost in RECENCY_BOOSTS if age_days <= days), 0)


def _intervention(assessment, concept_name: str) -> tuple[str, str, str]:
    demonstrated = performance(assessment.accuracy, assessment.recall_score, assessment.transfer_score, assessment.explanation_score)
    confidence = assessment.average_confidence / 5
    if confidence - demonstrated >= CALIBRATION_MISMATCH and demonstrated <= WEAK_EVIDENCE:
        return (f"Calibrate your {concept_name} model by predicting, explaining, then checking the result.", "Your recent assessment showed strong confidence but weak demonstrated evidence.", "calibration_intervention")
    if assessment.recall_score < WEAK_EVIDENCE and assessment.recall_score <= min(assessment.transfer_score, assessment.explanation_score):
        return (f"Practice {concept_name} with guided recall before reviewing examples.", "Your recent assessment showed that recalling the idea without prompts was difficult.", "guided_recall")
    if assessment.transfer_score < WEAK_EVIDENCE and assessment.transfer_score <= assessment.explanation_score:
        return (f"Apply {concept_name} in a changed-condition problem.", "You showed more understanding than you could apply when the conditions changed.", "transfer_practice")
    if assessment.explanation_score < WEAK_EVIDENCE:
        return (f"Reconstruct the reasoning behind {concept_name} step by step.", "Your answer needs a clearer explanation of the relationships involved.", "reasoning_reconstruction")
    if assessment.calibration_gap <= -CALIBRATION_MISMATCH:
        return (f"Verify your {concept_name} reasoning with one challenging example.", "Your evidence is stronger than your confidence suggests.", "verification")
    return (f"Strengthen your {concept_name} model with a counterexample.", "This concept still has an unresolved learning gap.", "misconception_repair")


def rank_recommendations(rows, gaps, now: datetime | None = None) -> list[dict]:
    """Rank assessments using only evidence attached to each assessment's concept."""
    if not rows:
        return []
    now = now or datetime.now(timezone.utc)
    active_by_concept = defaultdict(list)
    for gap in gaps:
        if gap.resolved_at is None:
            active_by_concept[gap.concept_id].append(gap)
    latest = max(assessment.updated_at for assessment, _, _ in rows)
    ranked = []
    for assessment, concept, subject in rows:
        active = active_by_concept[concept.id]
        severity = max((gap.severity for gap in active), default=0)
        state = _state(assessment.risk_level)
        age = _age_days(assessment.updated_at, now)
        unresolved = bool(active) or state in {"AT_RISK", "FRAGILE", "OVERCONFIDENT", "UNDERCONFIDENT"}
        # A resolved stable/mastered concept remains in history and the concept map,
        # but should not displace an actionable concept (or invent more practice).
        if not unresolved:
            continue
        score = (STATE_PRIORITY.get(state, STATE_PRIORITY["UNKNOWN"])
                 + WEIGHTS["gap_severity"] * severity
                 + WEIGHTS["calibration"] * abs(assessment.calibration_gap)
                 + WEIGHTS["recall_weakness"] * (1 - assessment.recall_score)
                 + WEIGHTS["transfer_weakness"] * (1 - assessment.transfer_score)
                 + WEIGHTS["explanation_weakness"] * (1 - assessment.explanation_score)
                 + WEIGHTS["mastery_weakness"] * (1 - assessment.concept_mastery)
                 + _recency(age)
                 + (WEIGHTS["latest_unresolved_continuity"] if assessment.updated_at == latest and unresolved else 0))
        action, reason, intervention = _intervention(assessment, concept.name)
        target_gap = max(active, key=lambda gap: gap.severity, default=None)
        ranked.append({"concept_id": concept.id, "concept_name": concept.name, "subject_name": subject.name,
                       "gap_id": getattr(target_gap, "id", None), "action_type": "tutor_remediation" if target_gap else "assessment",
                       "intervention": intervention if target_gap else "diagnostic_reassessment",
                       "recommended_action": action, "reason": reason, "priority_score": round(score, 2)})
    return sorted(ranked, key=lambda item: (-item["priority_score"], item["concept_id"]))


def empty_recommendation() -> dict:
    return {"concept_id": None, "concept_name": None, "subject_name": None, "gap_id": None,
            "action_type": "assessment", "intervention": "diagnostic",
            "recommended_action": "Start a diagnostic to calibrate your understanding.", "reason": "Complete an assessment to generate an evidence-based next step.", "priority_score": 0}
