from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.core.db import get_db
from app.models.db_models import User

def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    db: Session = Depends(get_db)
) -> User:
    user = None
    
    # 1. 헤더 정보를 통해 사용자 조회
    if x_user_id:
        try:
            user_id_int = int(x_user_id)
            user = db.query(User).filter(User.id == user_id_int).first()
        except ValueError:
            pass
            
    if not user and x_user_email:
        user = db.query(User).filter(User.email == x_user_email.strip().lower()).first()
        
    # 2. 비인증 / 예외 폴백 처리
    if not user:
        test_email = "dbeaver_test@careerai.com"
        
        # 폴백 1: dbeaver_test@careerai.com 계정 매칭
        user = db.query(User).filter(User.email == test_email).first()
        
        # 폴백 2: DB 상의 첫 번째 유저 매칭
        if not user:
            user = db.query(User).first()
            
        # 폴백 3: DB에 사용자가 아예 없는 경우, dbeaver_test 계정 자동 생성
        if not user:
            try:
                user = User(
                    email=test_email,
                    password_hash="hashed_password_12345",
                    name="디비버길동",
                    role="풀스택 개발자"
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"⚠️ [Auth Fallback] DB가 비어있어 기본 사용자({test_email})를 자동 생성했습니다.")
            except Exception as e:
                db.rollback()
                print(f"❌ [Auth Fallback] 기본 사용자 자동 생성 실패: {e}")
                raise HTTPException(
                    status_code=401,
                    detail="인증되지 않은 요청이며, 기본 사용자 생성을 실패했습니다."
                )
                
    return user
