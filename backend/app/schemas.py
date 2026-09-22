from typing import Literal
from pydantic import BaseModel,EmailStr,Field,ConfigDict
class UserCreate(BaseModel): name:str=Field(min_length=2,max_length=100); email:EmailStr; password:str=Field(min_length=8,max_length=128)
class UserLogin(BaseModel): email:EmailStr; password:str
class UserOut(BaseModel): model_config=ConfigDict(from_attributes=True); id:int; name:str; email:str; role:str
class Token(BaseModel): access_token:str; token_type:str='bearer'; user:UserOut
class AttemptCreate(BaseModel): question_id:int; answer:str=Field(min_length=1,max_length=4000); confidence:int=Field(ge=1,le=5); explanation:str=Field(default='',max_length=5000); response_time_ms:int=Field(default=0,ge=0); changed_answer_count:int=Field(default=0,ge=0)
class ExplainRequest(BaseModel): explanation:str=Field(min_length=2,max_length=5000)
class TutorMessage(BaseModel):
    role: Literal['student','tutor']
    content: str = Field(min_length=1,max_length=5000)
class TutorRequest(BaseModel):
    concept_id:int
    message:str=Field(min_length=1,max_length=3000)
    history:list[TutorMessage]=Field(default_factory=list,max_length=40)
class GenerateRequest(BaseModel): concept_id:int; difficulty:float=Field(default=.5,ge=0,le=1)

class TutorResponse(BaseModel):
    message:str=Field(min_length=1,max_length=3000)
    action:Literal['diagnose','question','hint','counterexample','revise','explain','verify','evaluate_verification']
    identified_gap:str=''
    misconception:str=''
    hint_level:int=Field(default=0,ge=0,le=3)
    reasoning_quality:Literal['unknown','weak','developing','strong']='unknown'
    should_reveal_explanation:bool=False
    is_complete:bool=False
    verification_task:str|None=None
    provider_mode:Literal['real','demo']='demo'

class AnalysisResponse(BaseModel):
    concept_understanding:float=Field(ge=0,le=1); causal_reasoning:float=Field(ge=0,le=1); use_of_terms:float=Field(ge=0,le=1); logical_consistency:float=Field(ge=0,le=1); memorized_language:float=Field(ge=0,le=1)
    misconceptions:list[str]=Field(default_factory=list); missing_components:list[str]=Field(default_factory=list); overall_score:float=Field(ge=0,le=1)
class GeneratedQuestionResponse(BaseModel):
    question:str; type:str; concept_id:int; difficulty:float=Field(ge=0,le=1); correct_answer:str; explanation:str; trap_type:str|None=None
