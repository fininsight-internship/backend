## jd 분석 ##

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import jd_service

router = APIRouter(prefix="/jd", tags=["JD"])


class JDRequest(BaseModel):
    jd_text: str


@router.post("/analyze")
async def analyze(req: JDRequest):
    try:
        return jd_service.analyze_jd(req.jd_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
