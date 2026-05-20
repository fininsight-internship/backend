import hashlib
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.db_models import User
from app.core.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: Optional[str] = None

def hash_password(password: str) -> str:
    """가장 안정적이며 의존성 문제 없는 SHA-256 단방향 암호화 해싱"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

@router.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    
    # 1. 중복 사용자 체크
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="이미 존재하는 이메일입니다."
        )
    
    # 2. 비밀번호 암호화 해싱
    hashed = hash_password(req.password)
    
    # 3. 새로운 유저 객체 생성 및 DB 커밋
    new_user = User(
        email=email_clean,
        password_hash=hashed,
        name=req.name.strip() if req.name else None,
        role=req.role.strip() if req.role else None
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"👤 [DB] 신규 회원가입 완료: {new_user.email}")
        return {
            "status": "success",
            "message": "회원가입이 완료되었습니다.",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "role": new_user.role
            }
        }
    except Exception as e:
        db.rollback()
        print(f"❌ 회원가입 DB 저장 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"회원 등록 실패: {str(e)}"
        )

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    
    # 1. 사용자 존재 확인
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )
    
    # 2. 패스워드 일치 확인
    hashed = hash_password(req.password)
    if user.password_hash != hashed:
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )
        
    print(f"🔑 [DB] 로그인 성공: {user.email}")
    return {
        "status": "success",
        "message": "로그인이 성공적으로 완료되었습니다.",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }

class UserUpdateModel(BaseModel):
    name: Optional[str] = None
    eng_name: Optional[str] = None
    birth_date: Optional[str] = None
    role: Optional[str] = None

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name or "",
            "eng_name": current_user.eng_name or "",
            "birth_date": current_user.birth_date or "",
            "role": current_user.role or ""
        }
    }

@router.put("/me")
def update_me(req: UserUpdateModel, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.name is not None:
        current_user.name = req.name
    if req.eng_name is not None:
        current_user.eng_name = req.eng_name
    if req.birth_date is not None:
        current_user.birth_date = req.birth_date
    if req.role is not None:
        current_user.role = req.role
        
    try:
        db.commit()
        db.refresh(current_user)
        return {
            "status": "success",
            "message": "개인정보가 성공적으로 수정되었습니다.",
            "data": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name or "",
                "eng_name": current_user.eng_name or "",
                "birth_date": current_user.birth_date or "",
                "role": current_user.role or ""
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"개인정보 수정 실패: {str(e)}"
        )
