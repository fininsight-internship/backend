import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session
from app.models.db_models import CompanyReport

from app.crawler.news_crawler import crawl_news
from app.crawler.company_crawler import crawl_company_culture
from app.crawler.career_crawler import get_company_career_url

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 🔹 뉴스 요약
def summarize_news(contents: list):
    summaries = []

    for c in contents:
        prompt = f"""
다음 뉴스 한 개를 한 줄로 요약해라.
핵심 사건만 포함.

뉴스:
{c}
"""
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100
        )
        summaries.append(res.choices[0].message.content.strip())

    combined = "\n".join(summaries)

    final_prompt = f"""
다음 뉴스 요약들을 기반으로 기업의 주요 흐름을 정리해라.

조건:
- 반드시 해당 기업 기준으로 작성
- 다른 기업 언급 금지
- 특정 기능이 아닌 기업 전체 관점에서 작성
- 핵심 사업 중심으로 재해석

요약:
{combined}
"""

    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": final_prompt}],
        temperature=0.2,
        max_tokens=200
    )

    return final.choices[0].message.content.strip()


# 🔹 JSON 파싱 안정화
def safe_json_parse(content: str):
    try:
        return json.loads(content)
    except:
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            try:
                return json.loads(match.group())
            except:
                return {}
    return {}


# 🔹 strategy 타입 보정
def normalize_strategy(parsed: dict):
    fixed = []
    for s in parsed.get("strategy", []):
        if isinstance(s, dict):
            area = s.get("area", "")
            direction = s.get("direction", "")
            fixed.append(f"{area}: {direction}".strip(": "))
        else:
            fixed.append(str(s))
    parsed["strategy"] = fixed
    return parsed


# 🔹 business 카테고리 매핑 (핵심)
def normalize_business(llm_result: list):
    result = []

    for item in llm_result:
        text = str(item)

        if "검색" in text:
            result.append("검색")
        if "광고" in text:
            result.append("광고")
        if "커머스" in text or "쇼핑" in text or "패션" in text:
            result.append("커머스")
        if "AI" in text or "인공지능" in text:
            result.append("AI")
        if "콘텐츠" in text or "영상" in text:
            result.append("콘텐츠")
        if "클라우드" in text:
            result.append("클라우드")
        if "금융" in text:
            result.append("금융")

    result = list(set(result))

    # fallback (마지막에만)
    if len(result) == 0:
        result = ["플랫폼"]

    return result


# 🔹 기본 필드 보정
def ensure_fields(parsed: dict):
    parsed.setdefault("summary", "")
    parsed.setdefault("issues", [])
    parsed.setdefault("business", {"main": [], "description": ""})
    parsed.setdefault("strategy", [])
    parsed.setdefault("job_insight", None)
    return parsed


# 🔹 기업 분석
def generate_company_report(db: Session, company: str, job: str = None):
    # 0. 캐시 확인
    cached = db.query(CompanyReport).filter(CompanyReport.company_name == company).first()
    if cached and cached.company_analysis:
        analysis_data = cached.company_analysis
        if isinstance(analysis_data, str):
            try:
                analysis_data = json.loads(analysis_data)
            except:
                pass
        return {
            "status": "success",
            "company": company,
            "job": job,
            "data": analysis_data
        }

    # 1. 뉴스 수집
    news_contents = crawl_news(company)
    if not news_contents:
        news_contents = ["뉴스 없음"]

    # 2. 요약
    summarized_news = summarize_news(news_contents)

    # 3. LLM 분석
    prompt = f"""
기업: {company}

요약:
{summarized_news}

조건:
- 반드시 JSON만 출력
- 반드시 {company} 기준으로 작성
- 다른 기업 언급 금지
- issues 2~3개 필수 생성
- strategy 2~3개 필수 생성
- 특정 기능이 아니라 기업 전체 관점에서 작성

출력:

{{
  "summary": "",
  "issues": [],
  "business": {{
    "main": [],
    "description": ""
  }},
  "job_insight": null,
  "strategy": []
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600
    )

    raw = response.choices[0].message.content.strip()

    print("===== RAW LLM OUTPUT =====")
    print(raw)

    # 4. JSON 파싱
    parsed = safe_json_parse(raw)

    # 5. 필드 보정
    parsed = ensure_fields(parsed)

    # 6. business 매핑
    parsed["business"]["main"] = normalize_business(
        parsed["business"].get("main", [])
    )

    # 7. strategy 보정
    parsed = normalize_strategy(parsed)

    # 8. fallback 보정
    if len(parsed["issues"]) < 2:
        parsed["issues"] = [
            f"{company} 핵심 사업 경쟁 심화 가능성",
            f"{company} 서비스 고도화 필요성"
        ]

    if len(parsed["strategy"]) == 0:
        parsed["strategy"] = [
            f"{company} AI 기반 서비스 고도화",
            f"{company} 핵심 사업 경쟁력 강화"
        ]

    if len(parsed["business"]["main"]) == 0:
        parsed["business"]["main"] = ["플랫폼"]

    # 9. 추가 데이터
    parsed["culture"] = crawl_company_culture(company)
    parsed["career_url"] = get_company_career_url(company)

    # 10. DB 캐시에 저장
    try:
        new_report = CompanyReport(
            company_name=company,
            company_info=parsed.get("summary", ""),
            company_analysis=parsed
        )
        db.add(new_report)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[company_service] 캐시 저장 실패: {e}")
    
    return {
        "status": "success",
        "company": company,
        "job": job,
        "data": parsed
    }