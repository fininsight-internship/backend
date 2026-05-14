# 🚀 Job Agent Backend

취업 지원 AI 서비스 백엔드 (FastAPI 기반)

---

# 📌 프로젝트 개요

본 프로젝트는 취준생이 기업 분석부터 채용공고(JD) 분석, Resume 분석, Gap Analysis, 면접 준비까지 효율적으로 수행할 수 있도록 지원하는 AI 기반 취업 지원 서비스입니다.

JobKorea 채용공고를 자동으로 크롤링하고,  
LLM(OpenAI)을 활용하여 JD를 구조화 및 분석한 뒤,  
사용자의 Resume와 비교하여 적합도 및 보완 방향을 제공하는 기능을 구현했습니다.

---

# 🧩 구현 기능

## 1. JobKorea JD 크롤링 기능

### 구현 파일

```text
app/crawler/jd_crawler.py
```

### 주요 기능

- JobKorea 채용공고 URL 입력
- iframe 기반 실제 JD HTML 접근
- 공고 내용 자동 추출
- JSON 구조화 저장

### 추출 항목

- 담당업무(tasks)
- 기술스택(skills)
- 자격요건(requirements)
- 우대사항(preferred)
- 전형절차(process)
- 유의사항(notes)

### 추가 metadata 추출

- 채용 인원(headcount)
- 영문 이력서 필수 여부

### 저장 위치

```text
data/jd/{job_id}.json
```

---

## 2. JD 분석 기능

### 구현 파일

```text
app/services/jd_service.py
```

### 주요 기능

- JD 핵심역량 분석
- 기술스택 분석
- 요구 학력 분석
- 요구 경력 분석
- 이상적인 지원자 형태 생성

### 사용 모델

- OpenAI GPT-4o-mini

---

## 3. Resume Parsing 및 저장 기능

### 구현 파일

```text
app/services/resume_service.py
```

### 주요 기능

- Resume 텍스트 → JSON 구조화
- Resume 저장
- 저장된 Resume 조회

### 저장 위치

```text
data/resume/{user_id}_resume.json
```

---

## 4. JD 기반 Gap Analysis 기능

### API

```text
POST /jd/gap-analysis/v2
```

### 주요 기능

저장된:

- JD JSON
- Resume JSON

을 기반으로:

- 적합도 분석
- 강점 분석
- 부족한 점 분석
- 보완 방법 제안

기능 구현.

---

## 5. Resume 최적화 생성 기능

### API

```text
POST /jd/resume-write/v2
```

### 주요 기능

JD 요구사항 기반으로:

- Resume 개선 방향 제안
- 기술스택 재정리
- 프로젝트 표현 최적화

기능 구현.

---

# 📡 구현 API 목록

## JD 관련

```text
POST /jd/crawl-and-analyze
POST /jd/analyze
POST /jd/ideal-resume
POST /jd/gap-analysis/v2
POST /jd/resume-write/v2
```

---

## Resume 관련

```text
POST /resume/save
POST /resume/parse
GET /resume/{user_id}
```

---

# 🧱 프로젝트 구조

```text
backend/
├── app/
│
│   ├── api/
│   │    ├── jd.py
│   │    └── resume.py
│   │
│   ├── services/
│   │    ├── jd_service.py
│   │    └── resume_service.py
│   │
│   ├── crawler/
│   │    └── jd_crawler.py
│   │
│   └── main.py
│
├── data/
│   ├── jd/
│   └── resume/
│
└── README.md
```

---

# ⚙️ 실행 방법

## 1. backend 이동

```bash
cd backend
```

---

## 2. 가상환경 활성화

```bash
conda activate job-agent
```

---

## 3. 서버 실행

```bash
python -m uvicorn app.main:app --reload
```

---

## 4. Swagger UI 접속

```text
http://127.0.0.1:8000/docs
```

---

# 🧪 테스트 방법

## JD 크롤링 테스트

### API

```text
POST /jd/crawl-and-analyze
```

### Request Body

```json
{
  "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/49017016"
}
```

---

## Gap Analysis 테스트

### API

```text
POST /jd/gap-analysis/v2
```

### Request Body

```json
{
  "job_id": "49017016",
  "user_id": "test_user_01"
}
```

---

# 🧠 사용 기술

## Backend

- FastAPI
- Python
- Pydantic

---

## Crawling

- httpx
- BeautifulSoup4

---

## AI

- OpenAI API
- GPT-4o-mini

---

# 📌 구현 과정에서 해결한 문제

- JobKorea iframe 구조 분석
- 공고별 HTML 구조 차이 대응
- JSON 구조 표준화
- OpenAI 응답 JSON 파싱 처리
- FastAPI API 구조 분리
- crawler / api / services 구조 분리
- 저장 기반(v2) API 흐름 구성

---

# 📌 현재 상태

- JD 크롤링 정상 동작 확인
- Resume 저장 정상 동작 확인
- Gap Analysis 정상 동작 확인
- Resume 최적화 생성 정상 동작 확인
- Swagger API 테스트 완료

---

# 📌 Git Branch

현재 작업 브랜치:

```text
feature/jd
```

---

# 📌 향후 개선 가능 사항

- 비동기 크롤링 적용
- Embedding 기반 유사도 분석
- ATS Scoring 기능 추가
- Redis Cache 적용
- Batch Crawling
- Docker 배포
- CI/CD 적용

---

# 📌 한 줄 정리

👉 “JobKorea JD 크롤링부터 Resume Gap Analysis까지 자동화한 AI 취업 지원 백엔드”
