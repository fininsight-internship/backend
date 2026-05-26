import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MENTOR_SYSTEM_PROMPT = """당신은 대한민국 최고의 취업 멘토 **'면접왕 이형'**입니다.
전직 인사팀장의 시각으로 지원자의 경험에서 **'필살기'**를 뽑아내어, 자소서부터 면접까지 한 방에 해결할 수 있는 구조를 만듭니다.
말투는 자신감이 넘치고 명확하며, 지원자가 실수를 바로잡고 합격할 수 있도록 단호하면서도 실질적인 조언을 제공합니다.

[자소서 코칭 핵심 원칙]
1. 자소서와 면접은 병렬: 자소서는 단순히 글쓰기가 아니라 면접에서 말할 '필살기'의 기초 공사입니다.
2. 3C(Context, Intent, Core) 적용: 구구절절한 설명은 빼고, 면접관이 궁금해하는 핵심 위주로 배경(Context), 의도(Intent), 핵심(Core)을 정리합니다.
3. 4P(Process & Result) 구조화: 경험의 과정(Process)에서 어떤 구체적인 행동(Edge)을 했는지, 결론(Result)이 무엇인지 엣지 있게 구성합니다.
4. 성과 중심: 면접관이 뽑을 수밖에 없는 '경험의 수치화'와 '직무 역량'을 강조합니다.

[작성 가이드라인]
- "자, 면접 직전 퀵하게 정리합시다!" 또는 "믿고 따라오세요!"와 같은 에너제틱한 문구로 시작하세요.
- 추상적인 단어(열심히, 최선을 다하는, 혁신적인)를 발견하면 즉시 구체적인 '행동'과 '숫자'로 대체하세요.
- 답변 마지막에는 항상 "이게 바로 당신의 필살기입니다!"라고 확신을 주며 마무리하세요.
- 반드시 [3C/4P] 구조가 잘 드러나도록 소제목을 활용하여 작성하십시오.
"""

MENTOR_USER_PROMPT = """[회사명]
{company_name}

[기업/직무 분석 인사이트]
{insights}

[지원자 정보]
- 경험: {experiences}
- 기술: {skills}

[자기소개서 문항]
{question}

이형 멘토님, 위 내용을 바탕으로 면접까지 프리패스할 수 있는 '필살기' 자소서를 만들어주세요!
"""

class MentorGenerator:
    def __init__(self):
        self.model = "gpt-4o"

    def generate(self, context: dict) -> str:
        print("[MentorGenerator] 면접왕 이형 멘토가 자소서를 코칭 중입니다...")
        
        response = client.chat.completions.create(
            model=self.model,
            temperature=0.8, # 멘토의 창의성과 에너지를 위해 약간 높임
            messages=[
                {"role": "system", "content": MENTOR_SYSTEM_PROMPT},
                {"role": "user", "content": MENTOR_USER_PROMPT.format(
                    company_name=context.get("company_name", "미지정"),
                    insights=context.get("insights", "일반적인 직무 역량 중심"),
                    experiences=context.get("experiences", "데이터 없음"),
                    skills=context.get("skills", "데이터 없음"),
                    question=context.get("question", "지원 동기 및 포부")
                )}
            ]
        )
        
        return response.choices[0].message.content
