from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..schemas import *
from ..auth import *
from ..ai.real_provider import provider
from ..services.assessment import rebuild
router=APIRouter(prefix='/api')
@router.post('/auth/register',response_model=Token)
def register(data:UserCreate,db:Session=Depends(get_db)):
 if db.scalar(select(User).where(User.email==data.email.lower())):raise HTTPException(409,'Email already registered')
 u=User(name=data.name,email=data.email.lower(),password_hash=hash_password(data.password),role='student');db.add(u);db.commit();db.refresh(u);return Token(access_token=token(u),user=u)
@router.post('/auth/login',response_model=Token)
def login(data:UserLogin,db:Session=Depends(get_db)):
 u=db.scalar(select(User).where(User.email==data.email.lower()))
 if not u or not verify(data.password,u.password_hash):raise HTTPException(401,'Invalid email or password')
 return Token(access_token=token(u),user=u)
@router.get('/auth/me',response_model=UserOut)
def me(u=Depends(current_user)):return u
@router.delete('/auth/me',status_code=204)
def delete_me(u=Depends(current_user),db:Session=Depends(get_db)):
 for model in (ConceptGap,ConceptAssessment,Attempt):db.query(model).filter(model.user_id==u.id).delete()
 db.delete(u);db.commit()
@router.get('/subjects')
def subjects(db:Session=Depends(get_db),u=Depends(current_user)):return db.scalars(select(Subject)).all()
@router.get('/subjects/{sid}/concepts')
def concepts(sid:int,db:Session=Depends(get_db),u=Depends(current_user)):return db.scalars(select(Concept).where(Concept.subject_id==sid)).all()
@router.get('/questions/next')
def next_question(concept_id:int,type:str|None=None,db:Session=Depends(get_db),u=Depends(current_user)):
 q=select(Question).where(Question.concept_id==concept_id)
 if type:q=q.where(Question.type==type)
 item=db.scalar(q.order_by(Question.difficulty))
 if not item:raise HTTPException(404,'No task is available for this concept')
 return {'id':item.id,'concept_id':item.concept_id,'type':item.type,'difficulty':item.difficulty,'question_text':item.question_text,'metadata':item.question_metadata,'why':{'MCQ':'Begin with recognition, then test recall and transfer.','RECALL':'Produce the idea without answer choices.','CONFLICT':'Test whether your model remains stable under changed conditions.','TRANSFER':'Apply the same model in a new context.'}.get(item.type,'Diagnose understanding.')}
@router.post('/attempts')
async def attempt(data:AttemptCreate,db:Session=Depends(get_db),u=Depends(current_user)):
 q=db.get(Question,data.question_id)
 if not q:raise HTTPException(404,'Question not found')
 analysis=await provider().generate('analysis',{'explanation':data.explanation,'answer':data.answer}); correct=data.answer.strip().lower() in [x.strip().lower() for x in q.correct_answer.split('|')]
 a=Attempt(user_id=u.id,question_id=q.id,answer=data.answer,is_correct=correct,confidence=data.confidence,response_time_ms=data.response_time_ms,explanation=data.explanation,explanation_score=analysis['overall_score'],changed_answer_count=data.changed_answer_count);db.add(a);db.commit();db.refresh(a);ca=rebuild(db,u.id,q.concept_id)
 sequence={'MCQ':'RECALL','SHORT_ANSWER':'RECALL','RECALL':'CONFLICT' if not correct else 'TRANSFER','CONFLICT':'TRANSFER','TRANSFER':'COMPLETE'}
 return {'id':a.id,'is_correct':correct,'analysis':analysis,'next_type':sequence.get(q.type,'COMPLETE'),'assessment':serialize_assessment(ca),'ai_mode':'real' if __import__('app.config.settings',fromlist=['settings']).settings.ai_api_key else 'demo'}
@router.post('/attempts/{aid}/explain')
async def explain(aid:int,data:ExplainRequest,db:Session=Depends(get_db),u=Depends(current_user)):
 a=db.get(Attempt,aid)
 if not a or a.user_id!=u.id:raise HTTPException(404,'Attempt not found')
 result=await provider().generate('analysis',{'explanation':data.explanation});a.explanation=data.explanation;a.explanation_score=result['overall_score'];db.commit();rebuild(db,u.id,db.get(Question,a.question_id).concept_id);return result
@router.post('/assessments/{cid}/{kind}')
async def generated(cid:int,kind:str,db:Session=Depends(get_db),u=Depends(current_user)):
 if kind not in ('recall','conflict'):raise HTTPException(404)
 return await provider().generate(kind if kind=='conflict' else 'question',{'concept_id':cid,'difficulty':.65})
def serialize_assessment(x):return {k:getattr(x,k) for k in ('concept_id','accuracy','average_confidence','recall_score','transfer_score','explanation_score','calibration_gap','concept_mastery','risk_level')}
@router.get('/student/dashboard')
def student_dashboard(db:Session=Depends(get_db),u=Depends(current_user)):
 rows=db.execute(select(ConceptAssessment,Concept).join(Concept).where(ConceptAssessment.user_id==u.id)).all(); gaps=db.execute(select(ConceptGap,Concept).join(Concept).where(ConceptGap.user_id==u.id,ConceptGap.resolved_at==None)).all()
 assessments=[serialize_assessment(a)|{'concept_name':c.name} for a,c in rows]; n=max(1,len(rows));return {'user':UserOut.model_validate(u),'overall':{'confidence':sum(a.average_confidence/5 for a,c in rows)/n,'performance':sum((a.accuracy+a.recall_score+a.transfer_score+a.explanation_score)/4 for a,c in rows)/n,'calibration_gap':sum(a.calibration_gap for a,c in rows)/n,'mastery':sum(a.concept_mastery for a,c in rows)/n},'assessments':assessments,'gaps':[{'id':g.id,'concept_id':g.concept_id,'concept_name':c.name,'gap_type':g.gap_type,'severity':g.severity,'evidence':g.evidence,'recommended_action':g.recommended_action} for g,c in gaps],'recommendation':('Practice '+gaps[0][1].name+' with guided recall') if gaps else 'Start a diagnostic to calibrate your understanding.'}
@router.get('/student/concepts')
def student_concepts(db:Session=Depends(get_db),u=Depends(current_user)):return student_dashboard(db,u)['assessments']
@router.get('/student/gaps')
def student_gaps(db:Session=Depends(get_db),u=Depends(current_user)):return student_dashboard(db,u)['gaps']
@router.post('/ai/{kind}')
async def ai(kind:str,data:TutorRequest|GenerateRequest,u=Depends(current_user)):
 mapping={'generate-question':'question','analyze-explanation':'analysis','generate-conflict':'conflict','tutor':'tutor'}
 if kind not in mapping:raise HTTPException(404)
 return await provider().generate(mapping[kind],data.model_dump())
@router.get('/teacher/dashboard')
def teacher_dashboard(db:Session=Depends(get_db),u=Depends(teacher)):
 students=db.scalars(select(User).where(User.role=='student')).all(); rows=db.execute(select(ConceptAssessment,Concept,User).join(Concept).join(User,User.id==ConceptAssessment.user_id)).all();
 concepts={}
 for a,c,s in rows:
  x=concepts.setdefault(c.name,{'concept_id':c.id,'concept':c.name,'students':0,'accuracy':0,'confidence':0,'recall':0,'transfer':0,'calibration_gap':0,'risk':'STABLE'});x['students']+=1
  for key,val in [('accuracy',a.accuracy),('confidence',a.average_confidence/5),('recall',a.recall_score),('transfer',a.transfer_score),('calibration_gap',a.calibration_gap)]:x[key]+=val
  if a.risk_level in ('AT RISK','FRAGILE'):x['risk']=a.risk_level
 for x in concepts.values():
  for k in ('accuracy','confidence','recall','transfer','calibration_gap'):x[k]/=x['students']
 return {'overview':{'students':len(students),'average_mastery':sum(a.concept_mastery for a,c,s in rows)/max(1,len(rows)),'average_calibration':sum(abs(a.calibration_gap) for a,c,s in rows)/max(1,len(rows)),'at_risk_concepts':sum(x['risk']!='STABLE' for x in concepts.values())},'concepts':list(concepts.values()),'students':[{'id':s.id,'name':s.name,'email':s.email,'mastery':sum(a.concept_mastery for a,c,u2 in rows if u2.id==s.id)/max(1,sum(u2.id==s.id for a,c,u2 in rows))} for s in students],'recommendation':'Use recall plus changed-condition transfer activities for fragile concepts.'}
@router.get('/teacher/students')
def students(db:Session=Depends(get_db),u=Depends(teacher)):return db.scalars(select(User).where(User.role=='student')).all()
@router.get('/teacher/concepts')
def teacher_concepts(db:Session=Depends(get_db),u=Depends(teacher)):return teacher_dashboard(db,u)['concepts']
@router.get('/teacher/students/{uid}')
def student_detail(uid:int,db:Session=Depends(get_db),u=Depends(teacher)):
 s=db.get(User,uid)
 if not s:raise HTTPException(404,'Student not found')
 return student_dashboard(db,s)
