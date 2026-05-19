import os
import json
from openai import AsyncOpenAI
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ChatService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_next_question(self, company_name: str, jd_text: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Determines the next question to ask the user based on JD and chat history,
        or indicates if the chat is finished.
        """
        system_prompt = f"""
        당신은 {company_name}의 전문 헤드헌터이자 채용 담당자입니다.
        지원자의 경험과 역량을 파악하기 위해 인터뷰를 진행하고 있습니다.
        
        [채용 공고(JD)]
        {jd_text}
        
        **진행 규칙**:
        1. 첫 번째 질문은 보통 "현재 어떤 기술 스택을 주로 사용하고 계신가요?"와 같이 전반적인 역량을 묻습니다.
        2. 이후 사용자의 답변을 보고, JD에 명시된 핵심 요구사항(예: 대규모 트래픽 경험, 특정 프레임워크 경험 등)과 연결하여 꼬리 질문을 1~2회 더 진행합니다.
        3. 한 번에 하나의 질문만 하세요.
        4. 사용자가 충분한 정보를 제공했거나(총 2~3회 응답), 더 이상 물어볼 핵심 내용이 없다면 응답의 마지막에 반드시 "[FINISHED]" 라는 문자열을 포함하여 대화가 종료되었음을 알려주세요.
        5. 말투는 친절하고 전문적인 존댓말을 사용하세요.
        """

        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            # chat_history format: [{"role": "user" | "assistant", "content": "..."}]
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.6,
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            is_finished = "[FINISHED]" in content
            
            # Remove the [FINISHED] token from the final message shown to user
            clean_content = content.replace("[FINISHED]", "").strip()

            return {
                "success": True,
                "question": clean_content,
                "is_finished": is_finished
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

chat_service = ChatService()
