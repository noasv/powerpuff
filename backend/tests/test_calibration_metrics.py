from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.scoring import calibration_gap, performance
from app.api.routes import assessment_metrics
from app.database import Base
from app.models import Attempt, Concept, ConceptAssessment, Question, Subject, User
from app.services.assessment import rebuild


def metric(confidence, accuracy, recall, transfer, explanation):
    item = SimpleNamespace(
        average_confidence=confidence,
        accuracy=accuracy,
        recall_score=recall,
        transfer_score=transfer,
        explanation_score=explanation,
    )
    return assessment_metrics(item)


def test_gap_is_exactly_confidence_minus_weighted_performance():
    confidence, demonstrated, gap = metric(4.7, .6, .5, .4, .9)
    assert demonstrated == pytest.approx(.35 * .6 + .25 * .5 + .25 * .4 + .15 * .9)
    assert gap == pytest.approx(confidence - demonstrated)


@pytest.mark.parametrize(
    "confidence,evidence,direction",
    [(5, .5, 1), (1, .8, -1), (3, .6, 0)],
)
def test_positive_negative_and_near_zero_gap(confidence, evidence, direction):
    gap = calibration_gap(confidence, performance(evidence, evidence, evidence, evidence))
    assert (gap > 0) - (gap < 0) == direction


def test_rounding_occurs_only_for_display_and_preserves_arithmetic():
    confidence, demonstrated, gap = metric(4.72, .563, .557, .559, .561)
    assert gap == pytest.approx(confidence - demonstrated)
    assert round(gap * 100) == round(confidence * 100) - round(demonstrated * 100)


def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)


def add_attempt(db, user, concept, kind, correct, confidence, explanation=.5):
    question = Question(concept_id=concept.id, type=kind, difficulty=.5, question_text=f"{kind}?", correct_answer="yes", explanation="", question_metadata={})
    db.add(question); db.flush()
    db.add(Attempt(user_id=user.id, question_id=question.id, answer="yes", is_correct=correct, confidence=confidence, explanation="", explanation_score=explanation))
    db.commit()


def test_multiple_attempts_are_preserved_isolated_and_refresh_cached_aggregate():
    db = db_session()
    subject = Subject(name="Math", description="")
    user = User(name="Student", email="student@example.com", password_hash="x", role="student")
    db.add_all([subject, user]); db.flush()
    linear = Concept(subject_id=subject.id, name="Linear Equations", description="", difficulty=.5)
    newton = Concept(subject_id=subject.id, name="Newton's Laws", description="", difficulty=.5)
    db.add_all([linear, newton]); db.commit()

    add_attempt(db, user, linear, "MCQ", True, 5, .8)
    first = rebuild(db, user.id, linear.id)
    first_gap = first.calibration_gap
    add_attempt(db, user, linear, "RECALL", False, 1, .2)
    refreshed = rebuild(db, user.id, linear.id)
    add_attempt(db, user, newton, "MCQ", False, 5, .1)
    isolated = rebuild(db, user.id, newton.id)

    assert len(db.scalars(select(Attempt).where(Attempt.user_id == user.id)).all()) == 3
    assert refreshed.average_confidence == pytest.approx(3)
    assert refreshed.calibration_gap != first_gap
    assert refreshed.calibration_gap == pytest.approx(calibration_gap(refreshed.average_confidence, performance(refreshed.accuracy, refreshed.recall_score, refreshed.transfer_score, refreshed.explanation_score)))
    assert isolated.average_confidence == pytest.approx(5)
    assert isolated.accuracy == 0
    assert refreshed.accuracy == 1


def test_missing_evidence_is_neutral():
    assert metric(0, 0, 0, 0, 0) == (0, 0, 0)
