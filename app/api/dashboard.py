from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.core.db import get_db
from app.models.db_models import User, CompanyJDAnalysis, Resume, InterviewSession

router = APIRouter(prefix="/user", tags=["Dashboard"])


def _resolve_user_id(request: Request, db: Session) -> int:
    """X-User-Id 헤더로 사용자 ID를 확인합니다."""
    x_user_id = request.headers.get("X-User-Id")
    if not x_user_id:
        # 비로그인 테스트 모드: 첫 번째 유저 사용
        test_user = db.query(User).filter(User.email == "dbeaver_test@careerai.com").first()
        if not test_user:
            test_user = db.query(User).first()
        if not test_user:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
        return test_user.id
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 X-User-Id 헤더입니다.")


@router.get("/dashboard")
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    홈 대시보드에 필요한 통계, 최근 준비 중인 기업, 최근 활동을 반환합니다.
    """
    user_id = _resolve_user_id(request, db)

    # ─── 1. 통계 ─────────────────────────────────────────────────
    analysis_count = db.query(CompanyJDAnalysis).filter(
        CompanyJDAnalysis.user_id == user_id
    ).count()

    resume_count = db.query(Resume).filter(
        Resume.user_id == user_id
    ).count()

    interview_count = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id
    ).count()

    # ─── 2. 최근 준비 중인 기업 (분석 기준, 최신 5개) ────────────
    recent_analyses = (
        db.query(CompanyJDAnalysis)
        .filter(CompanyJDAnalysis.user_id == user_id)
        .order_by(desc(CompanyJDAnalysis.created_at))
        .limit(5)
        .all()
    )

    # company_name 기준으로 중복 제거 (최신 분석 우선)
    seen_companies: set = set()
    recent_companies = []
    for a in recent_analyses:
        key = f"{a.company_name}::{a.job_role}"
        if key not in seen_companies:
            seen_companies.add(key)
            recent_companies.append({
                "company_name": a.company_name,
                "job_role": a.job_role,
                "analysis_id": a.id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    # ─── 3. 최근 활동 (분석·자소서·면접 합산, 최신 5개) ─────────
    activities = []

    # 기업 분석 활동
    for a in (
        db.query(CompanyJDAnalysis)
        .filter(CompanyJDAnalysis.user_id == user_id)
        .order_by(desc(CompanyJDAnalysis.created_at))
        .limit(10)
        .all()
    ):
        activities.append({
            "type": "analysis",
            "text": f"{a.company_name} 기업 분석 완료",
            "company_name": a.company_name,
            "job_role": a.job_role,
            "created_at": a.created_at,
        })

    # 자소서 활동
    for r in (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(desc(Resume.created_at))
        .limit(10)
        .all()
    ):
        activities.append({
            "type": "resume",
            "text": f"자소서 '{r.title}' 작성",
            "company_name": None,
            "job_role": None,
            "created_at": r.created_at,
        })

    # 면접 세션 활동
    for s in (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(desc(InterviewSession.created_at))
        .limit(10)
        .all()
    ):
        activities.append({
            "type": "interview",
            "text": f"{s.company_name} {s.job_role} 면접 연습",
            "company_name": s.company_name,
            "job_role": s.job_role,
            "created_at": s.created_at,
        })

    # 최신순 정렬 후 상위 5개
    activities.sort(key=lambda x: x["created_at"] or "", reverse=True)
    recent_activities = [
        {
            "type": a["type"],
            "text": a["text"],
            "company_name": a["company_name"],
            "job_role": a["job_role"],
            "created_at": a["created_at"].isoformat() if a["created_at"] else None,
        }
        for a in activities[:5]
    ]

    return {
        "stats": {
            "analysis_count": analysis_count,
            "resume_count": resume_count,
            "interview_count": interview_count,
        },
        "recent_companies": recent_companies,
        "recent_activities": recent_activities,
    }


@router.get("/applications")
def get_applications(request: Request, db: Session = Depends(get_db)):
    """지원 현황(파이프라인) 목록을 반환합니다."""
    user_id = _resolve_user_id(request, db)

    # 1. CompanyJDAnalysis 가져오기 (회사별, 직무별 유니크하게)
    analyses = db.query(CompanyJDAnalysis).filter(CompanyJDAnalysis.user_id == user_id).all()
    
    # 2. 면접 세션 가져오기
    interviews = db.query(InterviewSession).filter(InterviewSession.user_id == user_id).all()
    
    apps_dict = {}
    
    # 분석 기록을 기반으로 초기 파이프라인 구성
    for a in analyses:
        key = f"{a.company_name}::{a.job_role}"
        if key not in apps_dict:
            apps_dict[key] = {
                "company": a.company_name,
                "role": a.job_role,
                "score": 85, # mock score
                "deadline": None,
                "jd": "done",
                "resume": "waiting",
                "interview": "waiting"
            }

    # 면접 기록을 기반으로 파이프라인 갱신 또는 추가
    for i in interviews:
        key = f"{i.company_name}::{i.job_role}"
        if key not in apps_dict:
            apps_dict[key] = {
                "company": i.company_name,
                "role": i.job_role,
                "score": 85,
                "deadline": None,
                "jd": "waiting",
                "resume": "waiting",
                "interview": "done"
            }
        else:
            apps_dict[key]["interview"] = "done"
            
    # 자소서는 회사명이 Resume 테이블에 직접 없어서, 연결이 어려우니 
    # 분석 기록이 있는 경우 임의로 "in_progress" 나 "done" 등으로 처리할 수 있음.
    # 여기서는 간단히 jd가 done이면 resume를 in_progress로 설정.
    for k, v in apps_dict.items():
        if v["jd"] == "done" and v["resume"] == "waiting":
            v["resume"] = "in_progress"

    return list(apps_dict.values())

