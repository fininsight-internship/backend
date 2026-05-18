from app.data.company_career_url import CAREER_URL_MAP
import requests
from bs4 import BeautifulSoup


# 🔹 1. 기본: 매핑 기반 (가장 안정)
def get_career_url(company: str):
    return CAREER_URL_MAP.get(company)


# 🔹 2. fallback: 회사 홈페이지에서 채용 링크 찾기
def find_career_from_homepage(company: str):
    homepage_map = {
        "네이버": "https://www.navercorp.com",
        "카카오": "https://www.kakaocorp.com"
    }

    base_url = homepage_map.get(company)

    if not base_url:
        return None

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(base_url, headers=headers, timeout=5)

        soup = BeautifulSoup(res.text, "html.parser")

        for a in soup.find_all("a", href=True):
            text = a.get_text().lower()
            href = a["href"]

            if "채용" in text or "career" in text:
                # 절대경로 보정
                if href.startswith("http"):
                    return href
                else:
                    return base_url + href

        return None

    except Exception as e:
        print("❌ career fallback 실패:", e)
        return None


# 🔹 3. 통합 함수 (실제로 사용할 것)
def get_company_career_url(company: str):
    # 1. 매핑 우선
    url = get_career_url(company)

    if url:
        return url

    # 2. fallback
    return find_career_from_homepage(company)