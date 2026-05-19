## 자소서 ##

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services import resume_service

router = APIRouter(prefix="/resume", tags=["Resume"])


class UserInfo(BaseModel):
    experiences: str
    skills: str
    education: str
    extra: Optional[str] = "없음"


class Question(BaseModel):
    question: str
    char_limit: int


class GenerateRequest(BaseModel):
    report_text: str
    questions: List[Question]
    user_info: UserInfo
    company_name: str
    jd_analysis: Optional[str] = "해당 없음"


class EvaluateRequest(BaseModel):
    draft: str
    context: dict


class RefineRequest(BaseModel):
    draft: str
    evaluation: str
    user_answers: str
    context: dict


@router.post("/generate")
async def generate(req: GenerateRequest):
    try:
        return resume_service.generate_cover_letter(
            report_text=req.report_text,
            questions=[{"question": q.question, "char_limit": q.char_limit} for q in req.questions],
            user_info=req.user_info.model_dump(),
            company_name=req.company_name,
            jd_analysis=req.jd_analysis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def evaluate(req: EvaluateRequest):
    try:
        return resume_service.evaluate_cover_letter(req.draft, req.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine")
async def refine(req: RefineRequest):
    try:
        return resume_service.refine_cover_letter(req.draft, req.evaluation, req.user_answers, req.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── STAR chat ──────────────────────────────────────────────────────

class StarSummaryRequest(BaseModel):
    experience_name: str
    experience_role: str
    answers: dict


@router.post("/star-summary")
async def star_summary(req: StarSummaryRequest):
    try:
        return resume_service.generate_star_summary(req.experience_name, req.experience_role, req.answers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Cover letter chat ──────────────────────────────────────────────

class CoverChatRequest(BaseModel):
    company_name: str
    job_title: str
    cover_question: str
    char_limit: Optional[int] = 0
    star_data: dict
    history: List[dict]
    company_insights: Optional[str] = ""


class CoverFinalizeRequest(BaseModel):
    company_name: str
    job_title: str
    cover_question: str
    char_limit: Optional[int] = 0
    star_data: dict
    selections: List[str]
    company_insights: Optional[str] = ""


@router.post("/cover-chat")
async def cover_chat(req: CoverChatRequest):
    try:
        return resume_service.cover_chat_next(
            req.company_name, req.job_title, req.cover_question,
            req.star_data, req.history, req.company_insights or "",
            req.char_limit or 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cover-finalize")
async def cover_finalize(req: CoverFinalizeRequest):
    try:
        return resume_service.cover_chat_finalize(
            req.company_name, req.job_title, req.cover_question,
            req.star_data, req.selections, req.company_insights or "",
            req.char_limit or 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Detailed evaluation ────────────────────────────────────────────

class EvaluateDetailedRequest(BaseModel):
    draft: str
    company_name: str
    job_title: str
    cover_question: str
    selections: Optional[List[str]] = None
    company_insights: Optional[str] = ""


class EvaluateAllRequest(BaseModel):
    company_name: str
    job_title: str
    questions: List[str]
    drafts: List[str]


@router.post("/evaluate-all")
async def evaluate_all(req: EvaluateAllRequest):
    try:
        return resume_service.evaluate_all_drafts(
            req.company_name, req.job_title, req.questions, req.drafts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-detailed")
async def evaluate_detailed(req: EvaluateDetailedRequest):
    try:
        return resume_service.evaluate_detailed(
            req.draft, req.company_name, req.job_title, req.cover_question,
            req.selections, req.company_insights or ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
