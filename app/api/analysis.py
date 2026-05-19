from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from app.services.scraper_service import scraper_service
from app.services.resume_parser import resume_parser
from app.services.ai_analysis_service import ai_analysis_service

router = APIRouter(
    prefix="/api/analysis",
    tags=["analysis"]
)

@router.post("/report")
async def generate_analysis_report(
    company_name: str = Form(...),
    jd_url: str = Form(...),
    resume_file: Optional[UploadFile] = File(None),
    resume_text_input: Optional[str] = Form(None)
):
    try:
        # 1. JD 스크래핑
        jd_result = scraper_service.scrape_jd(jd_url)
        if not jd_result.get("success"):
            raise HTTPException(status_code=400, detail=f"JD 스크래핑 실패: {jd_result.get('error')}")
        jd_text = jd_result["jd_text"]

        # 2. 기업 정보 스크래핑
        company_result = scraper_service.scrape_company_info(company_name)
        company_info = company_result.get("company_info", "")

        # 3. 이력서 파싱 또는 텍스트 입력 사용
        resume_text = ""
        if resume_file:
            file_bytes = await resume_file.read()
            parse_result = resume_parser.parse(file_bytes, resume_file.filename)
            if not parse_result.get("success"):
                raise HTTPException(status_code=400, detail=f"이력서 파싱 실패: {parse_result.get('error')}")
            resume_text = parse_result["text"]
        elif resume_text_input:
            resume_text = resume_text_input

        # 4. AI 분석
        report = await ai_analysis_service.analyze_company_and_jd(
            company_name=company_name,
            company_info=company_info,
            jd_text=jd_text,
            resume_text=resume_text
        )

        if "error" in report:
            raise HTTPException(status_code=500, detail=f"AI 분석 실패: {report['error']}")

        return {"success": True, "data": report}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")
