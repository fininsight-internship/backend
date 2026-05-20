from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import get_current_user
from app.models.db_models import User, CompanyReport, CompanyJDAnalysis
from app.services.scraper_service import scraper_service
from app.services.resume_parser import resume_parser
from app.services.ai_analysis_service import ai_analysis_service

router = APIRouter(
    prefix="/api/analysis",
    tags=["analysis"]
)

def has_profile_info(user: User) -> bool:
    if user.education_list and len(user.education_list) > 0:
        for edu in user.education_list:
            if edu.get("schoolName", "").strip():
                return True
    if user.certification_list and len(user.certification_list) > 0:
        for cert in user.certification_list:
            if cert.get("name", "").strip():
                return True
    if user.experiences and len(user.experiences) > 0:
        for exp in user.experiences:
            if (exp.title and exp.title.strip()) or (exp.detail and exp.detail.strip()):
                return True
    return False

def build_resume_from_profile(user: User) -> str:
    parts = []
    parts.append(f"이름: {user.name or ''}")
    if user.eng_name:
        parts.append(f"영문명: {user.eng_name}")
    if user.birth_date:
        parts.append(f"생년월일: {user.birth_date}")
    if user.role:
        parts.append(f"희망 직무: {user.role}")
        
    if user.education_list:
        parts.append("\n[학력 사항]")
        for edu in user.education_list:
            school = edu.get("schoolName", "")
            adm = edu.get("admissionDate", "")
            grad = edu.get("graduationDate", "")
            parts.append(f"- 학교명: {school} ({adm} ~ {grad})")
            
    if user.certification_list:
        parts.append("\n[자격증 및 수상 내역]")
        for cert in user.certification_list:
            name = cert.get("name", "")
            date = cert.get("date", "")
            org = cert.get("organization", "")
            parts.append(f"- 자격증명: {name} ({date}, 발급기관: {org})")

    # Group experiences by category
    experiences = user.experiences
    if experiences:
        categories = {}
        for exp in experiences:
            cat = exp.category or "기타경험"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(exp)
            
        for cat, items in categories.items():
            parts.append(f"\n[{cat}]")
            for item in items:
                title_label = "회사/기관명" if cat == "경력인턴" else ("교육명" if cat == "교육부트캠프" else "활동명")
                detail_parts = []
                detail_parts.append(f"- {title_label}: {item.title or ''}")
                if item.department:
                    detail_parts.append(f"  부서/역할: {item.department}")
                if item.topic:
                    detail_parts.append(f"  주제/내용: {item.topic}")
                if item.start_date or item.end_date:
                    detail_parts.append(f"  기간: {item.start_date or ''} ~ {item.end_date or ''}")
                if item.detail:
                    detail_parts.append(f"  상세내용: {item.detail}")
                parts.append("\n".join(detail_parts))
                
    return "\n".join(parts)

@router.post("/report")
async def generate_analysis_report(
    company_name: str = Form(...),
    jd_url: Optional[str] = Form(None),
    resume_file: Optional[UploadFile] = File(None),
    resume_text_input: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # 1. 기업분석 데이터 조회 및 캐싱 (CompanyReport)
        company_report = db.query(CompanyReport).filter(CompanyReport.company_name == company_name).first()
        if not company_report:
            # 1-1. 기업 정보 스크래핑
            company_result = scraper_service.scrape_company_info(company_name)
            company_info = company_result.get("company_info", "")
            
            # 1-2. AI 기업 분석 생성
            company_analysis = await ai_analysis_service.analyze_company_only(company_name, company_info)
            if "error" in company_analysis:
                raise HTTPException(status_code=500, detail=company_analysis["error"])
            
            # 1-3. DB에 기업 분석 캐시 저장
            company_report = CompanyReport(
                company_name=company_name,
                company_info=company_info,
                company_analysis=company_analysis
            )
            db.add(company_report)
            db.commit()
            db.refresh(company_report)

        # 2. JD 스크래핑
        jd_text = "상세 채용 공고 내용이 없습니다."
        if jd_url and jd_url.strip():
            jd_result = scraper_service.scrape_jd(jd_url.strip())
            if not jd_result.get("success"):
                raise HTTPException(status_code=400, detail=f"JD 스크래핑 실패: {jd_result.get('error')}")
            jd_text = jd_result["jd_text"]

        # 3. 사용자 경험 정보 통합 구성 (마이페이지 경험 정보 + 추가 업로드 이력서)
        user_profile_text = ""
        if has_profile_info(current_user):
            user_profile_text = build_resume_from_profile(current_user)
        else:
            user_profile_text = "등록된 마이페이지 경험 정보가 없습니다."
            
        uploaded_resume_text = ""
        if resume_file:
            file_bytes = await resume_file.read()
            parse_result = resume_parser.parse(file_bytes, resume_file.filename)
            if not parse_result.get("success"):
                raise HTTPException(status_code=400, detail=f"이력서 파싱 실패: {parse_result.get('error')}")
            uploaded_resume_text = parse_result["text"]
        elif resume_text_input:
            uploaded_resume_text = resume_text_input
            
        if uploaded_resume_text:
            resume_text = f"{user_profile_text}\n\n[추가 업로드된 이력서 내용]\n{uploaded_resume_text}"
        else:
            resume_text = user_profile_text

        # 4. AI 맞춤 적합도 및 JD 분석 수행 (2단계)
        fit_result = await ai_analysis_service.analyze_fit_and_jd(
            company_analysis=company_report.company_analysis,
            jd_text=jd_text,
            resume_text=resume_text
        )

        if "error" in fit_result:
            raise HTTPException(status_code=500, detail=fit_result["error"])

        # 5. 채용 직무명 자동 판별 및 데이터 로드
        job_role = fit_result.get("job_analysis", {}).get("job_role", "지원 직무")

        # 6. 사용자별 기존 동일 기업/직무 분석 결과가 있으면 업데이트(Upsert), 없으면 신규 생성
        jd_analysis = db.query(CompanyJDAnalysis).filter(
            CompanyJDAnalysis.user_id == current_user.id,
            CompanyJDAnalysis.company_name == company_name,
            CompanyJDAnalysis.job_role == job_role
        ).first()

        # 기존 is_starred 값 유지
        existing_starred = False
        if jd_analysis and jd_analysis.analysis_report:
            existing_starred = jd_analysis.analysis_report.get("is_starred", False)

        analysis_report = {
            "is_starred": existing_starred,
            "company_analysis": company_report.company_analysis,
            "job_analysis": fit_result.get("job_analysis", {}),
            "fit_analysis": fit_result.get("fit_analysis", {}),
            "document_optimization": fit_result.get("document_optimization", {})
        }

        if jd_analysis:
            jd_analysis.jd_content = jd_text
            jd_analysis.analysis_report = analysis_report
            jd_analysis.created_at = datetime.utcnow()
        else:
            jd_analysis = CompanyJDAnalysis(
                user_id=current_user.id,
                company_name=company_name,
                job_role=job_role,
                jd_content=jd_text,
                analysis_report=analysis_report
            )
            db.add(jd_analysis)

        db.commit()
        db.refresh(jd_analysis)

        # 7. 프론트엔드 포맷 맞춰 응답 데이터 결합
        combined_data = {
            "id": jd_analysis.id,
            "company_name": company_name,
            "job_role": job_role,
            "is_starred": existing_starred,
            "company_analysis": company_report.company_analysis,
            "job_analysis": fit_result.get("job_analysis", {}),
            "fit_analysis": fit_result.get("fit_analysis", {}),
            "document_optimization": fit_result.get("document_optimization", {}),
            "created_at": jd_analysis.created_at.isoformat() if jd_analysis.created_at else None
        }

        return {"success": True, "data": combined_data}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")

@router.get("/reports")
def get_saved_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        analyses = db.query(CompanyJDAnalysis).filter(
            CompanyJDAnalysis.user_id == current_user.id
        ).order_by(CompanyJDAnalysis.created_at.desc()).all()
        
        results = []
        for item in analyses:
            report = item.analysis_report or {}
            results.append({
                "id": item.id,
                "company_name": item.company_name,
                "job_role": item.job_role,
                "is_starred": report.get("is_starred", False),
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "company_analysis": report.get("company_analysis", {}),
                "job_analysis": report.get("job_analysis", {}),
                "fit_analysis": report.get("fit_analysis", {}),
                "document_optimization": report.get("document_optimization", {})
            })
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 목록 조회 중 오류 발생: {str(e)}")

@router.put("/reports/{report_id}/star")
def toggle_star_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        analysis = db.query(CompanyJDAnalysis).filter(
            CompanyJDAnalysis.id == report_id,
            CompanyJDAnalysis.user_id == current_user.id
        ).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
        
        report = analysis.analysis_report or {}
        new_starred = not report.get("is_starred", False)
        report["is_starred"] = new_starred
        analysis.analysis_report = report
        db.commit()
        db.refresh(analysis)
        return {"success": True, "is_starred": new_starred}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"즐겨찾기 상태 변경 중 오류 발생: {str(e)}")

@router.delete("/reports/{report_id}")
def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        analysis = db.query(CompanyJDAnalysis).filter(
            CompanyJDAnalysis.id == report_id,
            CompanyJDAnalysis.user_id == current_user.id
        ).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
        
        db.delete(analysis)
        db.commit()
        return {"success": True, "message": "보고서가 성공적으로 삭제되었습니다."}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 삭제 중 오류 발생: {str(e)}")
