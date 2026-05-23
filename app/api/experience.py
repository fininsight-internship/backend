from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.db import get_db
from app.models.db_models import User, Experience

router = APIRouter(prefix="/experience", tags=["Experience"])

# ─── Pydantic Models for Validation ───────────────────────────────
class EducationEntryModel(BaseModel):
    schoolName: str
    admissionDate: str
    graduationDate: str

class BasicInfoModel(BaseModel):
    name: str
    engName: Optional[str] = ""
    birthDate: Optional[str] = ""
    education: List[EducationEntryModel]

class CertEntryModel(BaseModel):
    id: str
    name: str
    date: str
    organization: str

class CareerEntryModel(BaseModel):
    id: str
    company: str
    department: str
    startDate: str
    endDate: str
    detail: str

class BootcampEntryModel(BaseModel):
    id: str
    name: str
    topic: str
    detail: str

class CommonEntryModel(BaseModel):
    id: str
    title: str
    detail: str

class ExperienceSaveRequest(BaseModel):
    기본정보: BasicInfoModel
    자격증상: List[CertEntryModel]
    경력인턴: List[CareerEntryModel]
    교육부트캠프: List[BootcampEntryModel]
    프로젝트: List[CommonEntryModel]
    동아리: List[CommonEntryModel]
    봉사활동: List[CommonEntryModel]
    기타경험: List[CommonEntryModel]


# ─── Endpoints ───────────────────────────────────────────────────

@router.get("")
def get_user_experience(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"), 
    db: Session = Depends(get_db)
):
    """
    현재 로그인된 사용자의 상세 경험 스펙 데이터를 DB에서 로드하여 전달합니다.
    """
    if not x_user_id:
        # 비로그인/테스트 모드일 시, dbeaver_test 유저 혹은 최선행 유저 조회
        test_user = db.query(User).filter(User.email == "dbeaver_test@careerai.com").first()
        if not test_user:
            test_user = db.query(User).first()
        if not test_user:
            raise HTTPException(status_code=401, detail="로그인이 필요하거나 테스트용 유저 계정이 존재하지 않습니다.")
        user_id = test_user.id
    else:
        try:
            user_id = int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 X-User-Id 헤더입니다.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 유저를 데이터베이스에서 찾을 수 없습니다.")

    # 1. 기본 인적사항 및 학력 정보 구성
    basic_info = {
        "name": user.name or "",
        "engName": user.eng_name or "",
        "birthDate": user.birth_date or "",
        "education": user.education_list or []
    }

    # 2. 자격증 및 수상 내역 구성
    certs = user.certification_list or []

    # 3. experiences 테이블에서 각 활동 카테고리 정보 로드
    careers = []
    bootcamps = []
    projects = []
    clubs = []
    volunteers = []
    others = []

    for exp in user.experiences:
        exp_data = {"id": str(exp.id), "detail": exp.detail or ""}
        
        if exp.category == "경력인턴":
            careers.append({
                "id": str(exp.id),
                "company": exp.title or "",
                "department": exp.department or "",
                "startDate": exp.start_date or "",
                "endDate": exp.end_date or "",
                "detail": exp.detail or ""
            })
        elif exp.category == "교육부트캠프":
            bootcamps.append({
                "id": str(exp.id),
                "name": exp.title or "",
                "topic": exp.topic or "",
                "detail": exp.detail or ""
            })
        elif exp.category == "프로젝트":
            projects.append({
                "id": str(exp.id),
                "title": exp.title or "",
                "detail": exp.detail or ""
            })
        elif exp.category == "동아리":
            clubs.append({
                "id": str(exp.id),
                "title": exp.title or "",
                "detail": exp.detail or ""
            })
        elif exp.category == "봉사활동":
            volunteers.append({
                "id": str(exp.id),
                "title": exp.title or "",
                "detail": exp.detail or ""
            })
        elif exp.category == "기타경험":
            others.append({
                "id": str(exp.id),
                "title": exp.title or "",
                "detail": exp.detail or ""
            })

    return {
        "기본정보": basic_info,
        "자격증상": certs,
        "경력인턴": careers,
        "교육부트캠프": bootcamps,
        "프로젝트": projects,
        "동아리": clubs,
        "봉사활동": volunteers,
        "기타경험": others
    }


@router.post("")
def save_user_experience(
    req: ExperienceSaveRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """
    유저가 수정한 온보딩 경험 폼 스펙 전체를 원자적으로 PostgreSQL DB에 반영(Upsert)합니다.
    """
    if not x_user_id:
        test_user = db.query(User).filter(User.email == "dbeaver_test@careerai.com").first()
        if not test_user:
            test_user = db.query(User).first()
        if not test_user:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
        user_id = test_user.id
    else:
        try:
            user_id = int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 X-User-Id 헤더입니다.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저가 존재하지 않습니다.")

    try:
        # 1. users 테이블의 인적사항, 학력, 자격증 컬럼 실시간 업데이트
        user.name = req.기본정보.name
        user.eng_name = req.기본정보.engName
        user.birth_date = req.기본정보.birthDate
        user.education_list = [edu.model_dump() for edu in req.기본정보.education]
        user.certification_list = [cert.model_dump() for cert in req.자격증상]

        # 2. experiences 테이블의 기존 활동 로우들을 원자적으로 클리어 후 재등록 (가장 간결하며 오차 없는 롤백 보장형 동기화)
        db.query(Experience).filter(Experience.user_id == user_id).delete()

        # 2-1. 경력/인턴 등록
        for c in req.경력인턴:
            if c.company.strip() or c.detail.strip():
                new_exp = Experience(
                    user_id=user_id,
                    category="경력인턴",
                    title=c.company,
                    department=c.department,
                    start_date=c.startDate,
                    end_date=c.endDate,
                    detail=c.detail,
                    company_name=c.company,
                    role=c.department,
                    description=c.detail
                )
                db.add(new_exp)

        # 2-2. 교육/부트캠프 등록
        for b in req.교육부트캠프:
            if b.name.strip() or b.detail.strip():
                new_exp = Experience(
                    user_id=user_id,
                    category="교육부트캠프",
                    title=b.name,
                    topic=b.topic,
                    detail=b.detail,
                    company_name=b.name,
                    role=b.topic,
                    description=b.detail
                )
                db.add(new_exp)

        # 2-3. 공통 활동 영역 등록 (프로젝트, 동아리, 봉사활동, 기타경험)
        category_map = {
            "프로젝트": req.프로젝트,
            "동아리": req.동아리,
            "봉사활동": req.봉사활동,
            "기타경험": req.기타경험
        }

        for cat, items in category_map.items():
            for item in items:
                if item.title.strip() or item.detail.strip():
                    new_exp = Experience(
                        user_id=user_id,
                        category=cat,
                        title=item.title,
                        detail=item.detail,
                        company_name=item.title,
                        description=item.detail
                    )
                    db.add(new_exp)

        db.commit()
        print(f"📦 [DB Experiences] 유저 ID {user_id}의 모든 경험 데이터가 experiences 테이블에 실시간 보관 완료되었습니다.")
        return {"status": "success", "message": "경험 스펙이 데이터베이스에 실시간 영구 기록되었습니다."}

    except Exception as e:
        db.rollback()
        print("❌ 경험 데이터베이스 영속화 실패:", e)
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 중 심각한 오류가 발생했습니다: {str(e)}")


class DetailUpdateRequest(BaseModel):
    detail: str


@router.patch("/{exp_id}/detail")
def update_detail(
    exp_id: int,
    req: DetailUpdateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db)
):
    """
    특정 경험 항목의 상세 내용(detail)을 업데이트합니다.
    """
    if not x_user_id:
        test_user = db.query(User).filter(User.email == "dbeaver_test@careerai.com").first()
        if not test_user:
            test_user = db.query(User).first()
        if not test_user:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
        user_id = test_user.id
    else:
        try:
            user_id = int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 X-User-Id 헤더입니다.")

    exp = db.query(Experience).filter(Experience.id == exp_id, Experience.user_id == user_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="해당 경험 항목을 찾을 수 없습니다.")

    try:
        exp.detail = req.detail
        exp.description = req.detail
        db.commit()
        return {"status": "success", "message": "경험 상세 내용이 저장되었습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"저장 중 오류가 발생했습니다: {str(e)}")
