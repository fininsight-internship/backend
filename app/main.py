from fastapi import FastAPI
from app.api import company, jd, resume, interview
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(company.router)
# app.include_router(jd.router)
# app.include_router(resume.router)
# app.include_router(interview.router)