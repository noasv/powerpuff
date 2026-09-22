from app.analytics.scoring import performance,calibration_gap,mastery,risk
from app.services.adaptive import next_action
from app.services.gaps import detect
from app.ai.mock_provider import MockAIProvider
import pytest,asyncio
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
