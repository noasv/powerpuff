from pydantic import BaseModel,EmailStr,Field,ConfigDict
class UserCreate(BaseModel): name:str=Field(min_length=2,max_length=100); email:EmailStr; password:str=Field(min_length=8,max_length=128)
class UserLogin(BaseModel): email:EmailStr; password:str
class UserOut(BaseModel): model_config=ConfigDict(from_attributes=True); id:int; name:str; email:str; role:str
class Token(BaseModel): access_token:str; token_type:str='bearer'; user:UserOut
class AttemptCreate(BaseModel): question_id:int; answer:str=Field(min_length=1,max_length=4000); confidence:int=Field(ge=1,le=5); explanation:str=Field(default='',max_length=5000); response_time_ms:int=Field(default=0,ge=0); changed_answer_count:int=Field(default=0,ge=0)
class ExplainRequest(BaseModel): explanation:str=Field(min_length=2,max_length=5000)
class TutorRequest(BaseModel): concept_id:int; message:str=Field(min_length=1,max_length=3000); step:int=Field(default=1,ge=1,le=8)
class GenerateRequest(BaseModel): concept_id:int; difficulty:float=Field(default=.5,ge=0,le=1)
