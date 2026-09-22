from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analytics.scoring import calibration_gap, mastery, performance, risk
from ..models import Attempt, ConceptAssessment, ConceptGap, Question
from .gaps import detect


def _snapshot(rows, historical_mastery=None):
    """Build the concept aggregate represented by an ordered set of attempts."""
    def average(question_type, default=0):
        values = [float(attempt.is_correct) for attempt, question in rows if question.type == question_type]
        return sum(values) / len(values) if values else default

    accuracy_rows = [
        float(attempt.is_correct)
        for attempt, question in rows
        if question.type in ("MCQ", "SHORT_ANSWER")
    ]
    accuracy = sum(accuracy_rows) / max(1, len(accuracy_rows))
    recall = average("RECALL")
    transfer = average("TRANSFER", average("CONFLICT"))
    explanation = sum(attempt.explanation_score for attempt, _ in rows) / max(1, len(rows))
    confidence = sum(attempt.confidence for attempt, _ in rows) / max(1, len(rows))
    gap = calibration_gap(confidence, performance(accuracy, recall, transfer, explanation))
    concept_mastery = mastery(accuracy, recall, transfer, explanation, gap, historical_mastery)
    return {
        "accuracy": accuracy,
        "average_confidence": confidence,
        "recall_score": recall,
        "transfer_score": transfer,
        "explanation_score": explanation,
        "calibration_gap": gap,
        "concept_mastery": concept_mastery,
        "risk_level": risk(concept_mastery, accuracy, recall, transfer),
    }


def assessment_history(rows):
    """Replay immutable attempt evidence into genuine, chronological snapshots."""
    ordered = sorted(rows, key=lambda row: (row[0].created_at, row[0].id or 0))
    history = []
    previous_mastery = None
    for index, (attempt, question) in enumerate(ordered):
        values = _snapshot(ordered[:index + 1], previous_mastery)
        previous_mastery = values["concept_mastery"]
        source = "tutor_verification" if question.question_metadata.get("generated_by") == "tutor" else "assessment"
        history.append(values | {
            "attempt_id": attempt.id,
            "question_type": question.type,
            "source": source,
            "created_at": attempt.created_at,
        })
    return history


def rebuild(db: Session, user_id: int, concept_id: int):
    rows = db.execute(
        select(Attempt, Question)
        .join(Question)
        .where(Attempt.user_id == user_id, Question.concept_id == concept_id)
        .order_by(Attempt.created_at, Attempt.id)
    ).all()
    history = assessment_history(rows)
    values = history[-1]
    assessment = db.scalar(select(ConceptAssessment).where(
        ConceptAssessment.user_id == user_id,
        ConceptAssessment.concept_id == concept_id,
    )) or ConceptAssessment(user_id=user_id, concept_id=concept_id)
    for key in (
        "accuracy", "average_confidence", "recall_score", "transfer_score",
        "explanation_score", "calibration_gap", "concept_mastery", "risk_level",
    ):
        setattr(assessment, key, values[key])
    assessment.updated_at = values["created_at"]
    db.add(assessment)

    # Gaps are event history: close active findings, but never delete them.
    observed_at = values["created_at"] or datetime.utcnow()
    db.query(ConceptGap).filter(
        ConceptGap.user_id == user_id,
        ConceptGap.concept_id == concept_id,
        ConceptGap.resolved_at == None,
    ).update({"resolved_at": observed_at})
    for gap_type, severity, evidence, action in detect(
        values["accuracy"], values["average_confidence"] / 5,
        values["recall_score"], values["transfer_score"], values["explanation_score"],
    ):
        db.add(ConceptGap(
            user_id=user_id, concept_id=concept_id, gap_type=gap_type,
            severity=severity, evidence=evidence, recommended_action=action,
            created_at=observed_at,
        ))
    db.commit()
    return assessment
