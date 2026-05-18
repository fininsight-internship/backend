import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ============================================================
# 평가 원칙:
# - 자소서가 "사용자가 선택한 답변"과 일치하는지 검사한다.
# - 원본 경험 입력값이 적더라도, 선택한 내용과 자소서가 맞으면 OK.
# - 0점은 오직 명백한 허구(없는 수치, 존재하지 않는 프로젝트)만 해당.
# ============================================================

SYSTEM_PROMPT = """당신은 33만 취준생의 멘토 **'면접왕 이형'**입니다. 전직 인사팀장으로서 자소서를 냉정하게 평가합니다.

[⚖️ 평가 기준]
1. 자소서의 내용이 "사용자가 선택한 답변"과 논리적으로 일치하는가?
2. 3C-4P 구조가 갖춰졌는가? (배경 20% 이내, 행동과 성과 70% 이상)
3. "열심히", "최선을 다해" 같은 추상적 표현이 있는가?
4. 면접에서 공격받을 약점이 있는가?

[🚫 0점 기준 - 명백한 허구만 해당]
선택 답변에 없는 완전히 새로운 수치나 존재하지 않는 프로젝트명이 등장할 때만 0점 처리.
단순히 경험이 적거나 표현이 부족한 것은 감점 요인이지 0점이 아닙니다.
"""

USER_PROMPT_TEMPLATE = """[사용자가 선택한 답변]
{selections}

[기업/직무 정보]
{insights}

[자기소개서 문항]
{question}

[작성된 자소서]
{draft}

---
아래 형식으로 평가하세요:

### 🎯 [면접왕 이형의 합격 성적표]
**총점: 00점 / 100점**

#### 1. 🔍 3C-4P 구조 분석
- **배경(Context)**:
- **핵심 행동(Core)**:
- **수치 성과(Proof)**:

#### 2. ⚡️ 개선 필요 문장 TOP 2

**[원문]** "..."

**[문제점]** ...

**[이형의 대안]** "..."

---

**[원문]** "..."

**[문제점]** ...

**[이형의 대안]** "..."

#### 3. 🚀 한 줄 총평
"..."
"""


class EvaluatorGPT:
    def evaluate(self, draft: str, context: dict) -> str:
        print("[EvaluatorGemini] 자소서 평가 시작 (선택 답변 기준)...")
        try:
            selections = context.get("selections", [])
            if isinstance(selections, list):
                sel_text = "\n".join([
                    f"- {s.get('text', str(s))}" if isinstance(s, dict) else f"- {s}"
                    for s in selections
                ])
            else:
                sel_text = str(selections)

            user_prompt = USER_PROMPT_TEMPLATE \
                .replace("{selections}", sel_text) \
                .replace("{insights}", str(context.get("insights", ""))) \
                .replace("{question}", str(context.get("question", ""))) \
                .replace("{draft}", draft)

            response = _client.models.generate_content(
                model="gemini-2.5-pro",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0,
                ),
            )
            return response.text
        except Exception as e:
            print(f"[EvaluatorGemini] 오류: {e}")
            return f"평가 중 오류가 발생했습니다: {str(e)}"

    def parse_total_score(self, evaluation_text: str) -> int:
        match = re.search(r"총점[:\s]*(\d+)점", evaluation_text)
        return int(match.group(1)) if match else 0
