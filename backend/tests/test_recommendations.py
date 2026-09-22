from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.recommendations import rank_recommendations


NOW = datetime(2026, 9, 22, tzinfo=timezone.utc)


def assessment(concept_id, *, days=0, risk="FRAGILE", recall=.3, transfer=.3,
               explanation=.5, accuracy=.8, confidence=4, mastery=.5, gap=.2):
    return SimpleNamespace(
        concept_id=concept_id, updated_at=NOW - timedelta(days=days),
        risk_level=risk, recall_score=recall, transfer_score=transfer,
        explanation_score=explanation, accuracy=accuracy,
        average_confidence=confidence, concept_mastery=mastery,
        calibration_gap=gap,
    )


def concept(concept_id, name):
    return SimpleNamespace(id=concept_id, name=name)


def subject(name):
    return SimpleNamespace(name=name)


def gap(concept_id, severity=.8, resolved=False):
    return SimpleNamespace(
        id=concept_id * 10, concept_id=concept_id, severity=severity,
        resolved_at=NOW if resolved else None,
    )


def row(item, name, subject_name):
    return item, concept(item.concept_id, name), subject(subject_name)


def test_recent_fragile_diagnostic_beats_older_gap():
    linear = assessment(1, days=60, risk="AT RISK", recall=.2, transfer=.3)
    newton = assessment(2, recall=0, transfer=0, explanation=.35, confidence=5, gap=.55)
    ranked = rank_recommendations(
        [row(linear, "Linear Equations", "Mathematics"), row(newton, "Newton's Laws", "Physics")],
        [gap(1, .8), gap(2, .85)], NOW,
    )
    assert ranked[0]["concept_name"] == "Newton's Laws"
    assert ranked[0]["subject_name"] == "Physics"


def test_resolved_recent_gap_allows_older_unresolved_concept_to_return():
    linear = assessment(1, days=30, risk="AT RISK", recall=.1, transfer=.2, mastery=.3)
    newton = assessment(2, risk="MASTERED", recall=.9, transfer=.9, explanation=.9, mastery=.9, gap=0)
    ranked = rank_recommendations(
        [row(linear, "Linear Equations", "Mathematics"), row(newton, "Newton's Laws", "Physics")],
        [gap(1, .9), gap(2, .85, resolved=True)], NOW,
    )
    assert ranked[0]["concept_name"] == "Linear Equations"


def test_recent_mastered_concept_does_not_beat_old_severe_at_risk_concept():
    old = assessment(1, days=45, risk="AT_RISK", recall=0, transfer=0, mastery=.2)
    recent = assessment(2, risk="MASTERED", recall=.95, transfer=.95, explanation=.9, mastery=.92, gap=0)
    ranked = rank_recommendations([row(old, "Fractions", "Math"), row(recent, "Forces", "Physics")], [gap(1, 1)], NOW)
    assert ranked[0]["concept_id"] == 1


def test_recency_breaks_similar_unresolved_severity():
    old = assessment(1, days=40)
    recent = assessment(2)
    ranked = rank_recommendations([row(old, "Old", "Math"), row(recent, "Recent", "Physics")], [gap(1), gap(2)], NOW)
    assert ranked[0]["concept_id"] == 2


def test_concept_evidence_is_isolated_during_ranking():
    linear = assessment(1, days=10)
    newton = assessment(2, recall=.9, transfer=.9, explanation=.9)
    rows = [row(linear, "Linear", "Math"), row(newton, "Newton", "Physics")]
    before = {x["concept_id"]: x for x in rank_recommendations(rows, [gap(1), gap(2)], NOW)}[1]
    newton.recall_score = newton.transfer_score = newton.explanation_score = 0
    after = {x["concept_id"]: x for x in rank_recommendations(rows, [gap(1), gap(2)], NOW)}[1]
    assert before == after


def test_weak_recall_selects_guided_recall():
    item = assessment(1, recall=.1, transfer=.7, explanation=.7, confidence=3, gap=0)
    recommendation = rank_recommendations([row(item, "Momentum", "Physics")], [gap(1)], NOW)[0]
    assert "guided recall" in recommendation["recommended_action"].lower()


def test_weak_transfer_selects_changed_condition_practice():
    item = assessment(1, recall=.8, transfer=.1, explanation=.7, confidence=3, gap=0)
    recommendation = rank_recommendations([row(item, "Momentum", "Physics")], [gap(1)], NOW)[0]
    assert "changed-condition" in recommendation["recommended_action"].lower()


def test_high_confidence_and_weak_evidence_selects_calibration():
    item = assessment(1, recall=.2, transfer=.2, explanation=.3, accuracy=.4, confidence=5, gap=.7)
    recommendation = rank_recommendations([row(item, "Momentum", "Physics")], [gap(1)], NOW)[0]
    assert "calibrate" in recommendation["recommended_action"].lower()
    assert "strong confidence" in recommendation["reason"].lower()


def test_unresolved_newtons_laws_routes_to_tutor_remediation():
    newton = assessment(2, recall=.7, transfer=.1, confidence=3, gap=0)
    recommendation = rank_recommendations([row(newton, "Newton's Laws", "Physics")], [gap(2)], NOW)[0]
    assert recommendation["action_type"] == "tutor_remediation"
    assert recommendation["gap_id"] == 20
    assert recommendation["intervention"] == "transfer_practice"


def test_risk_without_unresolved_gap_routes_to_reassessment():
    newton = assessment(2, risk="FRAGILE")
    recommendation = rank_recommendations([row(newton, "Newton's Laws", "Physics")], [], NOW)[0]
    assert recommendation["action_type"] == "assessment"
    assert recommendation["intervention"] == "diagnostic_reassessment"
