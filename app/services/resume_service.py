## 자소서 ##

from app.modules.pipeline import CoverLetterPipeline
from app.modules.cover_letter_generator import CoverLetterGenerator
from app.modules.evaluator_gpt import EvaluatorGPT
from app.modules.star_chat import get_question as _star_question, generate_summary as _star_summary
from app.modules.cover_letter_chat import get_next_step as _cover_next, generate_final_letter as _cover_finalize
from app.models.db_models import Resume, ResumeQuestion, ResumeEvaluation, ResumeQuestionEvaluation
from sqlalchemy.orm import Session

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


# ── Experience matching ───────────────────────────────────────────

def match_experiences(question: str, experiences: list) -> dict:
    """각 경험이 해당 자소서 문항에 얼마나 적합한지 매칭율(0-100)을 반환한다."""
    from google import genai
    from google.genai import types
    import os, json, re

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    exp_lines = []
    for exp in experiences:
        star = exp.get("starData") or {}
        star_text = ""
        if star:
            parts = [f"S: {star.get('S','')}", f"T: {star.get('T','')}", f"A: {star.get('A','')}", f"R: {star.get('R','')}"]
            star_text = "\n  " + "\n  ".join(p for p in parts if p.split(": ", 1)[1])
        exp_lines.append(
            f"[ID: {exp['id']}] {exp.get('company','')} / {exp.get('role','')} "
            f"| 기술: {', '.join(exp.get('tags', []))}{star_text}"
        )

    prompt = f"""자소서 문항에 대해 각 경험의 매칭율(0-100 정수)을 평가해주세요.
매칭율은 해당 경험이 이 문항을 답변하는 데 얼마나 적합한지를 나타냅니다.

[자소서 문항]
{question}

[경험 목록]
{chr(10).join(exp_lines)}

각 경험의 ID와 매칭율을 JSON 형식으로만 반환하세요. 예시: {{"1": 85, "2": 60}}
다른 텍스트 없이 JSON만 반환하세요."""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    text = response.text.strip()
    match = re.search(r'\{[^}]+\}', text, re.DOTALL)
    if match:
        scores = json.loads(match.group())
    else:
        scores = {str(exp["id"]): 50 for exp in experiences}

    return {"status": "success", "scores": scores}


# ── Resume DB CRUD (ERD 기준) ──────────────────────────────────────

def _find_or_create_resume(db: Session, user_id: int, company_name: str, job_title: str) -> Resume:
    """company_name + job_title 기준으로 resumes 행을 찾거나 생성한다.
    동시 저장으로 중복 생성된 경우 id가 가장 작은(가장 오래된) resume을 반환한다."""
    resumes = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.id).all()
    matched = [r for r in resumes
               if (r.parsed_content or {}).get("company_name") == company_name
               and (r.parsed_content or {}).get("job_title") == job_title]
    if matched:
        return matched[0]  # 중복 시 가장 오래된 것 반환
    resume = Resume(
        user_id=user_id,
        title=f"{company_name} {job_title} 자기소개서",
        parsed_content={"company_name": company_name, "job_title": job_title, "questions": []},
    )
    db.add(resume)
    db.flush()
    return resume


def get_drafts(db: Session, user_id: int, company_name: str, job_title: str) -> list:
    """해당 기업/직무의 자소서 문항 목록과 평가 결과를 반환한다."""
    resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
    resume = next(
        (r for r in resumes
         if (r.parsed_content or {}).get("company_name") == company_name
         and (r.parsed_content or {}).get("job_title") == job_title),
        None,
    )
    if not resume:
        return []

    # parsed_content.questions를 fallback으로 유지하되 rq.question_text 우선 사용
    question_texts = (resume.parsed_content or {}).get("questions", [])
    result = []
    for rq in sorted(resume.resume_questions, key=lambda x: x.question_number):
        if not rq.question_content or not rq.question_content.strip():
            continue  # 빈 content 행은 반환하지 않음
        idx = rq.question_number - 1
        q_text = rq.question_text or (question_texts[idx] if idx < len(question_texts) else "")
        latest_eval = rq.evaluations[-1] if rq.evaluations else None
        result.append({
            "id": rq.id,
            "question_text": q_text,
            "draft_content": rq.question_content or "",
            "ai_score": latest_eval.question_score if latest_eval else None,
            "ai_feedback": latest_eval.feedback or "" if latest_eval else "",
            "updated_at": rq.updated_at.isoformat() if rq.updated_at else None,
        })
    return result


def save_draft(db: Session, user_id: int, company_name: str, job_title: str,
               question_text: str, draft_content: str,
               ai_score: float = None, ai_feedback: str = None) -> dict:
    """완성된 문항별 자소서를 저장한다. 빈 내용은 저장하지 않는다."""
    # 빈 내용은 저장하지 않음
    if not draft_content or not draft_content.strip():
        return {
            "id": None,
            "question_text": question_text,
            "draft_content": "",
            "ai_score": None,
            "ai_feedback": "",
            "updated_at": None,
        }

    resume = _find_or_create_resume(db, user_id, company_name, job_title)

    # 질문 목록 동기화
    questions: list = list(resume.parsed_content.get("questions", []))
    if question_text not in questions:
        questions.append(question_text)
        resume.parsed_content = {**resume.parsed_content, "questions": questions}

    question_number = questions.index(question_text) + 1

    # resume_questions upsert (완성된 자소서 답변 저장)
    rq = next((q for q in resume.resume_questions if q.question_number == question_number), None)
    if rq:
        rq.question_text = question_text
        rq.question_content = draft_content
        rq.user_id = user_id
    else:
        rq = ResumeQuestion(
            resume_id=resume.id,
            user_id=user_id,
            question_number=question_number,
            question_text=question_text,
            question_content=draft_content,
        )
        db.add(rq)
        db.flush()

    # AI 평가 저장
    if ai_score is not None and ai_feedback is not None:
        eval_row = ResumeQuestionEvaluation(
            question_id=rq.id,
            resume_id=resume.id,
            user_id=user_id,
            question_score=ai_score,
            feedback=ai_feedback,
        )
        db.add(eval_row)
        db.flush()
        latest_eval = eval_row
    else:
        latest_eval = rq.evaluations[-1] if rq.evaluations else None

    # resumes.raw_content — 전체 자소서 조합 텍스트 갱신
    db.flush()
    all_rqs = sorted(resume.resume_questions, key=lambda x: x.question_number)
    assembled = "\n\n".join(
        f"[문항 {r.question_number}] {r.question_text or ''}\n{r.question_content or ''}"
        for r in all_rqs if r.question_content and r.question_content.strip()
    )
    resume.raw_content = assembled

    db.commit()
    db.refresh(rq)
    return {
        "id": rq.id,
        "question_text": question_text,
        "draft_content": rq.question_content or "",
        "ai_score": latest_eval.question_score if latest_eval else None,
        "ai_feedback": latest_eval.feedback or "" if latest_eval else "",
        "updated_at": rq.updated_at.isoformat() if rq.updated_at else None,
    }


def save_overall_evaluation(db: Session, user_id: int, company_name: str, job_title: str,
                            overall_feedback: str) -> dict:
    """전체 피드백 결과를 resume_evaluations 테이블에 저장한다."""
    resume = _find_or_create_resume(db, user_id, company_name, job_title)
    eval_row = ResumeEvaluation(
        resume_id=resume.id,
        overall_feedback=overall_feedback,
    )
    db.add(eval_row)
    db.commit()
    db.refresh(eval_row)
    return {"id": eval_row.id, "resume_id": resume.id}


def delete_draft(db: Session, question_id: int, user_id: int) -> bool:
    """resume_questions 행을 삭제한다 (해당 유저 소유 확인)."""
    rq = db.query(ResumeQuestion).filter(ResumeQuestion.id == question_id).first()
    if not rq:
        return False
    resume = db.query(Resume).filter(
        Resume.id == rq.resume_id,
        Resume.user_id == user_id,
    ).first()
    if not resume:
        return False
    # questions 목록에서 해당 항목 제거
    questions: list = list((resume.parsed_content or {}).get("questions", []))
    idx = rq.question_number - 1
    if 0 <= idx < len(questions):
        questions.pop(idx)
        # 이후 문항 번호 당기기
        for q in resume.resume_questions:
            if q.question_number > rq.question_number:
                q.question_number -= 1
        resume.parsed_content = {**resume.parsed_content, "questions": questions}
    db.delete(rq)
    db.commit()
    return True
