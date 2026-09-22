import os
os.environ['DATABASE_URL']='sqlite:///./test_calibrate.db'
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base,engine
from app.models import Attempt,Concept,ConceptAssessment,Question,Subject,TutorTurn,User
from app.auth import hash_password
from sqlalchemy.orm import Session
from sqlalchemy import select
import pytest
@pytest.fixture(autouse=True)
def fresh():
 Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
 with Session(engine) as d:d.add(User(name='Teacher',email='teacher@test.com',password_hash=hash_password('Password1!'),role='teacher'));d.commit()
 yield
@pytest.fixture
def client():return TestClient(app)
def test_register_login_and_dashboard(client):
 r=client.post('/api/auth/register',json={'name':'Learner','email':'learner@test.com','password':'Password1!'});assert r.status_code==200;token=r.json()['access_token'];assert client.get('/api/student/dashboard',headers={'Authorization':f'Bearer {token}'}).status_code==200
 assert client.post('/api/auth/login',json={'email':'learner@test.com','password':'Password1!'}).status_code==200
def test_teacher_authorization(client):
 r=client.post('/api/auth/register',json={'name':'Learner','email':'learner@test.com','password':'Password1!'});token=r.json()['access_token'];assert client.get('/api/teacher/dashboard',headers={'Authorization':f'Bearer {token}'}).status_code==403

def test_tutor_verification_is_attributed_and_preserves_assessment_history(client):
 r=client.post('/api/auth/register',json={'name':'Learner','email':'history@test.com','password':'Password1!'});token=r.json()['access_token'];headers={'Authorization':f'Bearer {token}'}
 with Session(engine) as db:
  user=db.query(User).filter_by(email='history@test.com').one();subject=Subject(name='Physics',description='Physics');db.add(subject);db.flush();concept=Concept(subject_id=subject.id,name="Newton's Laws",description='Forces');db.add(concept);db.flush();question=Question(concept_id=concept.id,type='MCQ',question_text='F=ma?',correct_answer='A',explanation='Force',question_metadata={});db.add(question);db.flush();db.add(Attempt(user_id=user.id,question_id=question.id,answer='B',is_correct=False,confidence=5,explanation='not sure',explanation_score=0));db.commit();uid=user.id;cid=concept.id
 from app.services.assessment import rebuild
 with Session(engine) as db:rebuild(db,uid,cid)
 first=client.post('/api/ai/tutor',headers=headers,json={'concept_id':cid,'message':'It changes because force and mass have a causal relationship, therefore the outcome depends on mass.'});assert first.status_code==200;assert first.json()['action']=='verify'
 second=client.post('/api/ai/tutor',headers=headers,json={'concept_id':cid,'message':'It changes because the new condition causes a different relationship and therefore a different outcome.'});assert second.status_code==200;assert second.json()['is_complete'] is True
 progress=client.get('/api/student/progress',headers=headers);assert progress.status_code==200;history=progress.json()['history']
 assert len(history)==2;assert history[0]['source']=='assessment';assert history[1]['source']=='tutor_verification';assert history[0]['concept_id']==history[1]['concept_id']==cid
 with Session(engine) as db:
  verification=db.execute(select(Attempt,Question).join(Question).where(Attempt.user_id==uid,Question.concept_id==cid).order_by(Attempt.id.desc())).first();turn=db.query(TutorTurn).filter_by(user_id=uid,concept_id=cid,is_complete=True).one();profile=db.query(ConceptAssessment).filter_by(user_id=uid,concept_id=cid).one()
  assert verification[1].question_metadata=={'generated_by':'tutor','tutor_turn_id':turn.id};assert profile.transfer_score==1

def test_demo_reset_is_restricted_and_clears_history(client):
 learner=client.post('/api/auth/register',json={'name':'Learner','email':'regular@test.com','password':'Password1!'}).json()['access_token']
 assert client.post('/api/demo/reset',headers={'Authorization':f'Bearer {learner}'}).status_code==403
 with Session(engine) as db:
  demo=User(name='Demo Student',email='student@demo.com',password_hash=hash_password('Demo123!'));db.add(demo);db.flush();subject=Subject(name='Demo',description='Demo');db.add(subject);db.flush();concept=Concept(subject_id=subject.id,name='Demo concept',description='Demo');db.add(concept);db.flush();question=Question(concept_id=concept.id,type='MCQ',question_text='Demo?',correct_answer='A',explanation='Demo',question_metadata={});db.add(question);db.flush();db.add(Attempt(user_id=demo.id,question_id=question.id,answer='B',is_correct=False,confidence=5,explanation='',explanation_score=0));db.commit();demo_id=demo.id;concept_id=concept.id
 from app.services.assessment import rebuild
 with Session(engine) as db:rebuild(db,demo_id,concept_id)
 token=client.post('/api/auth/login',json={'email':'student@demo.com','password':'Demo123!'}).json()['access_token'];response=client.post('/api/demo/reset',headers={'Authorization':f'Bearer {token}'});assert response.status_code==200
 with Session(engine) as db:assert db.query(Attempt).filter_by(user_id=demo_id).count()==0;assert db.query(ConceptAssessment).filter_by(user_id=demo_id).count()==0
