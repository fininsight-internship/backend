import sys
import os

# 백엔드 루트 폴더를 sys.path에 추가하여 app 패키지를 원활히 불러올 수 있도록 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal
from app.models.db_models import User

def create_permanent_user():
    print("✍️ DBeaver 확인용 테스트 사용자 생성을 시작합니다...")
    db = SessionLocal()
    test_email = "dbeaver_test@careerai.com"
    
    try:
        # 기존 동일 이메일이 있다면 중복 방지를 위해 삭제 후 재생성
        existing = db.query(User).filter(User.email == test_email).first()
        if existing:
            db.delete(existing)
            db.commit()
            
        new_user = User(
            email=test_email,
            password_hash="hashed_password_12345",
            name="디비버길동",
            role="풀스택 개발자"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print("\n🎉 데이터베이스에 사용자가 성공적으로 추가되었습니다!")
        print("이제 DBeaver에서 새로고침(Refresh)을 누르시면 아래 데이터를 확인하실 수 있습니다:")
        print(f"   - 이메일: {new_user.email}")
        print(f"   - 이름: {new_user.name}")
        print(f"   - 직무: {new_user.role}")
        
    except Exception as e:
        print("❌ 에러 발생:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_permanent_user()
