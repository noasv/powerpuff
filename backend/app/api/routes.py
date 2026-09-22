from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..schemas import *
from ..auth import *
from ..ai.real_provider import provider
from ..services.assessment import assessment_history,rebuild
from ..services.recommendations import rank_recommendations,empty_recommendation
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
def serialize_assessment(x):return {k:getattr(x,k) for k in ('concept_id','accuracy','average_confidence','recall_score','transfer_score','explanation_score','calibration_gap','concept_mastery','risk_level','updated_at')}
@router.get('/student/dashboard')
def student_dashboard(db:Session=Depends(get_db),u=Depends(current_user)):
 rows=db.execute(select(ConceptAssessment,Concept,Subject).join(Concept,Concept.id==ConceptAssessment.concept_id).join(Subject,Subject.id==Concept.subject_id).where(ConceptAssessment.user_id==u.id)).all(); gap_models=db.scalars(select(ConceptGap).where(ConceptGap.user_id==u.id,ConceptGap.resolved_at==None)).all(); concepts={c.id:c for _,c,_ in rows}
 assessments=[serialize_assessment(a)|{'concept_name':c.name} for a,c,s in rows]; ranked=rank_recommendations(rows,gap_models); gaps=sorted(gap_models,key=lambda g:next((i for i,r in enumerate(ranked) if r['concept_id']==g.concept_id),len(ranked))); n=max(1,len(rows));return {'user':UserOut.model_validate(u),'overall':{'confidence':sum(a.average_confidence/5 for a,c,s in rows)/n,'performance':sum((a.accuracy+a.recall_score+a.transfer_score+a.explanation_score)/4 for a,c,s in rows)/n,'calibration_gap':sum(a.calibration_gap for a,c,s in rows)/n,'mastery':sum(a.concept_mastery for a,c,s in rows)/n},'assessments':assessments,'gaps':[{'id':g.id,'concept_id':g.concept_id,'concept_name':concepts[g.concept_id].name,'gap_type':g.gap_type,'severity':g.severity,'evidence':g.evidence,'recommended_action':g.recommended_action} for g in gaps if g.concept_id in concepts],'recommendation':ranked[0] if ranked else empty_recommendation()}
@router.get('/student/concepts')
def student_concepts(db:Session=Depends(get_db),u=Depends(current_user)):return student_dashboard(db,u)['assessments']
@router.get('/student/gaps')
def student_gaps(db:Session=Depends(get_db),u=Depends(current_user)):return student_dashboard(db,u)['gaps']
@router.get('/student/progress')
def student_progress(db:Session=Depends(get_db),u=Depends(current_user)):
 concepts={c.id:c for c in db.scalars(select(Concept)).all()}
 attempts=db.execute(select(Attempt,Question).join(Question).where(Attempt.user_id==u.id).order_by(Attempt.created_at,Attempt.id)).all()
 by_concept={}
 for attempt,question in attempts:by_concept.setdefault(question.concept_id,[]).append((attempt,question))
 history=[]
 for concept_id,rows in by_concept.items():
  concept=concepts.get(concept_id)
  if not concept:continue
  history.extend(point|{'concept_id':concept_id,'concept_name':concept.name} for point in assessment_history(rows))
 history.sort(key=lambda point:(point['created_at'],point['attempt_id']))
 gaps=db.scalars(select(ConceptGap).where(ConceptGap.user_id==u.id).order_by(ConceptGap.created_at,ConceptGap.id)).all()
 return {'history':history,'gaps':[{'id':g.id,'concept_id':g.concept_id,'concept_name':concepts[g.concept_id].name,'gap_type':g.gap_type,'severity':g.severity,'evidence':g.evidence,'recommended_action':g.recommended_action,'created_at':g.created_at,'resolved_at':g.resolved_at} for g in gaps if g.concept_id in concepts]}
@router.post('/ai/{kind}')
async def ai(kind:str,data:TutorRequest|GenerateRequest,db:Session=Depends(get_db),u=Depends(current_user)):
 mapping={'generate-question':'question','analyze-explanation':'analysis','generate-conflict':'conflict','tutor':'tutor'}
 if kind not in mapping:raise HTTPException(404)
 if kind=='tutor':
  if not isinstance(data,TutorRequest):raise HTTPException(422,'Tutor evidence is required')
  concept=db.get(Concept,data.concept_id)
  if not concept:raise HTTPException(404,'Concept not found')
  subject=db.get(Subject,concept.subject_id)
  assessment=db.scalar(select(ConceptAssessment).where(ConceptAssessment.user_id==u.id,ConceptAssessment.concept_id==concept.id))
  gaps=db.scalars(select(ConceptGap).where(ConceptGap.user_id==u.id,ConceptGap.concept_id==concept.id,ConceptGap.resolved_at==None)).all()
  attempts=db.execute(select(Attempt,Question).join(Question).where(Attempt.user_id==u.id,Question.concept_id==concept.id).order_by(Attempt.created_at.desc()).limit(8)).all()
  turns=db.scalars(select(TutorTurn).where(TutorTurn.user_id==u.id,TutorTurn.concept_id==concept.id).order_by(TutorTurn.created_at.desc()).limit(20)).all();turns=list(reversed(turns))
  evidence={'subject':subject.name if subject else '', 'concept':concept.name,'concept_description':concept.description,'latest_response':data.message,
   'assessment':serialize_assessment(assessment) if assessment else None,
   'detected_concept_gaps':[{'type':g.gap_type,'severity':g.severity,'evidence':g.evidence} for g in gaps],
   'previous_attempts':[{'question':q.question_text,'question_type':q.type,'student_answer':a.answer,'correct_answer':q.correct_answer,'correctness':a.is_correct,'confidence':a.confidence,'student_explanation':a.explanation,'explanation_score':a.explanation_score} for a,q in attempts],
   'previous_tutor_turns':[{'student':t.student_message,'tutor':t.tutor_message,'action':t.action,'reasoning_quality':t.reasoning_quality,'verification_task':t.verification_task} for t in turns]}
  result=await provider().generate('tutor',evidence)
  validated=TutorResponse.model_validate(result)
  previous_verification=bool(turns and turns[-1].action=='verify' and turns[-1].verification_task)
  # Completion is an evidence claim, not a turn counter: require a prior transfer task and strong evaluated reasoning.
  if validated.is_complete and not (previous_verification and validated.action=='evaluate_verification' and validated.reasoning_quality=='strong'):
   validated.is_complete=False
  turn=TutorTurn(user_id=u.id,concept_id=concept.id,student_message=data.message,tutor_message=validated.message,action=validated.action,reasoning_quality=validated.reasoning_quality,verification_task=validated.verification_task,is_complete=validated.is_complete,provider_mode=validated.provider_mode);db.add(turn);db.flush()
  if validated.is_complete:
   verification=Question(concept_id=concept.id,type='TRANSFER',difficulty=.75,question_text=turns[-1].verification_task,correct_answer='Demonstrated causal transfer',explanation='Tutor-validated explanation under changed conditions.',question_metadata={'generated_by':'tutor','tutor_turn_id':turn.id})
   db.add(verification);db.flush();db.add(Attempt(user_id=u.id,question_id=verification.id,answer=data.message,is_correct=True,confidence=3,response_time_ms=0,explanation=data.message,explanation_score=1.0));db.commit();rebuild(db,u.id,concept.id)
  else:db.commit()
  return validated.model_dump()
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
