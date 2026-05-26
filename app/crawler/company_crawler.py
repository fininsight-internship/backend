from app.data.company_career_url import CAREER_URL_MAP



import requests
from bs4 import BeautifulSoup


def clean_text(text: str):
    noise_keywords = [
        "Skip to navigation",
        "Skip to content",
        "Contact",
        "logo",
        "메뉴",
        "전체 서비스"
    ]

    for n in noise_keywords:
        text = text.replace(n, "")

    return " ".join(text.split())  # 공백 정리

def crawl_company_culture(company: str):
    url_map = {
        "네이버": "https://www.navercorp.com",
        "카카오": "https://www.kakaocorp.com"
    }

    url = url_map.get(company)

    if not url:
        return {
            "keywords": [],
            "description": ""
        }

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)

        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = clean_text(text)

        return {
            "keywords": ["혁신", "협업", "기술 중심"],
            "description": text[:300]
        }

    except:
        return {
            "keywords": [],
            "description": ""
        }
        
        
        
def get_career_url(company: str):
    return CAREER_URL_MAP.get(company)