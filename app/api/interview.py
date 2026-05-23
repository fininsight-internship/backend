## 면접 준비 API (RAG + 평가축 기반 PoC) ##
import os
import json
import re
import uuid
import hashlib
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
import anthropic
from google import genai as google_genai
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.db_models import User, InterviewSession, InterviewQuestion, FollowUpQuestion, CompanyJDAnalysis, Resume, InterviewEvaluationAxisCache
from app.services.interview_rag_data import (
    FEATURE_TAXONOMY,
    AVAILABLE_POSITIONS,
    compute_feature_weights,
    retrieve_context,
    tag_features,
)

load_dotenv()

# ─── LLM Clients ───────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

client = openai_client  # backward-compat alias
router = APIRouter(prefix="/interview")

# ─── Current User Helper ───────────────────────────────────────
def get_current_user(
    db: Session,
    x_user_id: Optional[str] = None,
    x_user_email: Optional[str] = None
) -> User:
    """헤더 정보를 기반으로 로그인된 유저를 식별하며, 없는 경우 폴백 유저를 반환합니다."""
    # 1. X-User-Id 우선 식별
    if x_user_id:
        try:
            user = db.query(User).filter(User.id == int(x_user_id)).first()
            if user:
                return user
        except ValueError:
            pass

    # 2. X-User-Email 식별
    if x_user_email:
        user = db.query(User).filter(User.email == x_user_email.strip().lower()).first()
        if user:
            return user

    # 3. 폴백: DB 내에 등록된 첫 유저 반환
    user = db.query(User).first()
    if user:
        return user

    # 4. 폴백 2: DB가 비어있는 경우 디폴트 영구 사용자 생성 및 반환
    default_email = "dbeaver_test@careerai.com"
    user = db.query(User).filter(User.email == default_email).first()
    if not user:
        user = User(
            email=default_email,
            password_hash="hashed_password_12345",
            name="디비버길동",
            role="풀스택 개발자"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user



# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────
class PositionSelectRequest(BaseModel):
    position_id: str


class QuestionRequest(BaseModel):
    company: str
    job_role: str
    interview_type: Optional[str] = "전체"
    axis_type: Optional[str] = "static"
    analysis_id: Optional[int] = None
    resume_id: Optional[int] = None


class AdditionalQuestionRequest(BaseModel):
    company: str
    job_role: str
    interview_type: Optional[str] = "전체"
    analysis_id: Optional[int] = None
    resume_id: Optional[int] = None
    selected_axes: List[Dict[str, Any]]
    question_count: int
    existing_questions: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    company: str
    job_role: str
    question: str
    user_answer: str
    feature_weights: Optional[Dict[str, float]] = None
    evaluation_axes: Optional[List[Dict[str, Any]]] = None
    analysis_id: Optional[int] = None
    resume_id: Optional[int] = None


class FollowUpRequest(BaseModel):
    company: str
    job_role: str
    question: str
    user_answer: str
    resume_excerpt: Optional[str] = None
    analysis_id: Optional[int] = None
    resume_id: Optional[int] = None
class FollowUpFeedbackRequest(BaseModel):
    company: str
    job_role: str
    original_question: str
    follow_up_question: str
    follow_up_intent: str
    user_answer: str


class AnswerItem(BaseModel):
    id: str
    question: str
    category: str
    tips: str
    evaluation_axis: Optional[str] = None
    axis_name: Optional[str] = None
    evaluation_axes: Optional[List[Dict[str, Any]]] = None
    userAnswer: str
    feedback: Optional[str] = None
    followUps: Optional[List[dict]] = None


class EvaluationAxisItem(BaseModel):
    key: str
    name: str
    description: str
    weight: Optional[float] = None


class SaveSessionRequest(BaseModel):
    session_id: Optional[str] = None
    company: str
    job_role: str
    interview_type: Optional[str] = "전체"
    axis_type: Optional[str] = "static"
    axes_used: Optional[List[EvaluationAxisItem]] = None
    answers: List[AnswerItem]


# ─────────────────────────────────────────────────────────────
# Helper: LLM 호출 공통 함수 (3개 모델)
# ─────────────────────────────────────────────────────────────
def _call_claude(prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
    """질문/평가축 생성에 사용 (Claude 3.5 Sonnet)"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY가 .env에 없습니다.")
    msg = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return msg.content[0].text


def _call_gemini(prompt: str, max_tokens: int = 1200, temperature: float = 0.7) -> str:
    """압박 꼬리질문 생성에 사용 (Gemini 2.0 Flash)"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 .env에 없습니다.")
    gemini_client = google_genai.Client(api_key=api_key)
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text


def _call_openai(prompt: str, max_tokens: int = 1200, temperature: float = 0.7) -> str:
    """답변 평가/피드백에 사용 (GPT-4o)"""
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def _call_llm(prompt: str, max_tokens: int = 1200, temperature: float = 0.7) -> str:
    """하위 호환 alias — 기본값은 GPT-4o"""
    return _call_openai(prompt, max_tokens, temperature)


def _extract_json(raw: str) -> Any:
    """LLM 응답에서 JSON 파싱 (코드블록 제거 포함)"""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
    if match:
        cleaned = match.group()
    return json.loads(cleaned)


def _compact_json(data: Any) -> str:
    """프롬프트 컨텍스트용으로 JSON 데이터를 짧고 안정적으로 직렬화합니다."""
    if not data:
        return ""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _serialize_analysis(row: CompanyJDAnalysis) -> dict:
    report = row.analysis_report or {}
    return {
        "id": row.id,
        "company_name": row.company_name,
        "job_role": row.job_role,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "company_analysis": report.get("company_analysis", {}),
        "job_analysis": report.get("job_analysis", {}),
        "fit_analysis": report.get("fit_analysis", {}),
        "document_optimization": report.get("document_optimization", {}),
    }


def _normalize_interview_type(interview_type: Optional[str]) -> str:
    return interview_type if interview_type in {"인성", "실무"} else "전체"


def _axis_generation_guidance(interview_type: Optional[str]) -> str:
    normalized = _normalize_interview_type(interview_type)
    if normalized == "인성":
        return """
이번 평가축은 인성 면접용입니다.
기술 지식이나 구현 역량이 아니라 지원자의 태도, 협업 방식, 가치관, 성장 가능성, 커뮤니케이션, 조직 적응력을 평가하는 축으로 구성하세요.
예: 자기이해와 회고, 협업과 갈등 해결, 지원 동기와 조직 적합성, 성장 의지, 커뮤니케이션 균형, 책임감과 태도
"""
    if normalized == "실무":
        return """
이번 평가축은 실무 면접용입니다.
지원자의 직무 수행 능력, 문제 해결력, 프로젝트 수행 경험, 설계/구조화 능력, 성과와 임팩트를 평가하는 축으로 구성하세요.
예: 직무/기술 역량, 문제 해결력, 프로젝트 실행력, 설계/구조화, 성과/임팩트, 실무 협업 방식
"""
    return """
이번 평가축은 혼합 면접용입니다.
인성 면접과 실무 면접에서 모두 활용할 수 있는 균형 잡힌 평가축으로 구성하세요.
"""


def _analysis_signature(row: CompanyJDAnalysis, axis_type: str, interview_type: Optional[str] = "전체") -> str:
    report = row.analysis_report or {}
    payload = {
        "axis_type": axis_type,
        "interview_type": _normalize_interview_type(interview_type),
        "company_name": row.company_name,
        "job_role": row.job_role,
        "jd_content": row.jd_content or "",
        "company_analysis": report.get("company_analysis", {}),
        "job_analysis": report.get("job_analysis", {}),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _serialize_resume(row: Resume) -> dict:
    parsed = row.parsed_content or {}
    questions = []
    for q in sorted(row.resume_questions, key=lambda x: x.question_number):
        questions.append({
            "id": q.id,
            "question_text": q.question_text or "",
            "draft_content": q.question_content or "",
        })

    return {
        "id": row.id,
        "title": row.title,
        "company_name": parsed.get("company_name") or "",
        "job_role": parsed.get("job_title") or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "raw_content": row.raw_content or "",
        "questions": questions,
    }


def _resume_to_text(row: Resume) -> str:
    data = _serialize_resume(row)
    if data["raw_content"]:
        return data["raw_content"]
    parts = []
    for idx, q in enumerate(data["questions"], start=1):
        if q["question_text"] or q["draft_content"]:
            parts.append(f"[문항 {idx}] {q['question_text']}\n{q['draft_content']}")
    return "\n\n".join(parts)


def _compute_weights_from_context(ctx: dict, include_resume: bool = False) -> Dict[str, float]:
    weighted_sources = [
        (ctx.get("jd", ""), 1.0),
        (ctx.get("company_analysis", ""), 0.95),
    ]
    if include_resume:
        weighted_sources.append((ctx.get("resume", ""), 1.0))
    aggregated: Dict[str, float] = {}
    for text, trust in weighted_sources:
        for key, count in tag_features(text).items():
            aggregated[key] = aggregated.get(key, 0) + count * trust

    if not aggregated:
        return {}
    max_val = max(aggregated.values())
    if max_val == 0:
        return {}
    return {k: round(v / max_val, 3) for k, v in sorted(aggregated.items(), key=lambda x: -x[1])}


def _build_db_context(
    db: Session,
    current_user: User,
    company: str,
    job_role: str,
    analysis_id: Optional[int] = None,
    resume_id: Optional[int] = None,
) -> dict:
    """
    선택된 JD/기업분석과 자소서를 DB에서 읽어 면접 RAG 컨텍스트로 구성합니다.
    선택값이 없으면 기존 mock RAG 컨텍스트를 폴백으로 유지합니다.
    """
    ctx = {
        "jd": "",
        "company_analysis": "",
        "resume": "",
        "all_combined": "",
        "sources": [],
    }

    analysis = None
    if analysis_id:
        analysis = db.query(CompanyJDAnalysis).filter(
            CompanyJDAnalysis.id == analysis_id,
            CompanyJDAnalysis.user_id == current_user.id,
        ).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="선택한 JD/기업분석 데이터를 찾을 수 없습니다.")

    resume = None
    if resume_id:
        resume = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        ).first()
        if not resume:
            raise HTTPException(status_code=404, detail="선택한 자소서 데이터를 찾을 수 없습니다.")

    if analysis:
        report = analysis.analysis_report or {}
        ctx["jd"] = analysis.jd_content or ""
        ctx["company_analysis"] = "\n\n".join([
            "[기업 분석]",
            _compact_json(report.get("company_analysis", {})),
            "[JD 분석]",
            _compact_json(report.get("job_analysis", {})),
            "[적합도 분석]",
            _compact_json(report.get("fit_analysis", {})),
            "[문서 최적화]",
            _compact_json(report.get("document_optimization", {})),
        ]).strip()
        ctx["sources"].append({
            "id": f"analysis-{analysis.id}",
            "label": f"JD/기업분석: {analysis.company_name} · {analysis.job_role}",
        })

    if resume:
        ctx["resume"] = _resume_to_text(resume)
        ctx["sources"].append({
            "id": f"resume-{resume.id}",
            "label": f"자소서: {resume.title}",
        })

    if not analysis and not resume:
        return retrieve_context(company, job_role)

    ctx["all_combined"] = "\n\n---\n\n".join(
        part for part in [
            f"[채용공고]\n{ctx['jd']}" if ctx["jd"] else "",
            f"[기업/JD 분석]\n{ctx['company_analysis']}" if ctx["company_analysis"] else "",
            f"[자기소개서]\n{ctx['resume']}" if ctx["resume"] else "",
        ] if part
    )
    return ctx


def _get_required_analysis(db: Session, current_user: User, analysis_id: Optional[int]) -> CompanyJDAnalysis:
    if not analysis_id:
        raise HTTPException(status_code=400, detail="면접 질문 생성을 위해 JD/기업분석 선택이 필요합니다.")
    analysis = db.query(CompanyJDAnalysis).filter(
        CompanyJDAnalysis.id == analysis_id,
        CompanyJDAnalysis.user_id == current_user.id,
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="선택한 JD/기업분석 데이터를 찾을 수 없습니다.")
    return analysis


def _static_axes_from_weights(weights: Dict[str, float]) -> List[dict]:
    axes = []
    for key, score in list(weights.items())[:6]:
        if key in FEATURE_TAXONOMY:
            axes.append({
                "key": key,
                "name": FEATURE_TAXONOMY[key]["name"],
                "description": FEATURE_TAXONOMY[key]["description"],
                "weight": score,
            })
    return axes


def _static_axes_for_interview_type(weights: Dict[str, float], interview_type: Optional[str]) -> List[dict]:
    normalized = _normalize_interview_type(interview_type)
    if normalized == "인성":
        return [
            {"key": "self_reflection", "name": "자기이해와 회고", "description": "본인의 강점·약점·실패 경험을 객관적으로 인식하고 개선하려는 태도", "weight": 1.0},
            {"key": "collaboration_conflict", "name": "협업과 갈등 해결", "description": "팀 안에서 의견 차이를 조율하고 갈등을 건설적으로 해결하는 방식", "weight": 0.95},
            {"key": "motivation_fit", "name": "지원 동기와 조직 적합성", "description": "회사와 직무를 선택한 이유의 진정성 및 조직 문화와의 적합성", "weight": 0.9},
            {"key": "growth_mindset", "name": "성장 의지", "description": "피드백 수용, 학습 태도, 장기적 커리어 방향성", "weight": 0.85},
            {"key": "communication_balance", "name": "커뮤니케이션 균형", "description": "상대방을 존중하면서 자신의 의견을 명확히 전달하는 능력", "weight": 0.8},
            {"key": "responsibility_attitude", "name": "책임감과 태도", "description": "어려운 상황에서 책임을 회피하지 않고 끝까지 해결하려는 태도", "weight": 0.75},
        ]
    if normalized == "실무":
        base_axes = _static_axes_from_weights(weights)
        if base_axes:
            return base_axes
        return [
            {"key": "technical_competency", "name": "직무/기술 역량", "description": "직무 수행에 필요한 기술 지식과 실무 적용 능력", "weight": 1.0},
            {"key": "problem_solving", "name": "문제 해결력", "description": "문제 원인을 구조적으로 파악하고 해결책을 실행하는 능력", "weight": 0.95},
            {"key": "project_execution", "name": "프로젝트 실행력", "description": "프로젝트에서 맡은 역할, 의사결정, 실행 과정을 설명하는 능력", "weight": 0.9},
            {"key": "system_design", "name": "설계/구조화", "description": "요구사항을 구조화하고 확장 가능한 방식으로 설계하는 능력", "weight": 0.85},
            {"key": "impact", "name": "성과/임팩트", "description": "업무 결과를 수치나 사용자/비즈니스 효과로 설명하는 능력", "weight": 0.8},
            {"key": "practical_collaboration", "name": "실무 협업", "description": "리뷰, 일정 조율, 커뮤니케이션을 통해 결과물을 완성하는 능력", "weight": 0.75},
        ]
    return _static_axes_from_weights(weights)


def _get_cached_or_create_axes(
    db: Session,
    analysis: CompanyJDAnalysis,
    ctx: dict,
    axis_type: str,
    interview_type: Optional[str] = "전체",
) -> tuple[Dict[str, float], List[dict], Dict[str, str]]:
    """
    평가축은 JD/기업분석만 사용해 산출하고 source signature 기준으로 캐시합니다.
    자소서는 질문 내용 생성에는 쓰지만 평가 기준 산출에는 절대 쓰지 않습니다.
    """
    normalized_axis_type = axis_type if axis_type in {"static", "dynamic"} else "static"
    normalized_interview_type = _normalize_interview_type(interview_type)
    signature = _analysis_signature(analysis, normalized_axis_type, normalized_interview_type)
    cached = db.query(InterviewEvaluationAxisCache).filter(
        InterviewEvaluationAxisCache.source_signature == signature
    ).first()
    if cached:
        axes = cached.axes or []
        weights = cached.feature_weights or {ax.get("key"): ax.get("weight", 0) for ax in axes}
        dynamic_map = {ax.get("key"): ax.get("name") for ax in axes if ax.get("key") and ax.get("name")}
        return weights, axes, dynamic_map

    weights = _compute_weights_from_context(ctx, include_resume=False) or compute_feature_weights(
        analysis.company_name,
        analysis.job_role,
    )
    dynamic_map: Dict[str, str] = {}

    if normalized_axis_type == "dynamic":
        axes_prompt = f"""
당신은 기업 면접관입니다. 아래 JD와 기업분석 데이터를 바탕으로 해당 직무에 필요한 핵심 평가축(역량) 6가지를 동적으로 추출하세요.
평가축은 지원자 개인 자소서가 아니라 채용공고와 기업/직무 분석 기준에서만 도출해야 합니다.
{_axis_generation_guidance(normalized_interview_type)}

[지원 기업] {analysis.company_name}
[지원 직무] {analysis.job_role}
[채용공고 핵심 요약] {ctx['jd']}
[기업 분석 레포트 요약] {ctx['company_analysis']}

반드시 JSON 배열 형태로 출력하세요.
[
  {{
    "key": "영문키워드",
    "name": "평가축 이름",
    "description": "평가축 설명",
    "weight": 1.0
  }}
]
"""
        try:
            try:
                raw_axes = _call_claude(axes_prompt, max_tokens=1000, temperature=0.7)
                print("✅ Claude로 동적 평가축 생성 완료")
            except Exception as claude_err:
                print(f"⚠️ Claude 동적 평가축 생성 실패, GPT로 폴백: {claude_err}")
                raw_axes = _call_openai(axes_prompt, max_tokens=1000, temperature=0.7)
            axes = _extract_json(raw_axes)
            weights = {ax["key"]: ax.get("weight", 1.0) for ax in axes}
            dynamic_map = {ax["key"]: ax["name"] for ax in axes}
        except Exception as e:
            print("동적 평가축 추출 실패, 정적 평가축으로 폴백:", e)
            axes = _static_axes_for_interview_type(weights, normalized_interview_type)
            dynamic_map = {ax["key"]: ax["name"] for ax in axes}
    else:
        axes = _static_axes_for_interview_type(weights, normalized_interview_type)
        dynamic_map = {ax["key"]: ax["name"] for ax in axes}

    cache = InterviewEvaluationAxisCache(
        source_signature=signature,
        company_name=analysis.company_name,
        job_role=analysis.job_role,
        axis_type=f"{normalized_axis_type}:{normalized_interview_type}",
        axes=axes,
        feature_weights=weights,
    )
    db.add(cache)
    db.commit()

    return weights, axes, dynamic_map


# ─────────────────────────────────────────────────────────────
# 엔드포인트 1: 지원 가능한 포지션 목록
# ─────────────────────────────────────────────────────────────
@router.get("/positions")
def get_positions():
    """
    서비스 내에서 분석된 기업-직무 포지션 목록 반환.
    (PoC: KoDATA 1건 하드코딩)
    """
    return AVAILABLE_POSITIONS


@router.get("/sources")
def get_interview_sources(
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
):
    """면접 질문 생성에 사용할 DB 저장 JD/기업분석 목록과 자소서 목록을 반환합니다."""
    current_user = get_current_user(db, x_user_id, x_user_email)

    analyses = db.query(CompanyJDAnalysis).filter(
        CompanyJDAnalysis.user_id == current_user.id
    ).order_by(CompanyJDAnalysis.created_at.desc()).all()

    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.updated_at.desc(), Resume.created_at.desc()).all()

    return {
        "analyses": [_serialize_analysis(item) for item in analyses],
        "resumes": [_serialize_resume(item) for item in resumes],
    }


# ─────────────────────────────────────────────────────────────
# 엔드포인트 2: 평가축 추론 (feature weights)
# ─────────────────────────────────────────────────────────────
@router.post("/evaluate-axes")
def evaluate_axes(
    req: QuestionRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
):
    """
    JD + 기업분석 레포트만 기준으로 평가축을 계산하고 캐시된 결과를 반환합니다.
    자소서는 질문 내용에는 활용될 수 있지만 평가축 산출 기준에서는 제외됩니다.
    """
    current_user = get_current_user(db, x_user_id, x_user_email)
    analysis = _get_required_analysis(db, current_user, req.analysis_id)
    ctx = _build_db_context(db, current_user, analysis.company_name, analysis.job_role, req.analysis_id, None)
    weights, axes, _ = _get_cached_or_create_axes(db, analysis, ctx, req.axis_type or "static", req.interview_type)

    return {
        "company": analysis.company_name,
        "job_role": analysis.job_role,
        "evaluation_axes": axes,
        "sources": ctx["sources"],
        "feature_weights": weights,
        "note": "평가축은 JD·기업분석 데이터 기반 추론 결과이며 캐시되어 동일 분석 기준에서 재사용됩니다. 자소서는 평가축 산출에 포함하지 않습니다.",
    }


# ─────────────────────────────────────────────────────────────
# 엔드포인트 3: 면접 질문 생성 (RAG + 평가축 기반)
# ─────────────────────────────────────────────────────────────
@router.post("/questions")
def get_interview_questions(
    req: QuestionRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
):
    """
    RAG로 JD + 기업분석 + 자소서를 retrieval하고,
    평가축 weight 또는 동적 평가축 기반으로 맞춤형 면접 질문 5개를 생성합니다.
    """
    # 1) RAG retrieval
    current_user = get_current_user(db, x_user_id, x_user_email)
    analysis = _get_required_analysis(db, current_user, req.analysis_id)
    ctx = _build_db_context(db, current_user, analysis.company_name, analysis.job_role, req.analysis_id, req.resume_id)
    weights, axes_used_info, dynamic_axis_map = _get_cached_or_create_axes(
        db,
        analysis,
        ctx,
        req.axis_type or "static",
        req.interview_type,
    )
    axes_desc = "\n".join(
        [f"- {ax.get('name')}: {ax.get('description')} (weight: {ax.get('weight', 0)})" for ax in axes_used_info]
    )
                
    # 3) 면접 유형에 따른 조건 추가
    type_condition = ""
    type_specific_requirement = ""
    if req.interview_type == "인성":
        type_condition = (
            "3. 반드시 5개 질문 모두 인성 면접 카테고리 중 하나로만 생성하세요: "
            "behavioral(인성/경험), situational(상황 판단), values(가치관), "
            "growth(성장 가능성), communication(커뮤니케이션)."
        )
        type_specific_requirement = """
4. 기술 지식, 프레임워크, 구현 방법, 코딩/설계 세부 지식을 직접 검증하는 질문은 만들지 마세요.
5. 아래 인성 면접 대표 질문 흐름을 참고해 지원자의 태도와 사고방식을 확인하는 질문으로 구성하세요:
   - 자기소개: 커뮤니케이션 능력, 경험 정리 능력, 첫인상 확인
   - 장점과 단점: 자기 객관화 능력, 단점 개선 노력 확인
   - 힘들었던 경험과 극복 과정: 문제 해결 방식, 멘탈, 태도 확인
   - 팀 프로젝트 갈등 경험: 협업 스타일, 갈등 해결 방식 확인
   - 회사 지원 동기: 지원 동기 진정성, 기업 이해도 확인
   - 직무 선택 이유: 직무 적합성, 커리어 방향성 확인
   - 실패 경험: 책임 회피 여부, 회고 능력 확인
   - 부당한 지시 대응: 조직 적응력, 커뮤니케이션 균형 확인
   - 동료와 의견 차이: 설득 방식, 협업 태도 확인
   - 5년 후 모습: 성장 의지, 장기적 방향성 확인
6. 직무와 기업 맥락은 질문의 배경으로만 활용하고, 답변에서 기술 정답을 요구하지 마세요.
"""
    elif req.interview_type == "실무":
        type_condition = (
            "3. 반드시 5개 질문 모두 실무 면접 카테고리 중 하나로만 생성하세요: "
            "technical(직무/기술), problem_solving(문제 해결), project(프로젝트), "
            "design(설계/구조화), impact(성과/임팩트)."
        )
        type_specific_requirement = "4. 이 직무의 약점으로 분석된 지식 검증 질문 1개 이상 포함"
    else:
        type_condition = (
            "3. 카테고리: behavioral, situational, values, growth, communication, "
            "technical, problem_solving, project, design, impact 중 질문 목적에 맞게 선택하세요."
        )
        type_specific_requirement = "4. 이 직무의 약점으로 분석된 지식 검증 질문 1개 이상 포함"

    prompt = f"""
당신은 기업 면접관입니다. 아래 데이터를 참조하여 지원자에게 할 면접 질문을 생성하세요.

[지원 기업] {analysis.company_name}
[지원 직무] {analysis.job_role}

[RAG 기반 검색 결과 - 채용공고 핵심 요약]
{ctx['jd']}

[RAG 기반 검색 결과 - 기업 분석 레포트 핵심 요약]
{ctx['company_analysis']}

[RAG 기반 검색 결과 - 지원자 자기소개서]
{ctx['resume']}

[분석된 핵심 평가축]
{axes_desc}

위 데이터를 반드시 참조하여, 아래 조건에 맞게 면접 질문 5개를 생성하세요:

조건:
1. 선택된 자소서가 있으면 자소서에서 언급된 구체적 경험을 직접 검증하는 질문을 포함하세요. 자소서가 비어 있으면 JD/기업분석 기반 질문으로 구성하세요.
2. 제시된 핵심 평가축 중심으로 질문을 강화하되, 평가축 자체는 JD/기업분석 기준으로만 해석하세요.
{type_condition}
{type_specific_requirement}
7. evaluation_axis 필드에 해당 질문이 검증하는 평가축 key를 명시
8. tips 필드에는 단순한 일반 조언이 아니라, 해당 evaluation_axis의 평가기준 중 어떤 세부 포인트를 면접관이 집중해서 보는지 1~2문장으로 서술하세요.

반드시 아래 JSON 배열 형식으로만 출력하세요. 설명, 인사말, 코드블록(```) 절대 출력 금지.

[
  {{
    "id": "question-1",
    "question": "질문 내용 (자소서 경험 기반 구체적으로)",
    "category": "behavioral | situational | values | growth | communication | technical | problem_solving | project | design | impact",
    "evaluation_axis": "평가축 key",
    "tips": "이 평가기준 안에서 면접관이 집중해서 확인하려는 세부 포인트"
  }}
]
"""

    # ① Claude 3.5 Sonnet — 질문/평가축 생성
    try:
        try:
            raw = _call_claude(prompt, max_tokens=2000, temperature=0.7)
            print("✅ Claude로 질문 생성 완료")
        except Exception as claude_err:
            print(f"⚠️ Claude 실패, GPT로 폴백: {claude_err}")
            raw = _call_openai(prompt, max_tokens=2000, temperature=0.7)

        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            parsed = parsed.get("questions", [])

        for item in parsed:
            item["id"] = f"q-{uuid.uuid4().hex[:8]}"
            axis_key = item.get("evaluation_axis", "")
            
            matched = False
            # 1) 캐시된 평가축 매칭 시도 (key 또는 name 매칭)
            for ax in axes_used_info:
                if ax.get("key") == axis_key or ax.get("name") == axis_key:
                    item["axis_name"] = ax.get("name")
                    item["axis_weight"] = ax.get("weight", 0.0)
                    item["evaluation_axis"] = ax.get("key", axis_key)
                    matched = True
                    break
            
            # 2) 정적/기본 평가축 매칭 시도
            if not matched:
                if axis_key in FEATURE_TAXONOMY:
                    item["axis_name"] = FEATURE_TAXONOMY[axis_key]["name"]
                    item["axis_weight"] = weights.get(axis_key, 0.0)
                else:
                    # 한국어 name으로 들어왔을 경우 매칭
                    for k, v in FEATURE_TAXONOMY.items():
                        if v["name"] == axis_key:
                            item["axis_name"] = v["name"]
                            item["axis_weight"] = weights.get(k, 0.0)
                            matched = True
                            break

        return {
            "questions": parsed,
            "feature_weights": weights,
            "sources": ctx["sources"],
            "axes_used": axes_used_info
        }

    except Exception as e:
        print("❌ 질문 생성 에러:", e)
        raise HTTPException(status_code=500, detail=f"질문 생성 실패: {str(e)}")


@router.post("/questions/additional")
def get_additional_interview_questions(
    req: AdditionalQuestionRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
):
    """
    기존 면접 세션에서 선택한 평가축 기준으로 추가 질문을 생성합니다.
    """
    selected_axes = [ax for ax in req.selected_axes if ax.get("key") and ax.get("name")]
    if not selected_axes:
        raise HTTPException(status_code=400, detail="평가 기준을 1개 이상 선택해주세요.")

    question_count = max(1, min(req.question_count, 10))
    if question_count < len(selected_axes):
        raise HTTPException(status_code=400, detail="생성 개수는 선택한 평가 기준 개수 이상이어야 합니다.")

    current_user = get_current_user(db, x_user_id, x_user_email)
    ctx = _build_db_context(db, current_user, req.company, req.job_role, req.analysis_id, req.resume_id)
    axes_desc = "\n".join([
        f"- key: {ax.get('key')}, name: {ax.get('name')}, description: {ax.get('description', '')}, weight: {ax.get('weight', 0)}"
        for ax in selected_axes
    ])
    existing_questions = "\n".join([f"- {q}" for q in (req.existing_questions or []) if q.strip()])

    type_specific_requirement = ""
    if req.interview_type == "인성":
        type_condition = (
            "모든 질문은 인성 면접 카테고리 중 하나로만 생성하세요: "
            "behavioral(인성/경험), situational(상황 판단), values(가치관), "
            "growth(성장 가능성), communication(커뮤니케이션)."
        )
        type_specific_requirement = """
5. 기술 지식, 프레임워크, 구현 방법, 코딩/설계 세부 지식을 직접 검증하는 질문은 만들지 마세요.
6. 아래 인성 면접 대표 질문 흐름을 참고해 지원자의 태도와 사고방식을 확인하는 질문으로 구성하세요:
   - 자기소개: 커뮤니케이션 능력, 경험 정리 능력, 첫인상 확인
   - 장점과 단점: 자기 객관화 능력, 단점 개선 노력 확인
   - 힘들었던 경험과 극복 과정: 문제 해결 방식, 멘탈, 태도 확인
   - 팀 프로젝트 갈등 경험: 협업 스타일, 갈등 해결 방식 확인
   - 회사 지원 동기: 지원 동기 진정성, 기업 이해도 확인
   - 직무 선택 이유: 직무 적합성, 커리어 방향성 확인
   - 실패 경험: 책임 회피 여부, 회고 능력 확인
   - 부당한 지시 대응: 조직 적응력, 커뮤니케이션 균형 확인
   - 동료와 의견 차이: 설득 방식, 협업 태도 확인
   - 5년 후 모습: 성장 의지, 장기적 방향성 확인
7. 선택된 평가 기준은 인성 질문의 관찰 관점으로만 사용하고, 기술 정답을 요구하지 마세요.
"""
    elif req.interview_type == "실무":
        type_condition = (
            "모든 질문은 실무 면접 카테고리 중 하나로만 생성하세요: "
            "technical(직무/기술), problem_solving(문제 해결), project(프로젝트), "
            "design(설계/구조화), impact(성과/임팩트)."
        )
        type_specific_requirement = "5. 선택된 평가 기준이 직무 역량과 어떻게 연결되는지 구체적으로 검증하세요."
    else:
        type_condition = (
            "질문 목적에 맞게 behavioral, situational, values, growth, communication, "
            "technical, problem_solving, project, design, impact 중 하나를 선택하세요."
        )
        type_specific_requirement = "5. 선택된 평가 기준이 질문에서 분명히 드러나게 작성하세요."

    prompt = f"""
당신은 기업 면접관입니다. 기존 면접에 이어서 추가 질문을 생성하세요.

[지원 기업] {req.company}
[지원 직무] {req.job_role}

[채용공고 핵심 요약]
{ctx['jd']}

[기업/JD 분석 요약]
{ctx['company_analysis']}

[지원자 자기소개서]
{ctx['resume']}

[선택된 평가 기준]
{axes_desc}

[이미 생성된 질문]
{existing_questions}

조건:
1. 총 {question_count}개의 질문을 생성하세요.
2. 선택된 평가 기준을 모두 최소 1번 이상 사용하세요.
3. 기존 질문과 의미가 중복되지 않게 생성하세요.
4. {type_condition}
{type_specific_requirement}
8. evaluation_axis 필드에는 반드시 선택된 평가 기준의 key 중 하나만 넣으세요.
9. tips 필드에는 해당 평가 기준에서 면접관이 집중해서 확인할 포인트를 1~2문장으로 작성하세요.

반드시 아래 JSON 배열 형식으로만 출력하세요. 설명, 인사말, 코드블록(```) 절대 출력 금지.

[
  {{
    "id": "question-1",
    "question": "질문 내용",
    "category": "behavioral | situational | values | growth | communication | technical | problem_solving | project | design | impact",
    "evaluation_axis": "선택된 평가 기준 key",
    "tips": "면접관 확인 포인트"
  }}
]
"""

    try:
        try:
            raw = _call_claude(prompt, max_tokens=1800, temperature=0.7)
            print("✅ Claude로 추가 질문 생성 완료")
        except Exception as claude_err:
            print(f"⚠️ Claude 실패, GPT로 폴백: {claude_err}")
            raw = _call_openai(prompt, max_tokens=1800, temperature=0.7)

        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            parsed = parsed.get("questions", [])

        axis_map = {ax.get("key"): ax for ax in selected_axes}
        for item in parsed:
            item["id"] = f"q-{uuid.uuid4().hex[:8]}"
            axis_key = item.get("evaluation_axis", "")
            axis = axis_map.get(axis_key) or selected_axes[0]
            item["evaluation_axis"] = axis.get("key")
            item["axis_name"] = axis.get("name")
            item["axis_weight"] = axis.get("weight", 0.0)

        return {
            "questions": parsed[:question_count],
            "sources": ctx["sources"],
        }

    except Exception as e:
        print("❌ 추가 질문 생성 에러:", e)
        raise HTTPException(status_code=500, detail=f"추가 질문 생성 실패: {str(e)}")


@router.post("/follow-up/feedback")
def get_follow_up_feedback(req: FollowUpFeedbackRequest):
    """
    꼬리질문에 대한 사용자의 답변을 평가합니다.
    꼬리질문을 한 의도를 잘 파악했는지 위주로 2~3문장 간략 피드백 반환.
    """
    prompt = f"""
당신은 엄격한 면접관입니다. 앞서 지원자에게 던진 꼬리질문에 대한 답변을 평가하세요.

[원래 질문] {req.original_question}
[꼬리질문 내용] {req.follow_up_question}
[꼬리질문 의도] {req.follow_up_intent}
[지원자의 꼬리질문 답변] {req.user_answer}

지원자가 꼬리질문의 의도를 정확히 파악하고 설득력 있게 대답했는지 평가하여,
아래 JSON 형식으로만 응답하세요. (불필요한 텍스트 금지)

{{
  "feedback": "꼬리질문 의도 파악 여부 및 답변 퀄리티에 대한 간략한 핵심 피드백 (2~3문장)"
}}
"""
    try:
        # ③ GPT-4o — 꼬리질문 의도 파악력 평가
        try:
            raw = _call_openai(prompt, max_tokens=300, temperature=0.5)
            print("✅ GPT-4o로 꼬리질문 피드백 완료")
        except Exception as gpt_err:
            print(f"⚠️ GPT 실패, Claude로 폴백: {gpt_err}")
            raw = _call_claude(prompt, max_tokens=300, temperature=0.5)
        result = _extract_json(raw)
        return result
    except Exception as e:
        print("❌ 꼬리질문 피드백 에러:", e)
        raise HTTPException(status_code=500, detail=f"꼬리질문 피드백 생성 실패: {str(e)}")


# ─────────────────────────────────────────────────────────────
# 엔드포인트 4: 답변 평가 + 감점 리스크 분석
# ─────────────────────────────────────────────────────────────
@router.post("/feedback")
def get_answer_feedback(
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
):
    """
    지원자 답변을 평가축 기준으로 분석하여
    강점, 감점 리스크, 개선 방향을 제공합니다.
    """
    current_user = get_current_user(db, x_user_id, x_user_email)
    ctx = _build_db_context(db, current_user, req.company, req.job_role, req.analysis_id, req.resume_id)
    weights = req.feature_weights or _compute_weights_from_context(ctx) or compute_feature_weights(req.company, req.job_role)

    selected_axes = req.evaluation_axes or []
    if selected_axes:
        axes_desc = "\n".join(
            [f"- {ax.get('name')}: {ax.get('description', '')} (weight: {ax.get('weight', 0)})" for ax in selected_axes]
        )
        evaluation_instruction = f"""
[이 질문에 연결된 평가 기준]
{axes_desc}

위 평가 기준을 중심으로 답변을 평가하세요. risk_points의 axis에는 평가 기준명을 넣으세요.
"""
    else:
        evaluation_instruction = """
[공통 면접 답변 평가 기준]
이 질문은 특정 평가축에 연결되지 않은 직접 추가 질문입니다.
아래 공통 기준으로 답변을 평가하세요:
1. 질문 의도 파악: 질문에 직접 답했는가
2. 구체성: 실제 경험, 상황, 행동, 결과가 있는가
3. 논리성: 답변 흐름이 자연스럽고 설득력 있는가
4. 직무/회사 연관성: 지원 직무나 회사와 연결되는가
5. 자기 이해도: 본인의 강점, 약점, 가치관, 판단 기준이 드러나는가
6. 감점 리스크: 과장, 책임 회피, 모호한 표현, 부정적 태도가 있는가

risk_points의 axis에는 위 공통 기준명 중 가장 관련 있는 항목을 넣으세요.
"""

    prompt = f"""
당신은 엄격하지만 건설적인 면접관입니다. 아래 지원자의 답변을 평가하세요.

[지원 기업] {req.company}
[지원 직무] {req.job_role}
[면접 질문] {req.question}
[지원자 답변] {req.user_answer}

{evaluation_instruction}

[자소서 참조 (답변과 일관성 검증에 활용)]
{ctx['resume']}

아래 형식으로 답변을 평가하세요. 반드시 JSON 형식으로만 출력하세요.

{{
  "overall_score": 1~5 (정수, 5가 최고),
  "strengths": ["강점 1", "강점 2"],
  "risk_points": [
    {{
      "issue": "감점 요소 설명",
      "reason": "왜 감점인지 면접관 관점에서 설명",
      "axis": "관련 평가축 한국어명"
    }}
  ],
  "improvement": "구체적인 개선 방향 (1~2문장)",
  "follow_up_hint": "면접관이 이 답변을 듣고 가장 먼저 파고들 부분"
}}
"""

    try:
        # ② GPT-4o — 답변 평가 / 감점 리스크
        try:
            raw = _call_openai(prompt, max_tokens=800, temperature=0.5)
            print("✅ GPT-4o로 피드백 완료")
        except Exception as gpt_err:
            print(f"⚠️ GPT 실패, Claude로 폴백: {gpt_err}")
            raw = _call_claude(prompt, max_tokens=800, temperature=0.5)
        result = _extract_json(raw)
        return result
    except Exception as e:
        print("❌ 피드백 에러:", e)
        raise HTTPException(status_code=500, detail=f"피드백 생성 실패: {str(e)}")


# ─────────────────────────────────────────────────────────────
# 엔드포인트 5: 압박 꼬리질문 생성
# ─────────────────────────────────────────────────────────────
@router.post("/follow-up")
def get_follow_up_question(
    req: FollowUpRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
):
    """
    지원자 답변의 논리적 허점이나 자소서와의 불일치를
    파고드는 압박 꼬리질문을 생성합니다.
    """
    current_user = get_current_user(db, x_user_id, x_user_email)
    ctx = _build_db_context(db, current_user, req.company, req.job_role, req.analysis_id, req.resume_id)
    resume_ref = req.resume_excerpt or ctx["resume"][:500]

    prompt = f"""
당신은 날카로운 면접관입니다. 지원자의 답변을 듣고 자소서와의 일관성,
논리적 허점, 구체성 부족 등을 파고드는 압박 꼬리질문을 생성하세요.

[면접 질문] {req.question}
[지원자 답변] {req.user_answer}
[자소서 참조] {resume_ref}
[지원 직무] {req.job_role} @ {req.company}

꼬리질문 조건:
1. 답변의 가장 약한 논리 지점을 파고들 것
2. 자소서에서 강조한 내용과 답변 간 불일치가 있으면 검증할 것
3. "그렇다면..." "구체적으로..." "왜..." 형태로 시작하는 날카로운 질문
4. 2~3개 생성

반드시 JSON 배열만 출력하세요.

[
  {{
    "question": "꼬리질문 내용",
    "intent": "이 질문으로 확인하려는 것"
  }}
]
"""

    try:
        # ③ Gemini 1.5 Pro — 압박형 꼬리질문
        try:
            raw = _call_gemini(prompt, max_tokens=600, temperature=0.8)
            print("✅ Gemini로 꼬리질문 생성 완료")
        except Exception as gem_err:
            print(f"⚠️ Gemini 실패, GPT로 폴백: {gem_err}")
            raw = _call_openai(prompt, max_tokens=600, temperature=0.8)
        result = _extract_json(raw)
        return {"follow_up_questions": result}
    except Exception as e:
        print("❌ 꼬리질문 에러:", e)
        raise HTTPException(status_code=500, detail=f"꼬리질문 생성 실패: {str(e)}")


# ─────────────────────────────────────────────────────────────
# 엔드포인트 6: 세션 저장
# ─────────────────────────────────────────────────────────────
# 엔드포인트 6: 세션 저장
# ─────────────────────────────────────────────────────────────
@router.post("/sessions")
def save_interview_session(
    req: SaveSessionRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None)
):
    """사용자가 작성한 면접 답변을 데이터베이스에 저장(추가/업데이트)합니다."""
    current_user = get_current_user(db, x_user_id, x_user_email)
    session_id = req.session_id or f"session-{uuid.uuid4().hex[:8]}"
    
    # 세션 통계 계산
    total_q = len(req.answers)
    answered_q = sum(1 for a in req.answers if a.userAnswer and a.userAnswer.strip())
    
    scores = []
    for a in req.answers:
        if a.feedback:
            try:
                # feedback은 문자열일 수도 있고 딕셔너리일 수도 있으므로 분기 처리
                fb = json.loads(a.feedback) if isinstance(a.feedback, str) else a.feedback
                if isinstance(fb, dict) and "overall_score" in fb:
                    scores.append(fb["overall_score"])
            except Exception as e:
                print(f"피드백 점수 파싱 실패: {e}")
                pass
    
    avg_score = None
    if scores:
        avg_score = sum(scores) / len(scores) * 20 # Convert 5-point to 100-point scale

    stats_data = {
        "total_questions": total_q,
        "answered_questions": answered_q,
        "score": avg_score
    }
    
    axes_used_data = [ax.dict() for ax in req.axes_used] if req.axes_used else []

    # 1. 면접 세션(InterviewSession) 조회 또는 생성 (Upsert)
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if session:
        session.company_name = req.company
        session.job_role = req.job_role
        session.interview_type = req.interview_type or "전체"
        session.axis_type = req.axis_type or "static"
        session.axes_used = axes_used_data
        session.stats = stats_data
        print(f"✅ DB 세션 업데이트 진행 (ID: {session_id})")
    else:
        session = InterviewSession(
            id=session_id,
            user_id=current_user.id,
            company_name=req.company,
            job_role=req.job_role,
            interview_type=req.interview_type or "전체",
            axis_type=req.axis_type or "static",
            axes_used=axes_used_data,
            stats=stats_data
        )
        db.add(session)
        print(f"✅ DB 신규 세션 생성 진행 (ID: {session_id})")
        
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ 면접 세션 저장 에러: {e}")
        raise HTTPException(status_code=500, detail=f"면접 세션 저장 실패: {str(e)}")

    # 저장 요청에서 빠진 질문은 삭제된 질문으로 간주하여 답변/피드백/꼬리질문까지 정리합니다.
    incoming_question_ids = [a.id for a in req.answers]
    existing_questions_query = db.query(InterviewQuestion).filter(InterviewQuestion.session_id == session_id)
    if incoming_question_ids:
        questions_to_delete = existing_questions_query.filter(~InterviewQuestion.id.in_(incoming_question_ids)).all()
    else:
        questions_to_delete = existing_questions_query.all()

    for question_to_delete in questions_to_delete:
        db.query(FollowUpQuestion).filter(FollowUpQuestion.question_id == question_to_delete.id).delete()
        db.delete(question_to_delete)

    if questions_to_delete:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ 삭제된 면접 질문 정리 에러: {e}")
            raise HTTPException(status_code=500, detail=f"삭제된 면접 질문 정리 실패: {str(e)}")

    # 2. 면접 질문(InterviewQuestion) 개별 Upsert
    for a in req.answers:
        feedback_obj = None
        if a.feedback:
            try:
                feedback_obj = json.loads(a.feedback) if isinstance(a.feedback, str) else a.feedback
            except Exception:
                feedback_obj = a.feedback
                
        question = db.query(InterviewQuestion).filter(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.id == a.id
        ).first()
        
        if question:
            question.question_text = a.question
            question.category = a.category
            question.evaluation_axis_key = a.evaluation_axis
            question.axis_name = a.axis_name
            question.tips = a.tips
            question.user_answer = a.userAnswer
            question.feedback = feedback_obj
        else:
            question = InterviewQuestion(
                id=a.id,
                session_id=session_id,
                question_text=a.question,
                category=a.category,
                evaluation_axis_key=a.evaluation_axis,
                axis_name=a.axis_name,
                tips=a.tips,
                user_answer=a.userAnswer,
                feedback=feedback_obj
            )
            db.add(question)
            
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ 면접 질문 저장 에러: {e}")
            raise HTTPException(status_code=500, detail=f"면접 질문 저장 실패: {str(e)}")

        # 3. 꼬리질문(FollowUpQuestion) 동기화 (전체 삭제 후 다시 삽입하여 무결성 유지)
        db.query(FollowUpQuestion).filter(FollowUpQuestion.question_id == question.id).delete()
        
        if a.followUps:
            for fu in a.followUps:
                fu_question = fu.get("question")
                fu_intent = fu.get("intent")
                fu_user_answer = fu.get("userAnswer")
                fu_feedback = fu.get("feedback")
                
                new_fu = FollowUpQuestion(
                    question_id=question.id,
                    question_text=fu_question,
                    intent=fu_intent,
                    user_answer=fu_user_answer,
                    feedback_text=fu_feedback
                )
                db.add(new_fu)
                
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"❌ 꼬리질문 저장 에러: {e}")
                raise HTTPException(status_code=500, detail=f"꼬리질문 저장 실패: {str(e)}")

    print(f"🎉 [DB] 세션(ID: {session_id}) 및 질문 전체 저장 완료!")
    return {"message": "면접 세션이 성공적으로 저장되었습니다.", "session_id": session_id}


@router.delete("/sessions/{session_id}/questions/{question_id}")
def delete_interview_question(
    session_id: str,
    question_id: str,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None)
):
    """저장된 면접 세션에서 질문과 연결된 꼬리질문을 삭제합니다."""
    current_user = get_current_user(db, x_user_id, x_user_email)
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="면접 세션을 찾을 수 없습니다.")

    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id,
        InterviewQuestion.id == question_id,
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="삭제할 질문을 찾을 수 없습니다.")

    db.query(FollowUpQuestion).filter(FollowUpQuestion.question_id == question.id).delete()
    db.delete(question)

    remaining_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id,
        InterviewQuestion.id != question_id,
    ).all()
    scores = []
    for item in remaining_questions:
        if isinstance(item.feedback, dict) and "overall_score" in item.feedback:
            scores.append(item.feedback["overall_score"])

    session.stats = {
        "total_questions": len(remaining_questions),
        "answered_questions": sum(1 for item in remaining_questions if item.user_answer and item.user_answer.strip()),
        "score": (sum(scores) / len(scores) * 20) if scores else None,
    }

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ 면접 질문 삭제 에러: {e}")
        raise HTTPException(status_code=500, detail=f"면접 질문 삭제 실패: {str(e)}")

    return {"message": "질문이 삭제되었습니다."}


@router.delete("/sessions/{session_id}")
def delete_interview_session(
    session_id: str,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None)
):
    """저장된 면접 세션과 연결된 질문/꼬리질문을 모두 삭제합니다."""
    current_user = get_current_user(db, x_user_id, x_user_email)
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="면접 세션을 찾을 수 없습니다.")

    questions = db.query(InterviewQuestion).filter(InterviewQuestion.session_id == session_id).all()
    for question in questions:
        db.query(FollowUpQuestion).filter(FollowUpQuestion.question_id == question.id).delete()
        db.delete(question)
    db.delete(session)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ 면접 세션 삭제 에러: {e}")
        raise HTTPException(status_code=500, detail=f"면접 세션 삭제 실패: {str(e)}")

    return {"message": "면접 세션이 삭제되었습니다."}


@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None)
):
    """현재 로그인된 사용자의 모든 저장된 면접 세션을 반환합니다."""
    current_user = get_current_user(db, x_user_id, x_user_email)
    
    sessions = db.query(InterviewSession).filter(
        InterviewSession.user_id == current_user.id
    ).order_by(InterviewSession.created_at.desc()).all()
    
    result = []
    for s in sessions:
        answers = []
        for q in s.questions:
            follow_ups = []
            for fu in q.follow_ups:
                follow_ups.append({
                    "question": fu.question_text,
                    "intent": fu.intent,
                    "userAnswer": fu.user_answer or "",
                    "feedback": fu.feedback_text
                })
            
            answers.append({
                "id": q.id,
                "question": q.question_text,
                "category": q.category,
                "tips": q.tips or "",
                "evaluation_axis": q.evaluation_axis_key,
                "axis_name": q.axis_name,
                "userAnswer": q.user_answer or "",
                "feedback": q.feedback,
                "followUps": follow_ups
            })
            
        result.append({
            "id": s.id,
            "company": s.company_name,
            "job_role": s.job_role,
            "interview_type": s.interview_type,
            "axis_type": s.axis_type,
            "axes_used": s.axes_used,
            "answers": answers,
            "created_at": s.created_at.isoformat() if s.created_at else datetime.utcnow().isoformat(),
            "stats": s.stats
        })
        
    return result


# ─────────────────────────────────────────────────────────────
# (하위 호환) 기존 mock-context 엔드포인트 유지
# ─────────────────────────────────────────────────────────────
@router.get("/mock-context")
def get_mock_context():
    """기존 호환용 — /interview/positions 사용 권장"""
    return AVAILABLE_POSITIONS
