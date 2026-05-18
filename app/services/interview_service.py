## 면접 ##

import pathlib
from app.modules.chatbot_mentor import ChatbotMentor
from app.modules.evaluator_gpt import EvaluatorGPT

mentor = ChatbotMentor()
evaluator = EvaluatorGPT()

DATA_DIR = pathlib.Path(__file__).parent.parent.parent / "data"

COMPANY_FILES = {
    "네이버": "raw_data_naver.txt",
    "삼성전자": "raw_data_samsung.txt",
    "현대자동차": "raw_data_hyundai.txt",
    "카카오": "kakao_full_raw_data.txt"
}


def get_companies() -> list:
    return list(COMPANY_FILES.keys())


def load_company_data(company_name: str) -> str:
    file_name = COMPANY_FILES.get(company_name)
    if not file_name:
        return "일반적인 기업 분석 정보"
    path = DATA_DIR / file_name
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return f"{company_name}에 대한 심층 분석 데이터"


def get_next_step(step: int, user_data: dict, company_name: str, job_title: str, history: list = None) -> dict:
    insights = load_company_data(company_name)
    full_insights = f"지원 직무: {job_title}\n\n[기업 분석 정보]\n{insights}"
    return mentor.get_next_step(step, user_data, full_insights, history)


def finalize_letter(user_data: dict, company_name: str, job_title: str, question: str, selections: list) -> dict:
    insights = load_company_data(company_name)
    full_insights = f"지원 직무: {job_title}\n\n[자기소개서 문항]: {question}\n\n[기업 분석 정보]\n{insights}"
    result = mentor.finalize_letter(user_data, full_insights, selections)
    return {"final_letter": result}


def evaluate_letter(draft: str, company_name: str, question: str, char_limit: int, selections: list = None) -> dict:
    insights = load_company_data(company_name)
    context = {
        "insights": insights,
        "question": question,
        "char_limit": char_limit,
        "selections": selections or []
    }
    evaluation = evaluator.evaluate(draft, context)
    return {"evaluation": evaluation}
