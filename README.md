# 🚀 Job Agent Backend

취업 지원 AI 서비스 백엔드 (FastAPI 기반)

---

## 📌 프로젝트 개요

본 프로젝트는 취준생이 기업 분석부터 자기소개서, 면접 준비까지 효율적으로 수행할 수 있도록 지원하는 AI 서비스입니다.

---

## 🧩 주요 기능

* 기업 분석 (Company Analysis)
* JD 분석 (Job Description Analysis)
* 자기소개서 생성 (Resume Generation)
* 면접 준비 (Interview Preparation)

---

## 🧱 프로젝트 구조

```text
backend/
 ├── app/
 │    ├── main.py
 │    ├── api/
 │    │    ├── company.py
 │    │    ├── jd.py
 │    │    ├── resume.py
 │    │    └── interview.py
 │    │
 │    ├── services/
 │    │    ├── company_service.py
 │    │    ├── jd_service.py
 │    │    ├── resume_service.py
 │    │    └── interview_service.py
 │    │
 │    ├── models/
 │    │    └── company_model.py
 │    │
 │    ├── crawler/
 │    │    └── news_crawler.py
 │    │
 │    └── core/
 │         └── config.py
 │
 ├── requirements.txt
 ├── .env.example
 └── README.md
```

---

## ⚙️ 실행 방법 (중요)

### 1. 저장소 클론

```bash
git clone https://github.com/your-id/job-agent.git
cd job-agent/backend
```

---

### 2. 가상환경 생성 (Conda)

```bash
conda create -n job-agent python=3.10
conda activate job-agent
```

---

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

---

### 4. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 아래 값 입력:

```text
OPENAI_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
```

---

### 5. 서버 실행

```bash
uvicorn app.main:app --reload
```

---

### 6. API 확인

👉 Swagger UI
http://localhost:8000/docs

---

## 📡 API 목록

| 기능    | Endpoint          |
| ----- | ----------------- |
| 기업 분석 | `/company/report` |
| JD 분석 | `/jd/...`         |
| 자기소개서 | `/resume/...`     |
| 면접 준비 | `/interview/...`  |

---

## 🧪 테스트 방법

Swagger에서 직접 테스트:

1. `/docs` 접속
2. `/company/report` 선택
3. "Try it out" 클릭
4. company 입력 후 실행

---

## 📌 개발 규칙

* API는 `api/` 폴더에서 관리
* 로직은 `services/`에서 구현
* 데이터 구조는 `models/`에서 정의
* 크롤링은 `crawler/`에서 처리

---

## ⚠️ 주의사항

* `.env` 파일은 Git에 업로드 금지
* 가상환경은 각자 생성
* 실행 안 되면 requirements 재설치

---

## 📌 현재 상태

* FastAPI 백엔드 세팅 완료
* 기업 분석 API 기본 구현 완료
* Swagger 테스트 완료

---

## 📌 한 줄 정리

👉 “clone → env 설정 → 실행 → 바로 테스트 가능”
