import os
os.environ['DATABASE_URL']='sqlite:///./test_calibrate.db'
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base,engine
from app.models import User
from app.auth import hash_password
from sqlalchemy.orm import Session
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
