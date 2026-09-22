import os

os.environ["DATABASE_URL"] = "sqlite:///./test_calibrate.db"

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import hash_password, verify
from app.database import Base, engine
from app.models import Attempt, Concept, ConceptAssessment, ConceptGap, Question, Subject, TutorTurn, User
from seed import DEMO_PASSWORD, run_seed


def _counts(db):
    return tuple(db.scalar(select(func.count()).select_from(model)) for model in (Subject, Concept, Question, User))


def test_demo_reset_is_safe_idempotent_and_preserves_login():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    run_seed(reset_demo=True)

    with Session(engine) as db:
        student = db.scalar(select(User).where(User.email == "student@demo.com"))
        teacher = db.scalar(select(User).where(User.email == "teacher@demo.com"))
        assert verify(DEMO_PASSWORD, student.password_hash)
        assert verify(DEMO_PASSWORD, teacher.password_hash)
        question = db.scalar(select(Question))
        concept = db.scalar(select(Concept))
        real_user = User(name="Real Learner", email="real@example.com", password_hash=hash_password("RealPassword1!"), role="student")
        db.add(real_user)
        db.flush()
        for user in (student, teacher, real_user):
            db.add(Attempt(user_id=user.id, question_id=question.id, answer="test", is_correct=False, confidence=5))
            db.add(ConceptAssessment(user_id=user.id, concept_id=concept.id))
            db.add(ConceptGap(user_id=user.id, concept_id=concept.id, gap_type="test", severity=.5, evidence={}, recommended_action="test"))
            db.add(TutorTurn(user_id=user.id, concept_id=concept.id, student_message="test", tutor_message="test", action="diagnose"))
        db.commit()
        before = _counts(db)
        real_user_id = real_user.id

    run_seed(reset_demo=True)
    run_seed(reset_demo=True)

    with Session(engine) as db:
        assert _counts(db) == before
        demo_ids = list(db.scalars(select(User.id).where(User.email.in_(("student@demo.com", "teacher@demo.com")))))
        for model in (Attempt, ConceptAssessment, ConceptGap, TutorTurn):
            assert db.scalar(select(func.count()).select_from(model).where(model.user_id.in_(demo_ids))) == 0
            assert db.scalar(select(func.count()).select_from(model).where(model.user_id == real_user_id)) == 1
        assert db.get(User, real_user_id).email == "real@example.com"
        assert db.scalar(select(func.count()).select_from(Subject)) == 3
        assert db.scalar(select(func.count()).select_from(Concept)) == 30
        assert db.scalar(select(func.count()).select_from(Question)) == 120
        assert db.connection().exec_driver_sql("PRAGMA foreign_key_check").all() == []
