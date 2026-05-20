## 면접 준비 API (RAG + 평가축 기반 PoC) ##
import os
import json
import re
import uuid
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
from app.models.db_models import User, InterviewSession, InterviewQuestion, FollowUpQuestion
from app.services.interview_rag_data import (
    FEATURE_TAXONOMY,
    AVAILABLE_POSITIONS,
    compute_feature_weights,
    retrieve_context,
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


class FeedbackRequest(BaseModel):
    company: str
    job_role: str
    question: str
    user_answer: str
    feature_weights: Optional[Dict[str, float]] = None


class FollowUpRequest(BaseModel):
    company: str
    job_role: str
    question: str
    user_answer: str
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


# ─────────────────────────────────────────────────────────────
# 엔드포인트 2: 평가축 추론 (feature weights)
# ─────────────────────────────────────────────────────────────
@router.post("/evaluate-axes")
def evaluate_axes(req: QuestionRequest):
    """
    JD + 기업분석 레포트 + 자소서 문서를 RAG로 retrieval하여
    평가축별 weight를 계산하고 반환합니다.
    (평가축은 고정 taxonomy — weight만 동적 계산)
    """
    weights = compute_feature_weights(req.company, req.job_role)
    ctx = retrieve_context(req.company, req.job_role)

    # weight 기반 평가축 목록 (name + description + score 포함)
    axes = []
    for key, score in weights.items():
        if key in FEATURE_TAXONOMY:
            axes.append({
                "key": key,
                "name": FEATURE_TAXONOMY[key]["name"],
                "description": FEATURE_TAXONOMY[key]["description"],
                "weight": score,
            })

    return {
        "company": req.company,
        "job_role": req.job_role,
        "evaluation_axes": axes,
        "sources": ctx["sources"],
        "note": "평가축은 JD·기업분석·자소서 데이터 기반 추론 결과입니다. 실제 기업 내부 평가 기준과 다를 수 있습니다.",
    }


# ─────────────────────────────────────────────────────────────
# 엔드포인트 3: 면접 질문 생성 (RAG + 평가축 기반)
# ─────────────────────────────────────────────────────────────
@router.post("/questions")
def get_interview_questions(req: QuestionRequest):
    """
    RAG로 JD + 기업분석 + 자소서를 retrieval하고,
    평가축 weight 또는 동적 평가축 기반으로 맞춤형 면접 질문 5개를 생성합니다.
    """
    # 1) RAG retrieval
    ctx = retrieve_context(req.company, req.job_role)
    weights = compute_feature_weights(req.company, req.job_role)

    # 2) 평가축 설정 (정적 vs 동적)
    dynamic_axis_map = {}
    axes_used_info = []
    
    if req.axis_type == "dynamic":
        axes_prompt = f"""
당신은 기업 면접관입니다. 아래 데이터를 바탕으로 해당 직무에 필요한 핵심 평가축(역량) 6가지를 동적으로 추출하세요.

[지원 기업] {req.company}
[지원 직무] {req.job_role}
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
            dynamic_axes = _extract_json(raw_axes)
            axes_desc = "\n".join([f"- {ax['name']}: {ax['description']}" for ax in dynamic_axes])
            weights = {ax['key']: ax['weight'] for ax in dynamic_axes}
            dynamic_axis_map = {ax['key']: ax['name'] for ax in dynamic_axes}
            axes_used_info = dynamic_axes
        except Exception as e:
            print("동적 평가축 추출 실패, 기본값 사용:", e)
            req.axis_type = "static"

    if req.axis_type == "static":
        top_axes = list(weights.items())[:6]
        axes_desc = "\n".join(
            [f"- {FEATURE_TAXONOMY[k]['name']} (weight: {v}): {FEATURE_TAXONOMY[k]['description']}"
             for k, v in top_axes if k in FEATURE_TAXONOMY]
        )
        for k, v in top_axes:
            if k in FEATURE_TAXONOMY:
                axes_used_info.append({
                    "key": k,
                    "name": FEATURE_TAXONOMY[k]['name'],
                    "description": FEATURE_TAXONOMY[k]['description'],
                    "weight": v
                })
                
    # 3) 면접 유형에 따른 조건 추가
    type_condition = ""
    if req.interview_type == "인성":
        type_condition = "3. 반드시 5개 질문 모두 지원자의 경험, 가치관, 상황 대처 능력을 묻는 '인성/경험' (behavioral/situational) 카테고리로만 생성하세요."
    elif req.interview_type == "실무":
        type_condition = "3. 반드시 5개 질문 모두 지원자의 직무 지식, 기술적 문제 해결력, 포트폴리오를 검증하는 '실무/기술' (technical) 카테고리로만 생성하세요."
    else:
        type_condition = "3. 카테고리: behavioral(경험기반), technical(기술/직무), situational(상황대처) 골고루 섞어서 생성하세요."

    prompt = f"""
당신은 기업 면접관입니다. 아래 데이터를 참조하여 지원자에게 할 면접 질문을 생성하세요.

[지원 기업] {req.company}
[지원 직무] {req.job_role}

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
1. 자소서에서 언급된 구체적 경험을 직접 검증하는 질문 포함
2. 제시된 핵심 평가축 중심으로 질문 강화
{type_condition}
4. 이 직무의 약점으로 분석된 지식 검증 질문 1개 이상 포함
5. evaluation_axis 필드에 해당 질문이 검증하는 평가축 key를 명시

반드시 아래 JSON 배열 형식으로만 출력하세요. 설명, 인사말, 코드블록(```) 절대 출력 금지.

[
  {{
    "id": "question-1",
    "question": "질문 내용 (자소서 경험 기반 구체적으로)",
    "category": "behavioral | technical | situational",
    "evaluation_axis": "평가축 key",
    "tips": "이 질문에서 면접관이 보고자 하는 포인트"
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
            # 1) 동적 평가축 매칭 시도 (key 또는 name 매칭)
            if req.axis_type == "dynamic":
                for ax in dynamic_axes:
                    if ax.get("key") == axis_key or ax.get("name") == axis_key:
                        item["axis_name"] = ax.get("name")
                        item["axis_weight"] = ax.get("weight", 0.0)
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
def get_answer_feedback(req: FeedbackRequest):
    """
    지원자 답변을 평가축 기준으로 분석하여
    강점, 감점 리스크, 개선 방향을 제공합니다.
    """
    ctx = retrieve_context(req.company, req.job_role)
    weights = req.feature_weights or compute_feature_weights(req.company, req.job_role)

    top_axes = list(weights.items())[:4]
    axes_desc = "\n".join(
        [f"- {FEATURE_TAXONOMY[k]['name']} (weight: {v})"
         for k, v in top_axes if k in FEATURE_TAXONOMY]
    )

    prompt = f"""
당신은 엄격하지만 건설적인 면접관입니다. 아래 지원자의 답변을 평가하세요.

[지원 기업] {req.company}
[지원 직무] {req.job_role}
[면접 질문] {req.question}
[지원자 답변] {req.user_answer}

[이 기업/직무의 핵심 평가축 (중요도 순)]
{axes_desc}

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
def get_follow_up_question(req: FollowUpRequest):
    """
    지원자 답변의 논리적 허점이나 자소서와의 불일치를
    파고드는 압박 꼬리질문을 생성합니다.
    """
    ctx = retrieve_context(req.company, req.job_role)
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
    
    # Calculate some stats for the session
    total_q = len(req.answers)
    answered_q = sum(1 for a in req.answers if a.userAnswer and a.userAnswer.strip())
    
    # Simple score calculation if feedback exists
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
