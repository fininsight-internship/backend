import os
import io
import zipfile
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any
from datetime import datetime, timedelta

class ScraperService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.dart_corp_codes = {}

    def scrape_jd(self, url: str) -> Dict[str, Any]:
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)

            return {
                "success": True,
                "url": url,
                "jd_text": clean_text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _get_google_news(self, company_name: str) -> str:
        try:
            url = f"https://news.google.com/rss/search?q={company_name}&hl=ko&gl=KR&ceid=KR:ko"
            resp = requests.get(url, timeout=5)
            soup = BeautifulSoup(resp.text, 'xml')
            items = soup.find_all('item')[:5]
            news = []
            for item in items:
                title = item.title.text if item.title else ""
                news.append(f"- {title}")
            return "\n".join(news)
        except:
            return ""

    def _get_naver_news(self, company_name: str) -> str:
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        if not client_id or not client_secret:
            return "네이버 API 키가 없습니다."
        try:
            url = "https://openapi.naver.com/v1/search/news.json"
            headers = {
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret
            }
            params = {"query": company_name, "display": 5, "sort": "sim"}
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                news = []
                for item in items:
                    title = BeautifulSoup(item['title'], 'html.parser').get_text()
                    news.append(f"- {title}")
                return "\n".join(news)
            return f"API 에러: {resp.status_code}"
        except:
            return "네이버 뉴스 수집 실패"

    def _get_dart_info(self, company_name: str) -> str:
        dart_key = os.getenv("DART_API_KEY")
        if not dart_key:
            return "DART API 키가 없습니다."
        
        try:
            # 1. 고유번호 매핑 캐시 확인 및 로드
            if not self.dart_corp_codes:
                resp = requests.get(f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={dart_key}")
                if resp.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                        with z.open('CORPCODE.xml') as f:
                            tree = ET.parse(f)
                            root = tree.getroot()
                            for list_node in root.findall('list'):
                                c_name = list_node.find('corp_name').text
                                c_code = list_node.find('corp_code').text
                                self.dart_corp_codes[c_name] = c_code
            
            corp_code = self.dart_corp_codes.get(company_name)
            if not corp_code:
                # "(주)" 같은 문자열이 포함/제외된 경우를 위한 부분 매칭 시도
                for name, code in self.dart_corp_codes.items():
                    if company_name in name or name in company_name:
                        corp_code = code
                        break

            if not corp_code:
                return "DART 고유번호를 찾을 수 없습니다."

            # 2. 기업 개요 가져오기
            info_url = f"https://opendart.fss.or.kr/api/company.json?crtfc_key={dart_key}&corp_code={corp_code}"
            info_resp = requests.get(info_url, timeout=5)
            if info_resp.status_code == 200 and info_resp.json().get("status") == "000":
                data = info_resp.json()
                return f"대표자명: {data.get('ceo_nm')}\n법인구분: {data.get('corp_cls')}\n주요사업: {data.get('induty_nm')}"
            return "DART 기업 정보 조회 실패"
        except Exception as e:
            return f"DART 수집 에러: {str(e)}"

    def scrape_company_info(self, company_name: str) -> Dict[str, Any]:
        """
        다양한 외부 소스(구글 뉴스, 네이버 뉴스, DART)에서 기업 정보를 수집합니다.
        """
        google_news = self._get_google_news(company_name)
        naver_news = self._get_naver_news(company_name)
        dart_info = self._get_dart_info(company_name)

        combined_info = f"""
[DART 기업정보]
{dart_info}

[최근 구글 뉴스]
{google_news}

[최근 네이버 뉴스]
{naver_news}
"""
        return {
            "success": True,
            "company_name": company_name,
            "company_info": combined_info.strip(),
        }

scraper_service = ScraperService()
