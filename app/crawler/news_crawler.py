import requests
import os
import html
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


# 🔹 본문 크롤링
def extract_article_content(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)

        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")

        selectors = [
            "#dic_area",
            "#newsct_article",
            ".news_end",
            ".article_body",
            "#articeBody"
        ]

        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                text = content.get_text(separator=" ", strip=True)
                if len(text) > 200:
                    return text[:2000]

        return None

    except:
        return None


# 🔹 relevance 점수 계산
def score_relevance(title: str, content: str, company: str):
    text = (title + " " + (content or "")).lower()
    company = company.lower()

    score = 0

    # 제목 포함 → 강한 신호
    if company in title.lower():
        score += 3

    # 본문 포함 횟수
    score += text.count(company)

    return score


# 🔹 뉴스 크롤링 (동적 수집 + ranking)
def crawl_news(company: str):
    url = "https://openapi.naver.com/v1/search/news.json"

    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }

    collected = []
    start = 1
    MAX_FETCH = 30   # 최대 30개
    TARGET = 3       # 목표 기사 수

    while len(collected) < TARGET and start <= MAX_FETCH:

        params = {
            "query": company,
            "display": 10,
            "start": start,
            "sort": "date"
        }

        res = requests.get(url, headers=headers, params=params)
        data = res.json()

        items = data.get("items", [])

        for item in items:
            title = html.unescape(item["title"])
            title = title.replace("<b>", "").replace("</b>", "")

            link = item.get("originallink") or item.get("link")

            content = extract_article_content(link)

            score = score_relevance(title, content, company)

            if score > 0:
                combined = f"{title}\n{content}" if content else title
                collected.append((score, combined))

        start += 10

    # 🔥 fallback
    if not collected:
        return ["관련 뉴스 부족"]

    # 🔥 점수 기반 정렬
    collected.sort(key=lambda x: x[0], reverse=True)

    # 🔥 다양성 필터 추가
    def is_similar(a: str, b: str):
        return a[:80] == b[:80]

    unique_results = []

    for score, content in collected:
        if all(not is_similar(content, u) for u in unique_results):
            unique_results.append(content)

        if len(unique_results) == TARGET:
            break

    # fallback
    if not unique_results:
        return ["관련 뉴스 부족"]

    return unique_results
