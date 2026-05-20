from fastapi import FastAPI
from app.api import company, jd, resume, interview, analysis, chat, auth, experience
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine
from app.models.db_models import Base

app = FastAPI()

@app.on_event("startup")
def on_startup():
    # 서버 실행 시 DB 테이블 자동 생성 (없을 때만 안전하게 생성됨)
    Base.metadata.create_all(bind=engine)
    print("🚀 [FastAPI Startup] 데이터베이스 테이블 검사 및 자동 생성 완료!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(company.router)
app.include_router(chat.router)
app.include_router(analysis.router)
app.include_router(jd.router)
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(experience.router)