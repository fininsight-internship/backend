import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Mac 환경의 Postgres.app 기본 접속 URL (기본 계정명과 포트 5432 사용)
# 기본 데이터베이스 명은 'careerai'로 설정합니다.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://localhost:5432/careerai"
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True # 연결 유효성 자동 검사
)

# 세션 생성기
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# DB 모델 생성을 위한 Base 클래스
Base = declarative_base()

# FastAPI Dependency Injection용 DB 세션 획득 제네레이터
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
