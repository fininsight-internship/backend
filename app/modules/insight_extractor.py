import os
import hashlib
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 간단한 인메모리 캐시 (실제 서비스에서는 Redis 등으로 교체)
_cache = {}

SYSTEM_PROMPT = """당신은 기업 분석 전문가입니다.
주어진 기업 분석 보고서를 읽고 아래 항목만 정확하게 추출해주세요.
보고서에 없는 내용은 절대 지어내지 말 것."""

OUTPUT_FORMAT = """
아래 기업 분석 보고서를 읽고 정해진 항목만 추출해줘.

[기업 분석 보고서]
{report_text}

반드시 아래 형식으로만 출력할 것:

[핵심 전략 과제]
- 1~2개, 각 1문장으로 작성

[인재상 키워드]
- 최대 5개, 단어로만 작성

[최근 주요 성과]
- 1~2개, 각 1문장으로 작성

[직무 관련 사업 영역]
- 1~2개, 각 1문장으로 작성

[기업 차별적 가치]
- 1개, 1문장으로 작성

추출 규칙:
1. 각 항목은 반드시 개수 제한을 준수할 것
2. 보고서에 명시되지 않은 내용은 절대 추가하지 말 것
3. 원문의 표현을 최대한 유지하되 불필요한 내용은 제거할 것
4. 항목별 내용이 보고서에 없을 경우 "해당 없음"으로 표기할 것
"""


class InsightExtractor:
    def extract(self, report_text: str) -> str:
        # 보고서 원문의 해시값으로 캐시 키 생성
        cache_key = hashlib.md5(report_text.encode()).hexdigest()

        # 캐시에 있으면 바로 반환
        if cache_key in _cache:
            print("[InsightExtractor] 캐시에서 인사이트 로드")
            return _cache[cache_key]

        # 캐시에 없으면 GPT 호출
        print("[InsightExtractor] GPT 호출하여 인사이트 추출")
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0,  # 팩트 추출이므로 0으로 고정
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": OUTPUT_FORMAT.format(report_text=report_text)}
            ]
        )

        insights = response.choices[0].message.content

        # 결과 캐싱
        _cache[cache_key] = insights
        return insights