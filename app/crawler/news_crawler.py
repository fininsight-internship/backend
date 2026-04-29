import requests
import os
import html
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


def crawl_news(company: str):
    url = "https://openapi.naver.com/v1/search/news.json"

    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }

    params = {
        "query": company,
        "display": 10,
        "sort": "date"
    }

    res = requests.get(url, headers=headers, params=params)
    data = res.json()

    items = data.get("items", [])

    news_list = []
    for item in items:
        title = html.unescape(item["title"])
        title = title.replace("<b>", "").replace("</b>", "")

        if company.lower() in title.lower():
            news_list.append(title)

    return news_list[:5]  # 