import sys
import os

# 백엔드 루트 폴더를 sys.path에 추가하여 app 패키지를 원활히 불러올 수 있도록 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import engine, Base
# 모든 모델들을 임포트하여 metadata에 등록되도록 유도
from app.models.db_models import (
    User, 
    Resume, 
    Experience, 
    Application, 
    CompanyJDAnalysis, 
    InterviewSession, 
    InterviewQuestion, 
    FollowUpQuestion, 
    ChatSession, 
    ChatMessage
)

def init_db():
    print("🚀 PostgreSQL 'careerai' 데이터베이스에 접속하여 테이블을 생성하는 중...")
    try:
        # 설계된 모든 테이블 자동 생성
        Base.metadata.create_all(bind=engine)
        print("🎉 대박! 모든 데이터베이스 테이블이 성공적으로 생성되었습니다!")
    except Exception as e:
        print("❌ 데이터베이스 초기화 중 에러가 발생했습니다:", e)

if __name__ == "__main__":
    init_db()
