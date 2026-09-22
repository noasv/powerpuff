from app.database import Base,engine,SessionLocal
from app.models import *
from app.auth import hash_password
from sqlalchemy import select
Base.metadata.create_all(engine);db=SessionLocal()
subjects={
'Mathematics':['Linear Equations','Quadratic Equations','Discriminant','Functions','Derivatives','Probability','Polynomials','Geometry','Trigonometry','Statistics'],
'Physics':["Newton's Laws",'Force','Momentum','Energy','Work','Acceleration','Velocity','Electric Fields','Waves','Thermodynamics'],
'Chemistry':['Chemical Equilibrium','Acids and Bases','Stoichiometry','Reaction Rates','Atomic Structure','Bonding','Moles','Oxidation','Solutions','Gas Laws']}
if not db.scalar(select(Subject)):
 for sn,names in subjects.items():
  s=Subject(name=sn,description=f'Core {sn.lower()} concepts');db.add(s);db.flush(); previous=None
  for i,name in enumerate(names):
   c=Concept(subject_id=s.id,name=name,description=f'Understand, explain and transfer {name}.',difficulty=.35+i*.04,prerequisite_ids=[previous] if previous else []);db.add(c);db.flush();previous=c.id
   base=("Which formula represents Newton's second law?" if name=="Newton's Laws" else f'Which statement best represents {name}?')
   correct='A'; options=['A','B','C','D'];db.add(Question(concept_id=c.id,type='MCQ',difficulty=.4,question_text=base,correct_answer=correct,explanation=f'A captures the defining relationship for {name}.',question_metadata={'options':options if name!="Newton's Laws" else ['A. F = ma','B. E = mc²','C. p = mv','D. W = mg']}))
   db.add(Question(concept_id=c.id,type='RECALL',difficulty=.55,question_text=f'Without choices, explain the key relationship in {name} and why it holds.',correct_answer='because|relationship',explanation='A complete answer names the relationship and causal mechanism.',question_metadata={}))
   db.add(Question(concept_id=c.id,type='CONFLICT',difficulty=.7,question_text=f'A learner applies {name} unchanged after an important condition changes. Identify what must be reconsidered.',correct_answer='condition|depends|change',explanation='The changed condition affects whether the original relationship applies.',question_metadata={}))
   db.add(Question(concept_id=c.id,type='TRANSFER',difficulty=.75,question_text=f'Apply {name} in a new real-world context. State your prediction and justify it.',correct_answer='because|therefore|depends',explanation='Transfer connects the same causal model to a new context.',question_metadata={}))
for name,email,role in [('Demo Student','student@demo.com','student'),('Demo Teacher','teacher@demo.com','teacher')]:
 if not db.scalar(select(User).where(User.email==email)):db.add(User(name=name,email=email,password_hash=hash_password('Demo123!'),role=role))
db.commit()
student=db.scalar(select(User).where(User.email=='student@demo.com')); concepts=db.scalars(select(Concept).limit(3)).all()
if not db.scalar(select(Attempt).where(Attempt.user_id==student.id)):
 from app.services.assessment import rebuild
 for idx,c in enumerate(concepts):
  qs=db.scalars(select(Question).where(Question.concept_id==c.id)).all()
  vals=[(True,5,.8),(idx!=0,5,.35),(False,5,.3),(idx>1,4,.55)]
  for q,(ok,conf,es) in zip(qs,vals):db.add(Attempt(user_id=student.id,question_id=q.id,answer=q.correct_answer.split('|')[0] if ok else 'I am not sure',is_correct=ok,confidence=conf,explanation='The variables are related according to the rule.',explanation_score=es,response_time_ms=3200))
  db.commit();rebuild(db,student.id,c.id)
print('Seeded 3 subjects, 30 concepts, 120 questions, and demo accounts.')
