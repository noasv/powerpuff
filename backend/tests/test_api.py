import os
os.environ['DATABASE_URL']='sqlite:///./test_calibrate.db'
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base,engine
from app.models import User,Subject,Concept,ConceptAssessment,ConceptGap,Question,Attempt,TutorTurn
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

def remediation_setup(client):
 token=client.post('/api/auth/register',json={'name':'Learner','email':'learner@test.com','password':'Password1!'}).json()['access_token'];headers={'Authorization':f'Bearer {token}'}
 with Session(engine) as db:
  physics=Subject(name='Physics',description='Physics');math=Subject(name='Mathematics',description='Math');db.add_all([physics,math]);db.flush()
  newton=Concept(subject_id=physics.id,name="Newton's Laws",description='Forces and motion');linear=Concept(subject_id=math.id,name='Linear Equations',description='Solve equations');db.add_all([newton,linear]);db.flush()
  db.add_all([ConceptAssessment(user_id=2,concept_id=newton.id,accuracy=.8,average_confidence=4,recall_score=.7,transfer_score=.1,explanation_score=.7,calibration_gap=.2,concept_mastery=.45,risk_level='FRAGILE'),ConceptAssessment(user_id=2,concept_id=linear.id,accuracy=.9,average_confidence=4,recall_score=.9,transfer_score=.9,explanation_score=.9,calibration_gap=0,concept_mastery=.9,risk_level='MASTERED')]);db.flush()
  gap=ConceptGap(user_id=2,concept_id=newton.id,gap_type='TRANSFER_FAILURE',severity=.85,evidence={'transfer':.1},recommended_action='Practice changed conditions.');db.add(gap)
  old=Question(concept_id=linear.id,type='RECALL',difficulty=.5,question_text='Old linear evidence',correct_answer='x',explanation='linear',question_metadata={});db.add(old);db.flush();db.add(Attempt(user_id=2,question_id=old.id,answer='old algebra answer',is_correct=False,confidence=5,response_time_ms=1,explanation='linear equation reasoning',explanation_score=.1));db.commit();return headers,newton.id,gap.id

def test_tutor_context_is_newtons_laws_and_excludes_linear_evidence(client):
 headers,concept_id,gap_id=remediation_setup(client)
 dashboard=client.get('/api/student/dashboard',headers=headers).json();recommendation=dashboard['recommendation']
 assert recommendation['action_type']=='tutor_remediation' and recommendation['concept_id']==concept_id and recommendation['gap_id']==gap_id
 context=client.get(f'/api/student/tutor-context?concept_id={concept_id}&gap_id={gap_id}',headers=headers).json()
 assert context['subject']=='Physics' and context['concept']=="Newton's Laws"
 assert context['assessment']['transfer_score']==.1 and context['active_concept_gaps'][0]['id']==gap_id
 assert context['previous_attempts']==[]
 assert 'Linear Equations' not in str(context) and 'old algebra answer' not in str(context)

def test_successful_tutor_verification_rebuilds_evidence_and_recommendation(client):
 headers,concept_id,gap_id=remediation_setup(client)
 first=client.post('/api/ai/tutor',headers=headers,json={'concept_id':concept_id,'gap_id':gap_id,'message':'Because force causes acceleration, the result depends on mass changing.'});assert first.json()['action']=='verify'
 second=client.post('/api/ai/tutor',headers=headers,json={'concept_id':concept_id,'gap_id':gap_id,'message':'Because the changed mass affects acceleration, therefore the same force causes a different result.'});assert second.json()['is_complete'] is True
 dashboard=client.get('/api/student/dashboard',headers=headers).json()
 newton=next(a for a in dashboard['assessments'] if a['concept_id']==concept_id)
 assert newton['transfer_score']==1
 assert not any(g['concept_id']==concept_id for g in dashboard['gaps'])
 assert dashboard['recommendation']['action_type']=='assessment'


def test_dashboard_uses_weighted_performance_and_matching_calibration_population(client):
 headers,_,_=remediation_setup(client)
 dashboard=client.get('/api/student/dashboard',headers=headers).json()
 newton=next(a for a in dashboard['assessments'] if a['concept_name']=="Newton's Laws")
 assert newton['performance']==pytest.approx(.585)
 assert dashboard['overall']['confidence']==pytest.approx(.8)
 assert dashboard['overall']['performance']==pytest.approx(.7425)
 assert dashboard['overall']['calibration_gap']==pytest.approx(.0575)
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


def test_teacher_can_view_selected_student_evidence(client):
    learner = client.post(
        '/api/auth/register',
        json={
            'name': 'Selected Learner',
            'email': 'selected@test.com',
            'password': 'Password1!'
        }
    ).json()

    teacher_token = client.post(
        '/api/auth/login',
        json={
            'email': 'teacher@test.com',
            'password': 'Password1!'
        }
    ).json()['access_token']

    with Session(engine) as db:
        student = db.query(User).filter(User.email == 'selected@test.com').one()
        concept = Concept(
            subject_id=db.query(Subject).first().id
            if db.query(Subject).first()
            else 1,
            name='Teacher Detail Concept',
            description='Evidence visible to teacher'
        )

        if not db.query(Subject).first():
            subject = Subject(name='Science', description='Science')
            db.add(subject)
            db.flush()
            concept.subject_id = subject.id

        db.add(concept)
        db.flush()

        db.add(ConceptAssessment(
            user_id=student.id,
            concept_id=concept.id,
            accuracy=.8,
            average_confidence=4,
            recall_score=.6,
            transfer_score=.4,
            explanation_score=.7,
            calibration_gap=0,
            concept_mastery=.65,
            risk_level='FRAGILE'
        ))
        db.commit()
        student_id = student.id

    response = client.get(
        f'/api/teacher/students/{student_id}',
        headers={'Authorization': f'Bearer {teacher_token}'}
    )

    assert response.status_code == 200
    data = response.json()

    assert data['user']['id'] == student_id
    assert data['user']['name'] == 'Selected Learner'
    assert len(data['assessments']) == 1

    assessment = data['assessments'][0]
    assert assessment['concept_name'] == 'Teacher Detail Concept'
    assert assessment['performance'] == pytest.approx(
        .35 * .8 + .25 * .6 + .25 * .4 + .15 * .7
    )
    assert assessment['calibration_gap'] == pytest.approx(
        .8 - assessment['performance']
    )
