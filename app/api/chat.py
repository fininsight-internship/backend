from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.services.chat_service import chat_service
from app.services.scraper_service import scraper_service

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"]
)

class ChatMessage(BaseModel):
    role: str
    content: str

class NextQuestionRequest(BaseModel):
    company_name: str
    jd_url: Optional[str] = None
    jd_text: Optional[str] = None
    chat_history: List[ChatMessage]

@router.post("/next-question")
async def get_next_question(request: NextQuestionRequest):
    try:
        jd_content = request.jd_text
        # If JD text is not provided but URL is, scrape it
        if not jd_content and request.jd_url:
            jd_result = scraper_service.scrape_jd(request.jd_url)
            if not jd_result.get("success"):
                raise HTTPException(status_code=400, detail=f"JD 스크래핑 실패: {jd_result.get('error')}")
            jd_content = jd_result["jd_text"]
            
        if not jd_content:
            jd_content = "상세 채용 공고 내용이 없습니다."

        # Convert Pydantic models to dicts for the service
        history = [{"role": msg.role, "content": msg.content} for msg in request.chat_history]

        result = await chat_service.get_next_question(
            company_name=request.company_name,
            jd_text=jd_content,
            chat_history=history
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=f"AI 채팅 생성 실패: {result.get('error')}")

        return {
            "success": True,
            "data": {
                "question": result["question"],
                "is_finished": result["is_finished"],
                "jd_text": jd_content # Return jd_text so frontend can cache it
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")
