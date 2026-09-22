"""Seed CalibrateAI and provide a safe reset for the two demo accounts."""

import argparse

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    Attempt,
    Concept,
    ConceptAssessment,
    ConceptGap,
    Question,
    Subject,
    TutorTurn,
    User,
)

DEMO_ACCOUNTS = (
    ("Demo Student", "student@demo.com", "student"),
    ("Demo Teacher", "teacher@demo.com", "teacher"),
)
DEMO_PASSWORD = "Demo123!"
SUBJECTS = {
    "Mathematics": ["Linear Equations", "Quadratic Equations", "Discriminant", "Functions", "Derivatives", "Probability", "Polynomials", "Geometry", "Trigonometry", "Statistics"],
    "Physics": ["Newton's Laws", "Force", "Momentum", "Energy", "Work", "Acceleration", "Velocity", "Electric Fields", "Waves", "Thermodynamics"],
    "Chemistry": ["Chemical Equilibrium", "Acids and Bases", "Stoichiometry", "Reaction Rates", "Atomic Structure", "Bonding", "Moles", "Oxidation", "Solutions", "Gas Laws"],
}
QUESTION_TYPES = (
    ("MCQ", .4), ("RECALL", .55), ("CONFLICT", .7), ("TRANSFER", .75),
)


def _question_values(concept: Concept, question_type: str, difficulty: float) -> dict:
    name = concept.name
    if question_type == "MCQ":
        text = "Which formula represents Newton's second law?" if name == "Newton's Laws" else f"Which statement best represents {name}?"
        metadata = {"options": ["A. F = ma", "B. E = mc²", "C. p = mv", "D. W = mg"] if name == "Newton's Laws" else ["A", "B", "C", "D"]}
        return dict(type=question_type, difficulty=difficulty, question_text=text, correct_answer="A", explanation=f"A captures the defining relationship for {name}.", question_metadata=metadata)
    templates = {
        "RECALL": (f"Without choices, explain the key relationship in {name} and why it holds.", "because|relationship", "A complete answer names the relationship and causal mechanism."),
        "CONFLICT": (f"A learner applies {name} unchanged after an important condition changes. Identify what must be reconsidered.", "condition|depends|change", "The changed condition affects whether the original relationship applies."),
        "TRANSFER": (f"Apply {name} in a new real-world context. State your prediction and justify it.", "because|therefore|depends", "Transfer connects the same causal model to a new context."),
    }
    text, answer, explanation = templates[question_type]
    return dict(type=question_type, difficulty=difficulty, question_text=text, correct_answer=answer, explanation=explanation, question_metadata={})


def ensure_curriculum(db: Session) -> None:
    """Fill in missing canonical curriculum rows without duplicating existing rows."""
    for subject_name, concept_names in SUBJECTS.items():
        subject = db.scalar(select(Subject).where(Subject.name == subject_name))
        if subject is None:
            subject = Subject(name=subject_name, description=f"Core {subject_name.lower()} concepts")
            db.add(subject)
            db.flush()
        previous_id = None
        for index, concept_name in enumerate(concept_names):
            concept = db.scalar(select(Concept).where(Concept.subject_id == subject.id, Concept.name == concept_name))
            if concept is None:
                concept = Concept(subject_id=subject.id, name=concept_name, description=f"Understand, explain and transfer {concept_name}.", difficulty=.35 + index * .04, prerequisite_ids=[previous_id] if previous_id else [])
                db.add(concept)
                db.flush()
            previous_id = concept.id
            for question_type, difficulty in QUESTION_TYPES:
                values = _question_values(concept, question_type, difficulty)
                exists = db.scalar(select(Question.id).where(Question.concept_id == concept.id, Question.type == question_type, Question.question_text == values["question_text"]))
                if exists is None:
                    db.add(Question(concept_id=concept.id, **values))


def ensure_demo_users(db: Session) -> dict[str, User]:
    users = {}
    for name, email, role in DEMO_ACCOUNTS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(name=name, email=email, password_hash=hash_password(DEMO_PASSWORD), role=role)
            db.add(user)
            db.flush()
        users[email] = user
    return users


def reset_demo_learning_state(db: Session, users: dict[str, User]) -> None:
    """Delete learning state belonging only to the exact, known demo accounts."""
    demo_user_ids = [user.id for user in users.values()]
    # All learning tables reference users directly. Delete derived state first,
    # followed by its raw attempt evidence, to remain safe if FKs are tightened.
    for model in (ConceptGap, ConceptAssessment, TutorTurn, Attempt):
        db.execute(delete(model).where(model.user_id.in_(demo_user_ids)))


def seed_baseline_evidence(db: Session, student: User) -> None:
    """Retain the original normal-seed behavior; reset mode deliberately skips it."""
    if db.scalar(select(Attempt.id).where(Attempt.user_id == student.id)) is not None:
        return
    from app.services.assessment import rebuild

    concepts = db.scalars(select(Concept).order_by(Concept.id).limit(3)).all()
    for index, concept in enumerate(concepts):
        questions = db.scalars(select(Question).where(Question.concept_id == concept.id).order_by(Question.id)).all()
        values = [(True, 5, .8), (index != 0, 5, .35), (False, 5, .3), (index > 1, 4, .55)]
        for question, (correct, confidence, explanation_score) in zip(questions, values):
            db.add(Attempt(user_id=student.id, question_id=question.id, answer=question.correct_answer.split("|")[0] if correct else "I am not sure", is_correct=correct, confidence=confidence, explanation="The variables are related according to the rule.", explanation_score=explanation_score, response_time_ms=3200))
        db.flush()
        rebuild(db, student.id, concept.id)


def run_seed(*, reset_demo: bool = False, db: Session | None = None) -> None:
    """Seed the database, optionally leaving demo accounts in a clean state."""
    Base.metadata.create_all(engine)
    owns_session = db is None
    session = db or SessionLocal()
    try:
        ensure_curriculum(session)
        users = ensure_demo_users(session)
        session.flush()
        if reset_demo:
            reset_demo_learning_state(session, users)
        else:
            seed_baseline_evidence(session, users["student@demo.com"])
        session.commit()
        subject_count = session.scalar(select(func.count()).select_from(Subject))
        concept_count = session.scalar(select(func.count()).select_from(Concept))
        if reset_demo:
            print("Demo reset complete")
            print("Student: student@demo.com")
            print("Teacher: teacher@demo.com")
            print(f"Subjects: {subject_count}")
            print(f"Concepts: {concept_count}")
            print("Learning evidence reset: yes")
        else:
            question_count = session.scalar(select(func.count()).select_from(Question))
            print(f"Seeded {subject_count} subjects, {concept_count} concepts, {question_count} questions, and demo accounts.")
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-demo", action="store_true", help="clear learning state for only the known demo accounts")
    run_seed(reset_demo=parser.parse_args().reset_demo)
