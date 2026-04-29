## 기업 분석 ##

from fastapi import APIRouter
from app.models.company_model import CompanyResponse
from app.services.company_service import generate_company_report

router = APIRouter(prefix="/company")


@router.get("/report", response_model=CompanyResponse)
def company_report(company: str, job: str = None):
    return generate_company_report(company, job)