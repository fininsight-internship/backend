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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 1:N 관계 정의
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
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
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    resume = relationship("Resume", back_populates="experiences")


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_role = Column(String(255), nullable=False)
    status = Column(String(100), nullable=False, default="지원대기") # 서류합격, 면접대기 등
    applied_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    user = relationship("User", back_populates="applications")


class CompanyJDAnalysis(Base):
    __tablename__ = "company_jd_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_role = Column(String(255), nullable=False)
    jd_content = Column(Text, nullable=True)
    company_report = Column(Text, nullable=True)
    analysis_report = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    user = relationship("User", back_populates="company_analyses")


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
