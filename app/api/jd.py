## jd 분석 ##
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.jd_service import (
    analyze_jd,
    generate_ideal_resume,
    analyze_gap,
    generate_resume_content,
    load_jd_json,
    load_resume_json
)
from app.crawler.jd_crawler import (
    crawl_and_save
)

router = APIRouter()

class JDRequest(BaseModel):
    job_id: str
    jd_text: str

class GapRequest(BaseModel):
    job_id: str
    jd_text: str
    actual_resume: dict

class GapRequestV2(BaseModel):
    job_id: str
    user_id: str

class ResumeWriteRequestV2(BaseModel):
    job_id: str
    user_id: str

class CrawlRequest(BaseModel):
    url: str

# 1. JD 분석
@router.post("/jd/analyze")
async def jd_analyze(req: JDRequest):

    return analyze_jd(
        req.jd_text,
        req.job_id
    )

# 2. 이상적 이력서 생성
@router.post("/jd/ideal-resume")
async def jd_ideal_resume(req: JDRequest):

    jd_result = analyze_jd(
        req.jd_text,
        req.job_id
    )

    ideal = generate_ideal_resume(
        jd_result["data"]
    )

    ideal["job_id"] = req.job_id

    return ideal

# 3. 갭 분석
@router.post("/jd/gap-analysis")
async def jd_gap_analysis(req: GapRequest):

    jd_result = analyze_jd(
        req.jd_text,
        req.job_id
    )

    ideal = generate_ideal_resume(
        jd_result["data"]
    )

    gap = analyze_gap(
        ideal["data"],
        req.actual_resume
    )

    gap["job_id"] = req.job_id

    return gap

# 4. 갭 분석 v2
@router.post("/jd/gap-analysis/v2")
async def jd_gap_analysis_v2(req: GapRequestV2):

    jd_data = load_jd_json(
        req.job_id
    )

    if not jd_data:

        return {
            "status": "error",
            "message": "JD 파일 없음"
        }

    resume_data = load_resume_json(
        req.user_id
    )

    if not resume_data:

        return {
            "status": "error",
            "message": "이력서 파일 없음"
        }

    ideal = generate_ideal_resume(
        jd_data["data"]
    )

    gap = analyze_gap(
        ideal["data"],
        resume_data["data"]
    )

    gap["job_id"] = req.job_id
    gap["user_id"] = req.user_id

    return gap

# 5. 이력서 생성
@router.post("/jd/resume-write")
async def jd_resume_write(req: GapRequest):

    jd_result = analyze_jd(
        req.jd_text,
        req.job_id
    )

    ideal = generate_ideal_resume(
        jd_result["data"]
    )

    gap = analyze_gap(
        ideal["data"],
        req.actual_resume
    )

    resume = generate_resume_content(
        jd_result["data"],
        gap["data"],
        req.actual_resume
    )

    resume["job_id"] = req.job_id

    return resume

# 6. 이력서 생성 v2
@router.post("/jd/resume-write/v2")
async def jd_resume_write_v2(req: ResumeWriteRequestV2):

    jd_data = load_jd_json(
        req.job_id
    )

    if not jd_data:

        return {
            "status": "error",
            "message": "JD 파일 없음"
        }

    resume_data = load_resume_json(
        req.user_id
    )

    if not resume_data:

        return {
            "status": "error",
            "message": "이력서 파일 없음"
        }

    ideal = generate_ideal_resume(
        jd_data["data"]
    )

    gap = analyze_gap(
        ideal["data"],
        resume_data["data"]
    )

    resume = generate_resume_content(
        jd_data["data"],
        gap["data"],
        resume_data["data"]
    )

    resume["job_id"] = req.job_id
    resume["user_id"] = req.user_id

    return resume

# 7. 잡코리아 크롤링
@router.post("/jd/crawl-and-analyze")
async def jd_crawl_and_analyze(req: CrawlRequest):

    payload = crawl_and_save(
        req.url
    )

    if payload.get("error"):

        return {
            "status": "error",
            "message": payload["error"]
        }

    ideal = generate_ideal_resume(
        payload["data"]
    )

    ideal["job_id"] = payload["job_id"]
    ideal["metadata"] = payload["metadata"]
    ideal["source_url"] = payload["source_url"]

    return ideal