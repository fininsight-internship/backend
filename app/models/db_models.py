import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.core.db import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True) # 희망 직무 (예: 프론트엔드 개발자)
    
    # 세부 경험 추가 컬럼
    eng_name = Column(String(255), nullable=True)
    birth_date = Column(String(50), nullable=True)
    education_list = Column(JSON, nullable=True)
    certification_list = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 1:N 관계 정의
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    experiences = relationship("Experience", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    company_analyses = relationship("CompanyJDAnalysis", back_populates="user", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    raw_content = Column(Text, nullable=True)
    parsed_content = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 정의
    user = relationship("User", back_populates="resumes")
    experiences = relationship("Experience", back_populates="resume", cascade="all, delete-orphan")
    resume_questions = relationship("ResumeQuestion", back_populates="resume", cascade="all, delete-orphan")
    resume_evaluations = relationship("ResumeEvaluation", back_populates="resume", cascade="all, delete-orphan")


class Experience(Base):
    __tablename__ = "experiences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    
    # 활동 구분 및 공통/특화 필드
    category = Column(String(100), nullable=True) # '경력인턴', '교육부트캠프', '프로젝트', '동아리', '봉사활동', '기타경험'
    title = Column(String(255), nullable=True) # 활동명, 회사명, 교육/부트캠프명 등
    detail = Column(Text, nullable=True) # 상세 경험 내용
    star_data = Column(JSON, nullable=True) # STAR 구조화 데이터 {"S": ..., "T": ..., "A": ..., "R": ...}

    # 특화 상세 필드
    department = Column(String(255), nullable=True) # 경력 부서
    topic = Column(String(255), nullable=True) # 교육/부트캠프 주제
    
    # 기존 호환성 및 공통 기간 필드
    company_name = Column(String(255), nullable=True)
    role = Column(String(255), nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    user = relationship("User", back_populates="experiences")
    resume = relationship("Resume", back_populates="experiences")


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_role = Column(String(255), nullable=False)
    status = Column(String(100), nullable=False, default="지원대기") # 서류합격, 면접대기 등
    progress_status = Column(String(255), nullable=True, default="자소서작성:진행중") # 진행 상태
    applied_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    user = relationship("User", back_populates="applications")


class CompanyReport(Base):
    __tablename__ = "company_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), unique=True, nullable=False, index=True)
    company_info = Column(Text, nullable=True)
    company_analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyJDAnalysis(Base):
    __tablename__ = "company_jd_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_role = Column(String(255), nullable=False)
    jd_content = Column(Text, nullable=True)
    analysis_report = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계 정의
    user = relationship("User", back_populates="company_analyses")


class InterviewEvaluationAxisCache(Base):
    __tablename__ = "interview_evaluation_axis_cache"

    id = Column(Integer, primary_key=True, index=True)
    source_signature = Column(String(128), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    job_role = Column(String(255), nullable=False)
    axis_type = Column(String(50), nullable=False)
    axes = Column(JSON, nullable=False)
    feature_weights = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    # frontend/mock-data와의 호환성을 위해 ID를 문자열 UUID로 유지합니다.
    id = Column(String(100), primary_key=True, default=lambda: f"session-{uuid.uuid4().hex[:8]}")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_role = Column(String(255), nullable=False)
    interview_type = Column(String(100), nullable=False) # 전체, 인성, 실무
    axis_type = Column(String(50), nullable=False) # static, dynamic
    axes_used = Column(JSON, nullable=True)
    stats = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    user = relationship("User", back_populates="interview_sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    
    # frontend/mock-data와의 호환성을 위해 ID를 문자열 UUID로 유지합니다.
    id = Column(String(100), primary_key=True, default=lambda: f"q-{uuid.uuid4().hex[:8]}")
    session_id = Column(String(100), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    category = Column(String(100), nullable=False) # behavioral, technical, resume
    evaluation_axis_key = Column(String(255), nullable=True)
    axis_name = Column(String(255), nullable=True)
    axis_weight = Column(Float, nullable=True)
    tips = Column(Text, nullable=True)
    user_answer = Column(Text, nullable=True)
    feedback = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    session = relationship("InterviewSession", back_populates="questions")
    follow_ups = relationship("FollowUpQuestion", back_populates="question", cascade="all, delete-orphan")


class FollowUpQuestion(Base):
    __tablename__ = "follow_up_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(String(100), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    intent = Column(Text, nullable=True)
    user_answer = Column(Text, nullable=True)
    feedback_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    question = relationship("InterviewQuestion", back_populates="follow_ups")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_role = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(50), nullable=False) # user 또는 assistant
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계 정의
    session = relationship("ChatSession", back_populates="messages")


class ResumeQuestion(Base):
    __tablename__ = "resume_questions"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=True)    # 문항 질문 텍스트
    question_content = Column(Text, nullable=True) # 완성된 자소서 답변
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resume = relationship("Resume", back_populates="resume_questions")
    evaluations = relationship("ResumeQuestionEvaluation", back_populates="question", cascade="all, delete-orphan")


class ResumeEvaluation(Base):
    __tablename__ = "resume_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, nullable=True)
    strengths = Column(JSON, nullable=True)
    improvements = Column(JSON, nullable=True)
    overall_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="resume_evaluations")


class ResumeQuestionEvaluation(Base):
    __tablename__ = "resume_question_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("resume_questions.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    question_score = Column(Float, nullable=True)
    strengths = Column(JSON, nullable=True)
    improvements = Column(JSON, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("ResumeQuestion", back_populates="evaluations")
