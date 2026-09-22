from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Attempt, Concept, ConceptAssessment, ConceptGap, Question, Subject, User
from app.services.assessment import assessment_history, rebuild
from app.analytics.scoring import calibration_gap, performance


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    subject = Subject(name="Physics", description="Physics")
    user = User(name="Learner", email="history@test.com", password_hash="unused")
    db.add_all([subject, user]);db.flush()
    first = Concept(subject_id=subject.id, name="Newton's Laws", description="Forces")
    second = Concept(subject_id=subject.id, name="Momentum", description="Momentum")
    db.add_all([first, second]);db.flush()
    return db, user, first, second


def add_attempt(db, user, concept, question_type, correct, when, generated_by=None):
    question = Question(
        concept_id=concept.id, type=question_type, question_text=f"{question_type}?",
        correct_answer="yes", explanation="why",
        question_metadata={"generated_by": generated_by} if generated_by else {},
    )
    db.add(question);db.flush()
    attempt = Attempt(
        user_id=user.id, question_id=question.id, answer="answer", is_correct=correct,
        confidence=3, explanation="because", explanation_score=1 if correct else 0,
        created_at=when,
    )
    db.add(attempt);db.commit()
    return attempt, question


def test_weak_state_is_preserved_and_latest_profile_reflects_improvement():
    db, user, concept, _ = setup_db();start = datetime(2026, 1, 1, 9)
    add_attempt(db, user, concept, "MCQ", True, start)
    add_attempt(db, user, concept, "RECALL", False, start + timedelta(minutes=1))
    rebuild(db, user.id, concept.id)
    weak = assessment_history(db.execute(select(Attempt, Question).join(Question).where(Attempt.user_id == user.id, Question.concept_id == concept.id)).all())
    weak_mastery = weak[-1]["concept_mastery"]
    add_attempt(db, user, concept, "TRANSFER", True, start + timedelta(minutes=2), "tutor")
    profile = rebuild(db, user.id, concept.id)
    history = assessment_history(db.execute(select(Attempt, Question).join(Question).where(Attempt.user_id == user.id, Question.concept_id == concept.id)).all())
    assert len(history) == 3
    assert history[1]["concept_mastery"] == weak_mastery
    assert history[-1]["source"] == "tutor_verification"
    assert profile.concept_mastery == history[-1]["concept_mastery"] > weak_mastery
    assert profile.transfer_score == 1


def test_history_is_chronological_and_concepts_are_isolated():
    db, user, newton, momentum = setup_db();start = datetime(2026, 1, 1, 9)
    late = add_attempt(db, user, newton, "TRANSFER", True, start + timedelta(hours=2))[0]
    early = add_attempt(db, user, newton, "MCQ", False, start)[0]
    add_attempt(db, user, momentum, "MCQ", True, start + timedelta(hours=1))
    newton_rows = db.execute(select(Attempt, Question).join(Question).where(Attempt.user_id == user.id, Question.concept_id == newton.id)).all()
    history = assessment_history(newton_rows)
    assert [point["attempt_id"] for point in history] == [early.id, late.id]
    assert len(history) == 2
    assert all(point["accuracy"] == 0 for point in history)


def test_resolved_gaps_remain_and_reassessment_has_one_point_per_attempt():
    db, user, concept, _ = setup_db();start = datetime(2026, 1, 1, 9)
    add_attempt(db, user, concept, "MCQ", True, start)
    add_attempt(db, user, concept, "RECALL", False, start + timedelta(minutes=1))
    rebuild(db, user.id, concept.id)
    old_gap_ids = set(db.scalars(select(ConceptGap).where(ConceptGap.user_id == user.id)).all())
    add_attempt(db, user, concept, "RECALL", True, start + timedelta(minutes=2))
    rebuild(db, user.id, concept.id)
    gaps = db.scalars(select(ConceptGap).where(ConceptGap.user_id == user.id)).all()
    assert old_gap_ids
    assert all(gap.resolved_at is not None for gap in old_gap_ids)
    assert set(old_gap_ids).issubset(set(gaps))
    rows = db.execute(select(Attempt, Question).join(Question).where(Attempt.user_id == user.id, Question.concept_id == concept.id)).all()
    history = assessment_history(rows)
    assert len(history) == len(rows) == 3
    assert len({point["attempt_id"] for point in history}) == 3
    assert db.scalar(select(ConceptAssessment).where(ConceptAssessment.user_id == user.id)).updated_at == history[-1]["created_at"]


def test_history_replay_uses_authoritative_weighted_performance_and_calibration():
    db, user, concept, _ = setup_db();start = datetime(2026, 1, 1, 9)
    add_attempt(db, user, concept, "MCQ", True, start)
    add_attempt(db, user, concept, "RECALL", False, start + timedelta(minutes=1))
    add_attempt(db, user, concept, "TRANSFER", True, start + timedelta(minutes=2))
    rows = db.execute(select(Attempt, Question).join(Question).where(Attempt.user_id == user.id)).all()
    latest = assessment_history(rows)[-1]
    expected = performance(latest["accuracy"], latest["recall_score"], latest["transfer_score"], latest["explanation_score"])
    assert latest["performance_score"] == expected
    assert latest["calibration_gap"] == calibration_gap(latest["average_confidence"], expected)
