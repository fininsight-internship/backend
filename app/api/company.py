## 기업 분석 ##

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.company_model import CompanyResponse
from app.services.company_service import generate_company_report
from app.core.db import get_db

router = APIRouter(prefix="/company")


@router.get("/report", response_model=CompanyResponse)
def company_report(company: str, job: str = None, db: Session = Depends(get_db)):
    return generate_company_report(db, company, job)