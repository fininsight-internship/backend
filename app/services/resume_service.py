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


def cover_chat_next(company_name: str, job_title: str, cover_question: str, star_data: dict, history: list, company_insights: str = "") -> dict:
    return _cover_next(company_name, job_title, cover_question, star_data, history, company_insights)


def cover_chat_finalize(company_name: str, job_title: str, cover_question: str, star_data: dict, selections: list, company_insights: str = "") -> dict:
    letter = _cover_finalize(company_name, job_title, cover_question, star_data, selections, company_insights)
    return {"status": "success", "final_letter": letter}


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
