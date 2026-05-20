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
    ChatMessage,
    ResumeQuestion,
    ResumeEvaluation,
    ResumeQuestionEvaluation
)

def init_db():
    print("🚀 PostgreSQL 'careerai' 데이터베이스 테이블 재생성 중...")
    try:
        # 기존 테이블들 초기화 (마이그레이션 및 컬럼 변경 반영을 위해 재생성)
        Base.metadata.drop_all(bind=engine)
        # 설계된 모든 테이블 자동 생성
        Base.metadata.create_all(bind=engine)
        print("🎉 대박! 모든 데이터베이스 테이블이 성공적으로 생성되었습니다!")
        
        # 테스트용 영구 계정 자동 시드 생성
        from app.create_permanent_user import create_permanent_user
        create_permanent_user()
    except Exception as e:
        print("❌ 데이터베이스 초기화 중 에러가 발생했습니다:", e)

if __name__ == "__main__":
    init_db()
