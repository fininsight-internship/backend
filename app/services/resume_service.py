## 자소서 ##

from app.modules.pipeline import CoverLetterPipeline
from app.modules.cover_letter_generator import CoverLetterGenerator
from app.modules.evaluator_gpt import EvaluatorGPT
from app.modules.star_chat import get_question as _star_question, generate_summary as _star_summary
from app.modules.cover_letter_chat import get_next_step as _cover_next, generate_final_letter as _cover_finalize

pipeline = CoverLetterPipeline()
generator = CoverLetterGenerator()
evaluator = EvaluatorGPT()


def generate_cover_letter(report_text: str, questions: list, user_info: dict, company_name: str, jd_analysis: str = "해당 없음") -> dict:
    results = pipeline.run(
        report_text=report_text,
        questions=questions,
        user_info=user_info,
        company_name=company_name,
        jd_analysis=jd_analysis
    )
    return {"status": "success", "results": results}


def evaluate_cover_letter(draft: str, context: dict) -> dict:
    evaluation_text = evaluator.evaluate(draft, context)
    scores = pipeline._parse_scores(evaluation_text)
    return {
        "status": "success",
        "evaluation": evaluation_text,
        "scores": {
            "hr": scores[0] if len(scores) > 0 else 0,
            "tech": scores[1] if len(scores) > 1 else 0
        }
    }


def refine_cover_letter(draft: str, evaluation: str, user_answers: str, context: dict) -> dict:
    combined_feedback = f"{evaluation}\n\n[사용자 추가 정보]: {user_answers}"
    refined_draft = generator.refine(draft, combined_feedback, context)
    return {"status": "success", "refined_draft": refined_draft}


def get_star_question(star_step: str, experience_name: str, experience_role: str) -> dict:
    return _star_question(star_step, experience_name, experience_role)


def generate_star_summary(experience_name: str, experience_role: str, answers: dict) -> dict:
    summary = _star_summary(experience_name, experience_role, answers)
    return {"status": "success", "summary": summary}


def cover_chat_next(company_name: str, job_title: str, cover_question: str, star_data: dict, history: list, company_insights: str = "", char_limit: int = 0) -> dict:
    return _cover_next(company_name, job_title, cover_question, star_data, history, company_insights, char_limit)


def cover_chat_finalize(company_name: str, job_title: str, cover_question: str, star_data: dict, selections: list, company_insights: str = "", char_limit: int = 0) -> dict:
    letter = _cover_finalize(company_name, job_title, cover_question, star_data, selections, company_insights, char_limit)
    return {"status": "success", "final_letter": letter}


def evaluate_all_drafts(company_name: str, job_title: str, questions: list, drafts: list) -> dict:
    """전체 자소서 통합 검토 — 반복 경험/표현 체크 + 전체 완성도 피드백"""
    from google import genai
    from google.genai import types
    import os
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    pairs = []
    for i, (q, d) in enumerate(zip(questions, drafts)):
        if d and d.strip():
            pairs.append(f"[문항 {i + 1}] {q}\n[작성 내용]\n{d.strip()}")

    if not pairs:
        return {"status": "error", "feedback": "작성된 내용이 없습니다. 최소 한 문항 이상 작성 후 다시 시도하세요."}

    combined = "\n\n" + "─" * 40 + "\n\n".join(pairs)

    prompt = f"""당신은 자기소개서 전문 컨설턴트입니다.
아래는 {company_name} {job_title} 지원을 위해 작성된 자기소개서 전체 문항입니다.

{combined}

다음 세 가지 관점에서 통합 피드백을 제공하세요.

### 🔄 반복 경험 분석
여러 문항에서 동일한 경험(프로젝트명, 사건, 역할 등)이 반복 사용되었는지 확인하고,
반복된 경우 어떤 문항에서 어떻게 겹쳤는지 구체적으로 지적하세요.
문제가 없으면 "반복 경험 없음" 으로 작성하세요.

### 📝 반복 표현 분석
"열심히", "최선을 다해", "성장했습니다" 같이 여러 문항에서 동일하거나 유사한 표현이
반복 사용된 경우를 모두 찾아서 지적하고, 대안 표현을 제시하세요.
문제가 없으면 "반복 표현 없음" 으로 작성하세요.

### 💡 전체 완성도 평가
전체 자기소개서를 보았을 때 지원자의 강점이 일관성 있게 드러나는지,
각 문항이 서로 보완적인 내용을 담고 있는지 종합 평가하고
가장 우선적으로 개선해야 할 1~2가지 사항을 제시하세요.
"""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return {"status": "success", "feedback": response.text}


def evaluate_detailed(draft: str, company_name: str, job_title: str, cover_question: str,
                      selections: list = None, company_insights: str = "") -> dict:
    context = {
        "selections": selections or [],
        "insights": company_insights or f"{company_name} {job_title}",
        "question": cover_question,
    }
    evaluation_text = evaluator.evaluate(draft, context)
    total_score = evaluator.parse_total_score(evaluation_text)
    return {
        "status": "success",
        "evaluation": evaluation_text,
        "total_score": total_score,
    }
