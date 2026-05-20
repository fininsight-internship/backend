import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

STEP_SYSTEM_PROMPT = """당신은 자기소개서 작성 전문 컨설턴트입니다.
사용자의 실제 경험(STAR)과 기업 정보를 바탕으로 자소서 문항에 최적화된 질문을 단계적으로 합니다.

[출력 규칙]
- 반드시 JSON 형식으로만 출력
- 한 번에 하나의 질문만
- 선택지 4개: 사용자의 실제 STAR 데이터에서 구체적인 내용을 뽑아 1인칭으로 작성 (수치·프로젝트명·행동 포함)
- is_complete: 마지막 질문 응답 이후에만 true"""

FINAL_SYSTEM_PROMPT = """당신은 10년 경력의 자기소개서 전문 컨설턴트입니다.
수천 명의 합격자를 배출한 경험을 바탕으로, 읽는 사람이 면접을 부르고 싶게 만드는 자소서를 작성합니다.

[절대 원칙]
- 마크다운 기호(##, **, -, ``` 등) 사용 금지
- 순수 텍스트만 출력
- 클리셰 표현 사용 금지"""


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

    prompt = f"""## 지원 정보
기업: {company_name} / 직무: {job_title}
자소서 문항: {cover_question}{char_limit_text}

## STAR 경험 (선택지 작성 시 이 내용을 구체적으로 활용하세요)
S(상황): {star_data.get('S', '')}
T(과제): {star_data.get('T', '')}
A(행동): {star_data.get('A', '')}
R(결과): {star_data.get('R', '')}

## 기업 분석
{company_insights or f'{company_name}의 {job_title} 직무'}

## 대화 이력
{history_text}

---
현재 {step}번째 질문입니다 (총 4번의 질문 후 자소서를 작성합니다).

## 질문 생성 규칙
1. **문항 분석**: 자소서 문항이 무엇을 요구하는지 파악하고, 그 핵심에 맞는 질문을 생성
2. **단계적 심화**: 단계가 올라갈수록 더 구체적이고 깊은 내용을 이끌어내는 질문
   - 1단계: 핵심 상황/배경 (무엇을, 왜)
   - 2단계: 구체적 행동/과정 (어떻게)
   - 3단계: 결과/성과/영향 (얼마나, 어떤 변화)
   - 4단계(마지막): {company_name}과의 연결 / 입사 후 기여 방향
3. **선택지 품질 기준**:
   - STAR 데이터의 실제 내용(수치, 프로젝트명, 기술명, 역할)을 직접 반영
   - 추상적인 표현("열심히", "최선을 다해") 금지
   - 각 선택지는 서로 다른 관점이나 강도를 가져야 함
   - 1인칭 완결 문장 (예: "React Query 도입으로 서버 상태 관리를 개선해 로딩 속도를 40% 단축했습니다")
4. **이미 답한 내용은 다시 묻지 말 것**

{'## 마지막 질문 규칙\nis_complete를 true로 설정. ' + company_name + '에서 이 경험을 어떻게 활용할지, 입사 후 구체적 기여 방향을 이끌어내는 질문을 하세요.' if is_last else ''}

반드시 아래 JSON 형식으로만 출력하세요:
{{"question": "...", "aspect": "...", "options": ["...", "...", "...", "..."], "is_complete": {str(is_last).lower()}}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=STEP_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text.strip()
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

    char_instruction = (
        f"반드시 {char_limit}자 이내로 작성 (공백 포함, 글자 수 제한 엄수)"
        if char_limit > 0
        else "800자 내외로 작성 (너무 짧으면 설득력 저하)"
    )

    # STAR R에서 수치 추출 힌트
    star_r = star_data.get('R', '')
    has_metrics = any(c.isdigit() for c in star_r)
    metrics_instruction = (
        f"STAR 결과(R)에 포함된 수치({star_r})를 본문에 자연스럽게 녹이세요."
        if has_metrics
        else "가능하면 행동의 규모나 영향을 구체적으로 표현하세요 (예: 팀원 N명, N주간, N번의 반복 등)."
    )

    prompt = f"""## 지원 정보
기업: {company_name} / 직무: {job_title}
자소서 문항: {cover_question}

## STAR 경험
상황(S): {star_data.get('S', '')}
과제(T): {star_data.get('T', '')}
행동(A): {star_data.get('A', '')}
결과(R): {star_data.get('R', '')}

## 사용자가 직접 선택한 핵심 내용 (반드시 이 내용을 중심으로 작성)
{sel_text}

## 기업/직무 분석
{company_insights or f'{company_name} {job_title}'}

---
## 작성 지침

### 1. 문항 유형 파악 후 구조 선택
자소서 문항을 분석하여 가장 적합한 구조를 선택하세요:
- **지원 동기형**: [기업 선택의 구체적 계기] → [연결되는 경험·역량] → [{company_name}에서의 기여 방향]
- **성장·도전형**: [도전의 배경과 상황] → [구체적 행동과 어려움 극복] → [결과와 변화] → [직무 적용]
- **협업·리더십형**: [팀 상황과 나의 역할] → [구체적 행동·갈등 해결] → [팀 성과에 대한 기여] → [역량 정리]
- **실패·극복형**: [실패 상황 직시] → [원인 분석] → [극복을 위한 구체적 행동] → [교훈과 성장]
- **역량·경험 소개형**: [역량의 핵심 정의] → [근거가 되는 경험] → [수치·결과] → [{job_title}에서의 활용]

### 2. 첫 문장 (Hook)
다음 중 하나의 방식으로 시작하세요:
- 구체적인 수치나 장면: "40%의 성능 향상이라는 목표 앞에서..."
- 역발상 또는 문제 제기: "팀의 절반이 포기할 때, 저는 다른 방향을 선택했습니다."
- 핵심 역량의 정의: "저는 데이터가 말하게 하는 개발자입니다."

### 3. 수치와 구체성
{metrics_instruction}
모든 행동과 결과는 '얼마나', '몇 명', '몇 퍼센트', '몇 주' 등으로 구체화하세요.

### 4. {company_name} 연결
기업 분석 정보를 활용해 "{company_name}이기 때문에 내 경험이 의미 있다"는 연결고리를 만드세요.
단순히 회사명을 언급하는 것이 아닌, 회사의 가치·방향성과 경험을 엮어야 합니다.

### 5. 절대 금지 표현
다음 표현은 어떤 형태로도 사용하지 마세요:
- "열심히", "최선을 다해", "노력했습니다", "노력하겠습니다"
- "성장할 수 있었습니다", "많이 배웠습니다", "배우게 되었습니다"
- "도전을 두려워하지 않습니다", "항상 긍정적으로"
- "귀사" (반드시 "{company_name}" 사용)
- 마크다운 기호 (##, **, -, ``` 등)

### 6. 형식
- 순수 텍스트, 문어체
- {char_instruction}
- 단락 사이 빈 줄 하나"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=FINAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    result = response.content[0].text

    # 글자수 초과 시 1회 재시도
    if char_limit > 0 and len(result) > char_limit:
        retry_prompt = (
            f"방금 작성한 자소서가 {len(result)}자입니다. "
            f"반드시 {char_limit}자 이내(공백 포함)로 줄여서 다시 작성해주세요. "
            f"핵심 내용(수치, 행동, 기업 연결)은 유지하되 불필요한 수식어를 제거하세요.\n\n"
            f"[이전 작성본]\n{result}"
        )
        retry = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=FINAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": retry_prompt}],
        )
        result = retry.content[0].text

    return result
