import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

STAR_QUESTIONS = {
    'S': {
        'label': 'S — 상황',
        'question': '어떤 환경에서 일했나요?\n팀 규모, 서비스 성격, 본인의 역할을 간략히 알려주세요.',
        'hint': '예) 3인 팀, B2B SaaS 서비스, 프론트엔드 전담',
    },
    'T': {
        'label': 'T — 과제',
        'question': '그 경험에서 해결해야 했던 핵심 문제나 목표는 무엇이었나요?',
        'hint': '예) 레거시 jQuery 코드를 React로 전환하고 배포 파이프라인 구축',
    },
    'A': {
        'label': 'A — 행동',
        'question': '목표를 달성하기 위해 구체적으로 어떤 행동을 취했나요?\n본인이 주도한 부분을 중심으로 설명해주세요.',
        'hint': '예) 컴포넌트 단위 마이그레이션 계획 수립, Jest 커버리지 60%→85% 달성',
    },
    'R': {
        'label': 'R — 결과',
        'question': '그 행동의 결과는 어떠했나요?\n가능하면 수치로 표현해주세요.',
        'hint': '예) 배포 주기 2주→3일 단축, 버그 발생률 30% 감소',
    },
}

NEXT_STEP = {'S': 'T', 'T': 'A', 'A': 'R', 'R': None}


def get_question(star_step: str, experience_name: str, experience_role: str) -> dict:
    q = STAR_QUESTIONS[star_step]
    question = q['question']
    if star_step == 'S':
        question = f"{experience_name} {experience_role} 기간 동안 어떤 환경에서 일했나요?\n팀 규모, 서비스 성격, 본인의 역할을 간략히 알려주세요."
    return {
        'label': q['label'],
        'question': question,
        'hint': q['hint'],
        'next_step': NEXT_STEP[star_step],
    }


def generate_summary(experience_name: str, experience_role: str, answers: dict) -> dict:
    prompt = f"""아래 취준생의 경험 데이터를 각 항목별로 자연스럽고 임팩트 있는 한 문장으로 다듬어주세요.

경험: {experience_name} / {experience_role}
S (상황): {answers.get('S', '')}
T (과제): {answers.get('T', '')}
A (행동): {answers.get('A', '')}
R (결과): {answers.get('R', '')}

반드시 아래 JSON 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요:
{{"S": "...", "T": "...", "A": "...", "R": "..."}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.content[0].text.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content.strip())
    except Exception:
        return answers
