from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Attempt,Question,ConceptAssessment,ConceptGap
from ..analytics.scoring import performance,calibration_gap,mastery,risk
from .gaps import detect
def rebuild(db:Session,user_id:int,concept_id:int):
 rows=db.execute(select(Attempt,Question).join(Question).where(Attempt.user_id==user_id,Question.concept_id==concept_id)).all()
 def avg(t,default=0):
  a=[float(x.is_correct) for x,q in rows if q.type==t];return sum(a)/len(a) if a else default
 acc=sum(float(a.is_correct) for a,q in rows if q.type in ('MCQ','SHORT_ANSWER'))/max(1,sum(q.type in ('MCQ','SHORT_ANSWER') for a,q in rows)); recall=avg('RECALL'); transfer=avg('TRANSFER',avg('CONFLICT')); expl=sum(a.explanation_score for a,q in rows)/max(1,len(rows)); conf=sum(a.confidence for a,q in rows)/max(1,len(rows)); perf=performance(acc,recall,transfer,expl); gap=calibration_gap(conf,perf)
 ca=db.scalar(select(ConceptAssessment).where(ConceptAssessment.user_id==user_id,ConceptAssessment.concept_id==concept_id)) or ConceptAssessment(user_id=user_id,concept_id=concept_id)
 old=ca.concept_mastery if ca.id else None; ca.accuracy,ca.average_confidence,ca.recall_score,ca.transfer_score,ca.explanation_score=acc,conf,recall,transfer,expl;ca.calibration_gap=gap;ca.concept_mastery=mastery(acc,recall,transfer,expl,gap,old);ca.risk_level=risk(ca.concept_mastery,acc,recall,transfer);ca.updated_at=datetime.utcnow();db.add(ca)
 db.query(ConceptGap).filter(ConceptGap.user_id==user_id,ConceptGap.concept_id==concept_id,ConceptGap.resolved_at==None).delete()
 for typ,sev,evidence,action in detect(acc,conf/5,recall,transfer,expl):db.add(ConceptGap(user_id=user_id,concept_id=concept_id,gap_type=typ,severity=sev,evidence=evidence,recommended_action=action))
 db.commit();return ca
