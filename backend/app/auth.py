from datetime import datetime,timedelta,timezone
import jwt
from pwdlib import PasswordHash
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .config.settings import settings
hasher=PasswordHash.recommended(); bearer=HTTPBearer()
def hash_password(v):return hasher.hash(v)
def verify(v,h):return hasher.verify(v,h)
def token(user):return jwt.encode({'sub':str(user.id),'role':user.role,'exp':datetime.now(timezone.utc)+timedelta(hours=24)},settings.jwt_secret,algorithm='HS256')
def current_user(c:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
 try: uid=int(jwt.decode(c.credentials,settings.jwt_secret,algorithms=['HS256'])['sub'])
 except Exception: raise HTTPException(401,'Invalid or expired session')
 user=db.get(User,uid)
 if not user:raise HTTPException(401,'Account no longer exists')
 return user
def teacher(user=Depends(current_user)):
 if user.role not in ('teacher','admin'):raise HTTPException(403,'Teacher access required')
 return user
