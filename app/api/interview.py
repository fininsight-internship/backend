## 면접 ##

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services import interview_service

router = APIRouter(prefix="/interview", tags=["Interview"])


class StepRequest(BaseModel):
    step: int
    user_data: dict
    company_name: str
    job_title: str
    question: str
    char_limit: int
    history: Optional[List[dict]] = None


class FinalRequest(BaseModel):
    user_data: dict
    company_name: str
    job_title: str
    question: str
    selections: List[dict]


class EvaluateRequest(BaseModel):
    draft: str
    company_name: str
    question: str
    char_limit: int
    selections: Optional[List[dict]] = None


@router.get("/companies")
async def get_companies():
    return interview_service.get_companies()


@router.post("/next-step")
async def next_step(req: StepRequest):
    try:
        return interview_service.get_next_step(
            step=req.step,
            user_data=req.user_data,
            company_name=req.company_name,
            job_title=req.job_title,
            history=req.history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/finalize")
async def finalize(req: FinalRequest):
    try:
        return interview_service.finalize_letter(
            user_data=req.user_data,
            company_name=req.company_name,
            job_title=req.job_title,
            question=req.question,
            selections=req.selections
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def evaluate(req: EvaluateRequest):
    try:
        return interview_service.evaluate_letter(
            draft=req.draft,
            company_name=req.company_name,
            question=req.question,
            char_limit=req.char_limit,
            selections=req.selections
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
