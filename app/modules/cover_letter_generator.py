import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

SYSTEM_PROMPT = """당신은 수만 개의 자소서를 검토한 베테랑 인사팀장이자, 필력이 좋은 전문 작가입니다.

[🚫 절대 엄수 규칙: 데이터 무결성]
- 지원자 정보({experiences}, {skills}, {extra})에 명시되지 않은 경험, 프로젝트, 성과, 수치(%) 등을 절대로 지어내지 마십시오.
- 존재하지 않는 사실을 가공하여 작성하는 것은 지원자의 신뢰도를 파괴하는 치명적인 결함입니다.
- 만약 특정 직무 역량에 대한 구체적인 경험이 부족하다면, 지어내는 대신 해당 분야에 대한 '깊은 관심'과 '향후 학습 및 기여 의지'로 정직하게 표현하십시오.

[⚠️ 최우선 금지 규칙: '귀사' 표현 금지]
- 어떠한 경우에도 '귀사'라는 단어를 사용하지 마십시오.
- 대신 반드시 실제 회사명(예: 카카오)을 직접 언급하십시오.

[문체 가이드라인 - 격식과 예의]
1. [구어체 절대 금지]: "~였죠", "~했고요", "~거든요" 등 사적인 대화체나 블로그 문체를 절대 사용하지 마십시오. 비즈니스 공식 문서인 문어체(~했습니다, ~입니다)를 유지하십시오.
2. [회사의 가치관 존중]: 기업의 전략이나 가치를 정의 내리듯 말하지 마십시오. 대신 "지원자로서 ~라고 생각합니다", "~로 알고 있습니다", "~에 깊이 공감합니다"와 같이 자신의 관점임을 명시하십시오.
3. [겸손한 포부]: 본인의 역량이 무언가를 "보여준다"고 단정 짓지 마십시오. 대신 "이 역량을 바탕으로 ~에 기여하고 싶습니다", "~하는 데 일조하겠습니다"와 같이 기여의 의지를 표현하십시오.
4. [자연스러운 시제]: 깨달음은 "느꼈습니다"와 같은 경험형 과거 시제를, 포부는 "하겠습니다"와 같은 미래 의지형 시제를 사용하십시오.
5. [정형화된 연결어 금지]: '이는', '특히', '또한' 등 AI 단골 접속사를 빼고 문맥으로 자연스럽게 이어가십시오."""

USER_PROMPT = """[회사명]
{company_name}

[기업 분석 및 인사이트]
{insights}

[채용 공고(JD) 분석 결과]
{jd_analysis}

[자기소개서 문항]
{question}

[글자 수 제한]
{char_limit}자 이내

[지원자 정보]
- 경험: {experiences}
- 기술: {skills}
- 학력: {education}
- 기타: {extra}

위의 [기업 분석]과 [JD 분석] 내용을 바탕으로, 지원자의 경험이 해당 직무에 완벽히 부합함을 증명하는 압도적인 자기소개서를 작성하십시오. (JD 분석 내용이 있다면 해당 직무 역량을 최우선으로 반영하십시오.)"""

REFINE_PROMPT = """당신이 작성한 초안에 대해 아래와 같은 전문가의 냉혹한 평가가 내려졌습니다.

[전문가 평가 피드백]
{evaluation}

[채용 공고(JD) 분석 결과]
{jd_analysis}

[수정 지시]
1. 위 피드백에서 지적된 '감점 항목'과 '문제점'을 완벽하게 해결하십시오.
2. 만약 JD 분석 결과가 있다면, 해당 직무에서 요구하는 역량이 더 선명하게 드러나도록 수정하십시오.
3. 제안된 '대안 문장'의 논리를 전체 흐름에 맞게 자연스럽게 녹여내십시오.
4. 수정 후 점수가 90점 이상이 나올 수 있도록 품질을 극한으로 끌어올리십시오.

[이전 초안]
{previous_draft}"""


class CoverLetterGenerator:
    def generate(self, context: dict) -> str:
        print("[CoverLetterGenerator] Claude Sonnet 4.6으로 초안 작성 중...")
        jd_info = context.get("jd_analysis", "제공되지 않음")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": USER_PROMPT.format(
                    company_name=context["company_name"],
                    insights=context["insights"],
                    jd_analysis=jd_info,
                    question=context["question"],
                    char_limit=context["char_limit"],
                    experiences=context["experiences"],
                    skills=context["skills"],
                    education=context["education"],
                    extra=context.get("extra", "없음"),
                ),
            }],
        )
        return response.content[0].text

    def refine(self, draft: str, evaluation: str, context: dict) -> str:
        print("[CoverLetterGenerator] 피드백을 반영하여 자소서 고쳐 쓰는 중...")
        jd_info = context.get("jd_analysis", "제공되지 않음")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": REFINE_PROMPT.format(
                    evaluation=evaluation,
                    jd_analysis=jd_info,
                    previous_draft=draft,
                ),
            }],
        )
        return response.content[0].text
