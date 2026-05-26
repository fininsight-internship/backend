import hashlib
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.db_models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    nickname: Optional[str] = None
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
        eng_name=req.nickname.strip() if req.nickname else None,
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

@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    """현재 로그인된 사용자의 프로필 정보를 반환합니다."""
    x_user_id = request.headers.get("X-User-Id")
    if not x_user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    try:
        user_id = int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 사용자 ID입니다.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name or "",
        "role": user.role or "",
        "eng_name": user.eng_name or "",
        "birth_date": user.birth_date or "",
    }


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
