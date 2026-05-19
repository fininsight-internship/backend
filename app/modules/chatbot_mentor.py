import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================
# 핵심 설계 원칙:
# 1. 보기는 오직 사용자가 입력한 경험 데이터에서만 파생한다.
# 2. 경험 데이터가 적으면 → 더 많은 경험을 끌어내는 질문을 한다.
# 3. 보기는 항상 1인칭 답변 형태 ("나는 ~했다")로만 만든다.
# 4. 평가 엔진은 사용자의 선택 내용과 자소서가 일치하는지만 본다.
# ============================================================

CHATBOT_SYSTEM_PROMPT = """당신은 33만 취준생의 멘토 **'면접왕 이형'**입니다.

[🔒 보기(options) 생성 철칙]
1. 보기는 반드시 사용자가 제공한 경험 데이터에 기반해야 합니다.
2. 보기는 반드시 **지원자 입장의 1인칭 답변** 형태여야 합니다. (예: "Kafka를 활용해 처리 속도를 50% 개선했습니다.")
3. **절대 금지**: 보기에 질문을 넣지 마십시오. 보기는 오직 사용자가 선택할 '답변'입니다.
4. 경험 데이터가 부족하면 → 경험을 더 구체화하는 질문과, 그에 맞는 유도형 답변 보기를 만드세요.
   (예 질문: "대학 시절 가장 도전적이었던 순간은?" / 예 보기: "전공 캡스톤 프로젝트에서 팀장을 맡았습니다.")

[📋 JSON 출력 형식 - 반드시 준수]
{
  "step": 1,
  "comment": "이형의 코칭 멘트 (예: 자, 냉정하게 물어볼게요~)",
  "question": "질문 하나 (짧고 날카롭게)",
  "options": [
    {"id": 1, "text": "1인칭 답변 형태의 보기"},
    {"id": 2, "text": "1인칭 답변 형태의 보기"},
    {"id": 3, "text": "1인칭 답변 형태의 보기"},
    {"id": 4, "text": "1인칭 답변 형태의 보기"}
  ]
}

[5단계 질문 흐름]
1단계: 경험 소재 선정 (기업 JD와 연결된 가장 강력한 경험)
2단계: 문제 상황 구체화 (당시 직면한 진짜 도전/문제)
3단계: 핵심 행동 (본인만의 차별화된 해결 방식)
4단계: 수치 성과 (구체적 결과 수치)
5단계: 기업 연결 (이 경험이 지원 직무에 어떻게 기여하는가)
"""

class ChatbotMentor:
    def __init__(self):
        self.model = "gpt-4o"

    def get_next_step(self, step, user_data, insights, history=None):
        if step > 5:
            return {
                "step": 5,
                "comment": "믿고 따라온 덕분에 드디어 필살기가 완성됐습니다!",
                "question": "5단계 완료! 지금 바로 자소서를 확인하세요.",
                "options": []
            }

        print(f"[ChatbotMentor] {step}단계 질문 생성 중...")
        exp = user_data.get('experiences', '') or user_data.get('experience', '') or ''
        skills = user_data.get('skills', '') or ''

        # 히스토리가 없으면 안전하게 처리
        history_text = ""
        if history:
            for h in history:
                q = h.get("question", "")
                a = h.get("answer", "")
                if q and a:
                    history_text += f"Q: {q}\nA: {a}\n"

        prompt = f"""
[사용자 경험 데이터] (이 데이터 안에서만 보기를 만드세요)
경험: {exp if exp else "아직 구체적인 경험이 입력되지 않음 → 경험을 끌어내는 질문 필요"}
기술: {skills if skills else "입력 없음"}

[기업/직무 정보]
{insights}

[이전 대화 이력]
{history_text if history_text else "없음"}

[현재 단계]: {step}/5

위 사용자 데이터를 반드시 참고하여 {step}단계에 맞는 질문과 보기를 생성하세요.
- 보기는 위 [사용자 경험 데이터]에 근거한 구체적인 1인칭 답변이어야 합니다.
- 데이터가 부족하면 "어떤 경험이 있으신가요?"식 질문을 하고, 보기는 지원자가 경험을 떠올릴 수 있는 구체적인 유도형 답변으로 만드세요.
"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            data = json.loads(response.choices[0].message.content)
            print(f"[ChatbotMentor] 응답 수신: step={data.get('step')}, options={len(data.get('options', []))}개")

            # options가 없거나 4개 미만이면 경험 기반 유도 질문으로 대체
            if not data.get("options") or len(data["options"]) < 4:
                print("[ChatbotMentor] 보기 부족 → 경험 유도형 보기로 대체")
                data["options"] = self._build_experience_based_options(exp, skills, step)

            return data

        except Exception as e:
            print(f"[ChatbotMentor] 오류: {e}")
            return {
                "step": step,
                "comment": "잠깐, 다시 정리해보겠습니다!",
                "question": f"{step}단계: 지금까지의 경험 중 가장 자신 있는 것은 무엇인가요?",
                "options": self._build_experience_based_options(exp, skills, step)
            }

    def _build_experience_based_options(self, exp: str, skills: str, step: int) -> list:
        """경험 데이터 기반 유도형 보기 생성 (Generic 보기 대체)"""
        if exp and len(exp) > 10:
            # 경험이 있으면 그것을 활용한 보기
            return [
                {"id": 1, "text": f"제 경험 중 '{exp[:20]}...'와 관련된 성과를 말씀드릴게요."},
                {"id": 2, "text": "당시 가장 어려웠던 기술적 문제를 해결한 과정을 공유할게요."},
                {"id": 3, "text": "팀 프로젝트에서 제가 주도적으로 기여한 부분을 설명할게요."},
                {"id": 4, "text": "기타 (직접 입력)"}
            ]
        else:
            # 경험이 없으면 경험 유형을 고르도록 유도
            return [
                {"id": 1, "text": "전공 수업 또는 졸업 프로젝트 경험이 있어요."},
                {"id": 2, "text": "아르바이트나 인턴 경험에서 배운 점이 있어요."},
                {"id": 3, "text": "동아리/대외 활동에서 의미 있는 성과가 있어요."},
                {"id": 4, "text": "자격증 취득이나 개인 프로젝트 경험이 있어요."}
            ]

    def finalize_letter(self, user_data, insights, selections):
        """사용자가 선택한 답변들을 하나의 유기적인 스토리로 통합하여 순수 텍스트 자소서 작성"""
        print("[ChatbotMentor] 자소서 통합 생성 (마크다운 제거 모드)...")

        selected_texts = []
        for s in selections:
            if isinstance(s, dict):
                text = s.get("selected") or s.get("text") or s.get("answer") or str(s)
            else:
                text = str(s)
            if text:
                selected_texts.append(text)

        final_prompt = f"""
[사용자 답변 데이터]
{chr(10).join([f"- {t}" for t in selected_texts])}

[기업/직무 정보]
{insights}

위 데이터를 사용하여 **마크다운 기호가 없는 순수 텍스트 형태의 통합 자소서**를 작성하세요.

[🚨 작성 가이드 - 마크다운 절대 금지]
1. **순수 텍스트 출력**: ###, **, __, - 등의 마크다운 기호를 절대 사용하지 마십시오.
2. **소제목 형식**: 맨 처음에만 단 하나의 소제목을 [소제목 내용] 형태로 작성하십시오. (예: [30% 효율 개선] 캐싱을 통한 서버 최적화)
3. **가독성**: 문단 사이에는 빈 줄을 두어 눈에 잘 들어오게 하십시오.
4. **통합 스토리**: 모든 답변을 하나의 매끄러운 흐름으로 연결하되, 중복되는 내용은 삭제하십시오.
5. **3C-4P 원칙**: 배경은 짧게, 본인의 핵심 행동과 수치화된 성과 위주로 작성하십시오.
"""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 마크다운 기호를 절대 사용하지 않는 순수 텍스트 자소서 전문 작가입니다."},
                    {"role": "user", "content": final_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"자소서 생성 중 오류 발생: {str(e)}"
