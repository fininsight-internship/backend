## jd 분석 ##
from fastapi import APIRouter

router = APIRouter()

@router.get("/jd/analyze")
async def analyze_jd(company: str, job: str):
    return {"company": company, "job": job}

