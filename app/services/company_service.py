## 기업 분석 ##

def generate_company_report(company: str, job: str = None):
    return {
        "status": "success",
        "company": company,
        "job": job,
        "data": {
            "summary": f"{company}는 테스트 기업입니다.",
            "issues": ["테스트 이슈1", "테스트 이슈2"],
            "business": {
                "main": ["테스트 사업"],
                "description": "테스트 설명"
            },
            "culture": {
                "keywords": ["테스트"],
                "description": "테스트 문화"
            },
            "job_insight": None,
            "strategy": ["테스트 전략"]
        }
    }