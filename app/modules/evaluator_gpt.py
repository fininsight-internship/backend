import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """당신은 전직 대기업 인사팀장 출신 자소서 전문 컨설턴트입니다.
수천 건의 자소서를 검토한 경험을 바탕으로 합격/불합격을 좌우하는 핵심 요소를 정확히 짚어냅니다.

[평가 원칙]
- 사용자가 선택한 답변과 자소서 내용의 일치 여부를 최우선으로 본다.
- 경험 자체가 빈약해도 선택 내용과 자소서가 논리적으로 맞으면 감점 최소화.
- 0점은 선택 답변에 없는 완전히 새로운 수치나 존재하지 않는 프로젝트명이 등장할 때만 해당.
- 개선안은 반드시 원문을 실제로 대체할 수 있는 완성 문장으로 제시."""

USER_PROMPT_TEMPLATE = """[자기소개서 문항]
{question}

[기업/직무 정보]
{insights}

[사용자가 선택한 핵심 답변]
{selections}

[작성된 자기소개서]
{draft}

---
아래 형식으로 평가하세요. 각 항목을 빠짐없이 작성하세요.

### 🎯 합격 성적표
**총점: 00점 / 100점**

#### 📊 항목별 점수
| 항목 | 점수 | 평가 |
|------|------|------|
| 내용 일치도 (선택 답변 반영) | 00/30 | ... |
| 구체성·수치 활용 | 00/25 | ... |
| 구조·흐름 | 00/20 | ... |
| 기업 연결성 | 00/15 | ... |
| 문장 완성도 | 00/10 | ... |

#### 🔍 구조 분석
- **Hook(첫 문장)**: 임팩트 있음 / 평범함 / 개선 필요 — (이유 한 줄)
- **배경·상황**: (분량이 적절한지, 너무 길면 지적)
- **핵심 행동**: (구체적인지, STAR A가 잘 녹아있는지)
- **성과·결과**: (수치가 있는지, 없으면 대안 제시)
- **기업 연결**: ({company_keyword}과의 연결이 자연스러운지)

#### ⚡ 개선 필요 문장 TOP 2

**[1번]**
원문: "..."
문제: ...
개선안: "..."

**[2번]**
원문: "..."
문제: ...
개선안: "..."

#### 🚨 면접 리스크
이 자소서를 본 면접관이 공격적으로 파고들 수 있는 포인트 1~2개를 제시하고, 대비 방법을 알려주세요.

#### 💬 한 줄 총평
"..." (합격 가능성 판단 포함)
"""


class EvaluatorGPT:
    def evaluate(self, draft: str, context: dict) -> str:
        try:
            selections = context.get("selections", [])
            if isinstance(selections, list):
                sel_text = "\n".join([
                    f"- {s.get('text', str(s))}" if isinstance(s, dict) else f"- {s}"
                    for s in selections
                ])
            else:
                sel_text = str(selections)

            insights = str(context.get("insights", ""))
            question = str(context.get("question", ""))

            # 기업명 추출 (첫 단어 또는 전체)
            company_keyword = insights.split()[0] if insights.strip() else "해당 기업"

            user_prompt = USER_PROMPT_TEMPLATE \
                .replace("{selections}", sel_text or "선택 답변 없음") \
                .replace("{insights}", insights) \
                .replace("{question}", question) \
                .replace("{draft}", draft) \
                .replace("{company_keyword}", company_keyword)

            response = _client.models.generate_content(
                model="gemini-2.5-pro",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                ),
            )
            return response.text
        except Exception as e:
            print(f"[EvaluatorGPT] 오류: {e}")
            return f"평가 중 오류가 발생했습니다: {str(e)}"

    def parse_total_score(self, evaluation_text: str) -> int:
        match = re.search(r"총점[:\s]*(\d+)점", evaluation_text)
        return int(match.group(1)) if match else 0
