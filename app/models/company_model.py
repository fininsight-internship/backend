from pydantic import BaseModel
from typing import List, Optional


class Business(BaseModel):
    main: List[str]
    description: str


class Culture(BaseModel):
    keywords: List[str]
    description: str


class JobInsight(BaseModel):
    job: Optional[str]
    required_skills: List[str]
    insight: str


class CompanyData(BaseModel):
    summary: str
    issues: List[str]
    business: Business
    culture: Culture
    job_insight: Optional[JobInsight]
    strategy: List[str]


class CompanyResponse(BaseModel):
    status: str
    company: str
    job: Optional[str]
    data: CompanyData