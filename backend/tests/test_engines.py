from app.analytics.scoring import performance,calibration_gap,mastery,risk
from app.services.adaptive import next_action
from app.services.gaps import detect
from app.ai.mock_provider import MockAIProvider
from app.ai.real_provider import RealAIProvider
import pytest,asyncio,httpx
def test_calibration_large_positive_gap():
 score=performance(1,.4,.3,.5);assert calibration_gap(5,score)>.35
def test_calibration_near_zero(): assert abs(calibration_gap(3,.6))<.01
def test_mastery_not_accuracy(): assert mastery(1,.2,.2,.3,.4)<.7
def test_risk_classification():
 assert risk(.85,.9,.8,.8)=='MASTERED';assert risk(.55,.9,.3,.3)=='FRAGILE'
@pytest.mark.parametrize('args,expected',[((True,5,.4,None),'RECALL'),((True,5,.8,.4),'CONFLICT'),((False,5,None,None),'CONFLICT'),((False,2,None,None),'FOUNDATION'),((True,5,.8,.9),'INCREASE_DIFFICULTY')])
def test_adaptive(args,expected):assert next_action(*args)==expected
def test_gap_detection_requires_combination():
 assert detect(.9,.9,.3,.3,.3);assert not detect(.9,.6,.8,.8,.8)
def test_mock_provider_structured():
 result=asyncio.run(MockAIProvider().generate('analysis',{'explanation':'because force and mass have a causal relationship'}));assert 0<=result['overall_score']<=1;assert 'misconceptions' in result

def tutor(payload):return asyncio.run(MockAIProvider().generate('tutor',payload))
def test_different_misconceptions_get_different_tutor_responses():
 constant=tutor({'latest_response':'It always stays the same regardless of mass','concept':'Force'})
 causal=tutor({'latest_response':'The value increases but I cannot say why','concept':'Force'})
 assert constant['misconception']!=causal['misconception'];assert constant['message']!=causal['message']
def test_tutor_does_not_reveal_answer_or_complete_by_step():
 result=tutor({'latest_response':'I do not know','step':999,'correct_answer':'SECRET'})
 assert 'SECRET' not in result['message'];assert result['should_reveal_explanation'] is False;assert result['is_complete'] is False
def test_learner_response_changes_next_action_and_verification_precedes_completion():
 weak=tutor({'latest_response':'not sure','concept':'Acceleration','previous_tutor_turns':[]})
 strong=tutor({'latest_response':'It decreases because the same force is spread across more mass, therefore acceleration depends on mass.','concept':'Acceleration','previous_tutor_turns':[]})
 assert weak['action']=='diagnose';assert strong['action']=='verify';assert not strong['is_complete'];assert strong['verification_task']
 verified=tutor({'latest_response':'It changes because the new condition causes a different relationship and therefore a different outcome.','previous_tutor_turns':[{'action':'verify'}]})
 assert verified['action']=='evaluate_verification';assert verified['is_complete']

def test_real_provider_repairs_then_falls_back_on_malformed_output(monkeypatch):
 class Response:
  def raise_for_status(self):pass
  def json(self):return {'choices':[{'message':{'content':'not-json'}}]}
 class Client:
  def __init__(self,*a,**k):self.calls=0
  async def __aenter__(self):return self
  async def __aexit__(self,*a):pass
  async def post(self,*a,**k):self.calls+=1;return Response()
 monkeypatch.setattr('app.ai.real_provider.httpx.AsyncClient',Client)
 result=asyncio.run(RealAIProvider().generate('tutor',{'latest_response':'I do not know'}))
 assert result['provider_mode']=='demo';assert result['message'];assert result['is_complete'] is False

def test_frontend_never_references_backend_api_secret():
 from pathlib import Path
 frontend=Path(__file__).parents[2]/'frontend'/'src'
 assert all('AI_API_KEY' not in path.read_text() for path in frontend.rglob('*') if path.is_file())

def test_real_provider_retries_then_falls_back_on_network_failure(monkeypatch):
 calls={'count':0}

 class Client:
  def __init__(self,*a,**k):pass
  async def __aenter__(self):return self
  async def __aexit__(self,*a):pass
  async def post(self,*a,**k):
   calls['count']+=1
   raise httpx.ConnectError("simulated network failure")

 monkeypatch.setattr('app.ai.real_provider.httpx.AsyncClient',Client)

 result=asyncio.run(RealAIProvider().generate(
  'tutor',
  {'latest_response':'I do not know'}
 ))

 assert calls['count']==2
 assert result['provider_mode']=='demo'
 assert result['message']
 assert result['is_complete'] is False
