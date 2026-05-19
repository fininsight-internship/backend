## JD ##

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """당신은 채용 공고(JD) 분석 전문가입니다.
주어진 채용 공고를 읽고 핵심 정보만 구조적으로 추출해주세요."""

OUTPUT_FORMAT = """
아래 채용 공고를 분석하고 정해진 형식으로만 출력하세요.

[채용 공고]
{jd_text}

반드시 아래 형식으로만 출력할 것:

[직무 요약]
- 1~2문장으로 직무의 핵심 역할 설명

[필수 역량]
- 최대 5개, 각 1문장

[우대 역량]
- 최대 3개, 각 1문장

[핵심 키워드]
- 최대 7개, 단어로만

[직무 인사이트]
- 이 JD가 자소서 작성에 주는 핵심 힌트 1~2문장
"""


def analyze_jd(jd_text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": OUTPUT_FORMAT.format(jd_text=jd_text)}
        ]
    )
    analysis = response.choices[0].message.content
    return {"status": "success", "analysis": analysis}
