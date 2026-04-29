from pydantic import BaseModel
from typing import List

class CompanyData(BaseModel):
    summary: str
    issues: List[str]

class CompanyResponse(BaseModel):
    status: str
    company: str
    data: CompanyData