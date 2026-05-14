## 자소서 ## 
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.resume_service import (
    parse_resume_text,
    save_resume_json,
    load_resume_json
)

router = APIRouter()

class ResumeTextRequest(BaseModel):
    user_id: str
    resume_text: str

class ResumeJsonRequest(BaseModel):
    user_id: str
    resume_data: dict

# 1. 이력서 텍스트 → JSON 파싱 + 저장
@router.post("/resume/parse")
async def resume_parse(req: ResumeTextRequest):

    result = parse_resume_text(
        req.resume_text
    )

    saved_path = save_resume_json(
        req.user_id,
        result["data"]
    )

    result["saved_path"] = saved_path
    result["user_id"] = req.user_id

    return result

# 2. 이력서 JSON 직접 저장
@router.post("/resume/save")
async def resume_save(req: ResumeJsonRequest):

    saved_path = save_resume_json(
        req.user_id,
        req.resume_data
    )

    return {
        "status": "success",
        "user_id": req.user_id,
        "saved_path": saved_path
    }

# 3. 저장된 이력서 조회
@router.get("/resume/{user_id}")
async def resume_get(user_id: str):

    data = load_resume_json(
        user_id
    )

    if not data:

        return {
            "status": "error",
            "message": "이력서를 찾을 수 없습니다."
        }

    return {
        "status": "success",
        "data": data
    }