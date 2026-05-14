## JD ##
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

BASE_DIR = os.path.dirname(
    __file__
)

JD_DATA_DIR = os.path.join(
    BASE_DIR,
    "../../data/jd"
)

RESUME_DATA_DIR = os.path.join(
    BASE_DIR,
    "../../data/resume"
)

def extract_json(
    content: str
):

    content = (
        content
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    match = re.search(
        r"\{.*\}",
        content,
        re.DOTALL
    )

    if match:
        content = match.group()

    try:

        return json.loads(
            content
        )

    except Exception as e:

        print(
            "JSON 파싱 실패:",
            e
        )

        return {}

def ask_llm(
    prompt: str,
    max_tokens=2000
):

    response = client.chat.completions.create(

        model="gpt-4o-mini",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.3,

        max_tokens=max_tokens
    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    return extract_json(
        content
    )

def save_jd_json(
    job_id: str,
    data: dict
):

    os.makedirs(

        JD_DATA_DIR,

        exist_ok=True
    )

    filepath = os.path.join(

        JD_DATA_DIR,

        f"{job_id}.json"
    )

    output = {

        "meta": {

            "job_id": job_id,

            "created_at": (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
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

def load_jd_json(
    job_id: str
):

    filepath = os.path.join(

        JD_DATA_DIR,

        f"{job_id}.json"
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

        return json.load(
            f
        )

def load_resume_json(
    user_id: str
):

    filepath = os.path.join(

        RESUME_DATA_DIR,

        f"{user_id}_resume.json"
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

        return json.load(
            f
        )

def analyze_jd(
    jd_text: str,
    job_id: str = ""
):

    prompt = f"""
아래 채용공고를 분석해라.

{jd_text}

반드시 JSON만 출력.

{{
  "summary": "",
  "responsibilities": [],
  "requirements": {{
    "essential": {{}},
    "preferred": {{}}
  }},
  "keywords": [],
  "insight": ""
}}
"""

    parsed = ask_llm(
        prompt,
        1500
    )

    saved_path = None

    if job_id:

        saved_path = save_jd_json(

            job_id,

            parsed
        )

    return {

        "status": "success",

        "saved_path": saved_path,

        "data": parsed
    }

def generate_ideal_resume(
    jd_analysis: dict
):

    prompt = f"""
아래 JD 분석 결과 기반으로
이상적인 지원자 기준표 작성.

{json.dumps(jd_analysis, ensure_ascii=False)}

반드시 JSON만 출력.

{{
  "핵심역량": [],
  "기술스택": {{
    "main": [],
    "sub": []
  }},
  "학력": {{}},
  "경력": {{}},
  "자격증": [],
  "외국어": [],
  "프로젝트": []
}}
"""

    parsed = ask_llm(
        prompt,
        1500
    )

    return {

        "status": "success",

        "data": parsed
    }


def analyze_gap(
    ideal_resume: dict,
    actual_resume: dict
):

    prompt = f"""
이상적 지원자 기준과
실제 이력서를 비교해라.

[B]
{json.dumps(ideal_resume, ensure_ascii=False)}

[A]
{json.dumps(actual_resume, ensure_ascii=False)}

반드시 JSON만 출력.

{{
  "적합도": "",
  "지원가능여부": "",
  "강점": [],
  "부족한점": [],
  "보완방법": []
}}
"""

    parsed = ask_llm(
        prompt
    )

    return {

        "status": "success",

        "data": parsed
    }

def generate_resume_content(
    jd_analysis: dict,
    gap_analysis: dict,
    actual_resume: dict
):

    prompt = f"""
JD와 gap 분석을 기반으로
이력서를 최적화해라.

[JD]
{json.dumps(jd_analysis, ensure_ascii=False)}

[GAP]
{json.dumps(gap_analysis, ensure_ascii=False)}

[RESUME]
{json.dumps(actual_resume, ensure_ascii=False)}

반드시 JSON만 출력.

{{
  "핵심역량": [],
  "기술스택": {{
    "main": [],
    "sub": []
  }},
  "경력": [],
  "프로젝트": [],
  "자격증": [],
  "이력서_작성_팁": []
}}
"""

    parsed = ask_llm(
        prompt
    )

    return {

        "status": "success",

        "data": parsed
    }
