## 기업 분석 ##

import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from app.crawler.news_crawler import crawl_news

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_company_report(company: str, job: str = None):
    # 1. 뉴스 수집
    news = crawl_news(company)

    if not news:
        news = ["관련 뉴스 없음"]

    context = "\n".join(news)

    # 2. 프롬프트
    prompt = f"""
기업: {company}

뉴스:
{context}

뉴스가 부족해도 반드시 내용을 채워라.
빈 값으로 두지 말고 일반적인 기업 분석을 작성해라.

절대 JSON 외 텍스트 출력 금지
설명 금지
코드블록 금지

반드시 아래 JSON 형식으로만 출력해라.

{{
  "summary": "",
  "issues": [],
  "business": {{
    "main": [],
    "description": ""
  }},
  "culture": {{
    "keywords": [],
    "description": ""
  }},
  "job_insight": null,
  "strategy": []
}}
"""

    # 3. LLM 호출
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600
    )

    content = response.choices[0].message.content

    # 🔍 디버깅 (중요)
    print("===== LLM RAW OUTPUT =====")
    print(content)
    print("==========================")

    # 4. 코드블록 제거
    content = content.replace("```json", "").replace("```", "").strip()

    # 5. JSON 부분만 추출 (핵심)
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        content = match.group()

    # 6. JSON 파싱
    try:
        parsed = json.loads(content)
    except Exception as e:
        print("❌ JSON 파싱 에러:", e)
        print("❌ 문제 content:", content)

        parsed = {
            "summary": "파싱 실패",
            "issues": [],
            "business": {"main": [], "description": ""},
            "culture": {"keywords": [], "description": ""},
            "job_insight": None,
            "strategy": []
        }

    # 7. 최종 반환
    return {
        "status": "success",
        "company": company,
        "job": job,
        "data": parsed
    }