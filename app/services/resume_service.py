## 자소서 ## 자기소개서는 다시 만드시길.. resume = 이력서 
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

RESUME_DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../data/resume"
)

def _safe_json_parse(content: str):

    content = content.replace(
        "```json",
        ""
    ).replace(
        "```",
        ""
    ).strip()

    match = re.search(
        r"\{.*\}",
        content,
        re.DOTALL
    )

    if match:
        content = match.group()

    try:
        return json.loads(content)

    except Exception as e:

        print("❌ JSON 파싱 실패:", e)

        return {}

def save_resume_json(
    user_id: str,
    data: dict
):

    os.makedirs(
        RESUME_DATA_DIR,
        exist_ok=True
    )

    filename = f"{user_id}_resume.json"

    filepath = os.path.join(
        RESUME_DATA_DIR,
        filename
    )

    output = {
        "meta": {
            "user_id": user_id,
            "created_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        },
        "data": data
    }

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    return filepath

def load_resume_json(
    user_id: str
):

    filename = f"{user_id}_resume.json"

    filepath = os.path.join(
        RESUME_DATA_DIR,
        filename
    )

    if not os.path.exists(
        filepath
    ):
        return None

    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)

def parse_resume_text(
    resume_text: str
):

    prompt = f"""
아래는 지원자의 이력서 텍스트다.

{resume_text}

아래 규칙을 반드시 지켜라.

1. 이력서에 있는 내용만 추출해라.
2. 없는 내용은 절대 만들지 마라.
3. 해석하지 말고 사실 그대로만 추출해라.
4. 없는 항목은 빈 값으로 둬라.

절대 JSON 외 출력 금지
설명 금지
코드블록 금지

반드시 JSON만 출력.

{{
  "학력": [
    {{
      "학교명": "",
      "전공": "",
      "학점": "",
      "입학": "",
      "졸업": "",
      "졸업구분": ""
    }}
  ],
  "경력": [
    {{
      "회사명": "",
      "부서": "",
      "직책": "",
      "시작일": "",
      "종료일": "",
      "주요업무": [],
      "성과": []
    }}
  ],
  "경험": [
    {{
      "활동명": "",
      "활동처": "",
      "시작일": "",
      "종료일": "",
      "활동내용": []
    }}
  ],
  "교육": [
    {{
      "기관명": "",
      "과정명": "",
      "시작일": "",
      "종료일": "",
      "교육내용": []
    }}
  ],
  "자격증": [
    {{
      "자격명": "",
      "취득일": "",
      "발급기관": ""
    }}
  ],
  "외국어": [
    {{
      "언어": "",
      "시험명": "",
      "점수": "",
      "취득일": ""
    }}
  ],
  "기술스택": {{
    "main": [],
    "sub": []
  }},
  "프로젝트": [
    {{
      "프로젝트명": "",
      "역할": "",
      "시작일": "",
      "종료일": "",
      "사용기술": [],
      "주요업무": [],
      "성과": []
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=2000
    )

    parsed = _safe_json_parse(
        response.choices[0].message.content
    )

    return {
        "status": "success",
        "data": parsed
    }