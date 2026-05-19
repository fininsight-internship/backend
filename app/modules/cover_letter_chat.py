import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

SYSTEM_PROMPT = """당신은 취업 전문 AI 멘토입니다.
사용자의 경험(STAR 데이터)과 기업 정보를 바탕으로 자기소개서 작성을 단계적으로 도와줍니다.

[출력 규칙]
- 반드시 JSON 형식으로만 출력
- 한 번에 하나의 질문만
- 4개의 선택지 제공 (기업·직무·경험에 맞춘 구체적인 1인칭 답변 형태)
- is_complete: 4번째 질문 응답 수신 이후에만 true"""


def get_next_step(
    company_name: str,
    job_title: str,
    cover_question: str,
    star_data: dict,
    history: list,
    company_insights: str = "",
    char_limit: int = 0,
) -> dict:
    user_answer_count = sum(1 for h in history if h.get("role") == "user")
    step = user_answer_count + 1
    is_last = step >= 4

    history_text = "\n".join([
        f"{'사용자' if h['role'] == 'user' else 'AI'}: {h['content']}"
        for h in history
    ]) or "없음"

    char_limit_text = f"\n글자 수 제한: {char_limit}자 이내" if char_limit > 0 else ""

    prompt = f"""기업: {company_name}
직무: {job_title}
자소서 문항: {cover_question}{char_limit_text}

STAR 경험:
S: {star_data.get('S', '')}
T: {star_data.get('T', '')}
A: {star_data.get('A', '')}
R: {star_data.get('R', '')}

기업 분석: {company_insights or '일반적인 IT 기업'}

대화 이력:
{history_text}

현재 {step}번째 질문을 생성해주세요.
1번째 → 지원 동기 (기업 특성 반영한 4가지 선택지)
2번째 → 핵심 경험 연결 (STAR 데이터 기반 선택지)
3번째 → 역량/강점 (직무 관련)
4번째 이상 → is_complete: true, 포부/기여 질문

{'is_complete를 true로 설정하세요.' if is_last else ''}

반드시 아래 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요:
{{"question": "...", "aspect": "...", "options": ["...", "...", "...", "..."], "is_complete": {str(is_last).lower()}}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        return {
            "question": "자소서 작성을 계속 진행하겠습니다. 추가로 강조하고 싶은 내용이 있나요?",
            "aspect": "추가 내용",
            "options": [],
            "is_complete": is_last,
        }


def generate_final_letter(
    company_name: str,
    job_title: str,
    cover_question: str,
    star_data: dict,
    selections: list,
    company_insights: str = "",
    char_limit: int = 0,
) -> str:
    sel_text = "\n".join([f"- {s}" for s in selections])
    prompt = f"""아래 정보를 바탕으로 자기소개서를 작성해주세요.

기업: {company_name} / 직무: {job_title}
자소서 문항: {cover_question}

STAR 경험:
상황: {star_data.get('S', '')}
과제: {star_data.get('T', '')}
행동: {star_data.get('A', '')}
결과: {star_data.get('R', '')}

사용자 선택 내용:
{sel_text}

기업 분석: {company_insights or '일반 기업 정보'}

작성 규칙:
- 마크다운 기호 없이 순수 텍스트
- '귀사' 대신 실제 회사명({company_name}) 사용
- 문어체 유지
- 도입 - 경험 - 역량 - 포부 흐름으로 자연스럽게 작성
{f"- 반드시 {char_limit}자 이내로 작성 (글자 수 제한 엄수)" if char_limit > 0 else "- 700자 내외로 작성"}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system="자기소개서 전문 작가입니다. 마크다운 없이 순수 텍스트만 출력하세요.",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
