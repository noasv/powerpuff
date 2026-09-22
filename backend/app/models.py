from datetime import datetime
from sqlalchemy import String,Float,Integer,Boolean,DateTime,ForeignKey,Text,JSON
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class User(Base):
 __tablename__="users"; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(100)); email:Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash:Mapped[str]; role:Mapped[str]=mapped_column(default="student"); created_at:Mapped[datetime]=mapped_column(default=datetime.utcnow)
class Subject(Base):
 __tablename__="subjects"; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(unique=True); description:Mapped[str]=mapped_column(Text)
class Concept(Base):
 __tablename__="concepts"; id:Mapped[int]=mapped_column(primary_key=True); subject_id:Mapped[int]=mapped_column(ForeignKey("subjects.id")); name:Mapped[str]; description:Mapped[str]=mapped_column(Text); difficulty:Mapped[float]=mapped_column(default=.5); prerequisite_ids:Mapped[list]=mapped_column(JSON,default=list)
class Question(Base):
 __tablename__="questions"; id:Mapped[int]=mapped_column(primary_key=True); concept_id:Mapped[int]=mapped_column(ForeignKey("concepts.id")); type:Mapped[str]; difficulty:Mapped[float]=mapped_column(default=.5); question_text:Mapped[str]=mapped_column(Text); correct_answer:Mapped[str]; explanation:Mapped[str]=mapped_column(Text); question_metadata:Mapped[dict]=mapped_column(JSON,default=dict); created_at:Mapped[datetime]=mapped_column(default=datetime.utcnow)
class Attempt(Base):
 __tablename__="attempts"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id")); question_id:Mapped[int]=mapped_column(ForeignKey("questions.id")); answer:Mapped[str]=mapped_column(Text); is_correct:Mapped[bool]; confidence:Mapped[int]; response_time_ms:Mapped[int]=mapped_column(default=0); explanation:Mapped[str]=mapped_column(Text,default=""); explanation_score:Mapped[float]=mapped_column(default=0); changed_answer_count:Mapped[int]=mapped_column(default=0); created_at:Mapped[datetime]=mapped_column(default=datetime.utcnow)
class ConceptAssessment(Base):
 __tablename__="concept_assessments"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id")); concept_id:Mapped[int]=mapped_column(ForeignKey("concepts.id")); accuracy:Mapped[float]=mapped_column(default=0); average_confidence:Mapped[float]=mapped_column(default=0); recall_score:Mapped[float]=mapped_column(default=0); transfer_score:Mapped[float]=mapped_column(default=0); explanation_score:Mapped[float]=mapped_column(default=0); calibration_gap:Mapped[float]=mapped_column(default=0); concept_mastery:Mapped[float]=mapped_column(default=0); risk_level:Mapped[str]=mapped_column(default="UNKNOWN"); updated_at:Mapped[datetime]=mapped_column(default=datetime.utcnow,onupdate=datetime.utcnow)
class ConceptGap(Base):
 __tablename__="concept_gaps"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id")); concept_id:Mapped[int]=mapped_column(ForeignKey("concepts.id")); gap_type:Mapped[str]; severity:Mapped[float]; evidence:Mapped[dict]=mapped_column(JSON); recommended_action:Mapped[str]; created_at:Mapped[datetime]=mapped_column(default=datetime.utcnow); resolved_at:Mapped[datetime|None]=mapped_column(nullable=True)
