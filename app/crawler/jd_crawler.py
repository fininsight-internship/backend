import json
import re
import os
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0"
    )
}

BASE_DIR = os.path.dirname(
    __file__
)

SAVE_DIR = os.path.join(
    BASE_DIR,
    "../data/jd"
)

SECTION_KEYS = {

    "담당업무": "tasks",
    "주요업무": "tasks",

    "스킬": "skills",
    "기술스택": "skills",

    "자격요건": "requirements",
    "지원자격": "requirements",

    "우대사항": "preferred",

    "전형절차": "process",

    "유의사항": "notes"
}

EMPTY_DATA = {

    "tasks": [],
    "skills": [],
    "requirements": [],
    "preferred": [],
    "process": [],
    "notes": []
}

def extract_job_id(url):

    match = re.search(
        r"/GI_Read/(\d+)",
        url
    )

    if not match:

        raise ValueError(
            "잘못된 URL"
        )

    return match.group(1)

def build_iframe_url(
    job_id
):

    return (
        "https://www.jobkorea.co.kr/"
        "Recruit/GI_Read_Comt_Ifrm"
        f"?Gno={job_id}"
        "&isHiringCenter=false"
        "&hideMapView=true"
    )

def normalize_text(text):

    text = text.replace(
        "\xa0",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()

def extract_headcount(text):

    match = re.search(
        r"\(\s*([0-9O○]+명)\s*\)",
        text
    )

    if match:
        return match.group(1)

    return None

def save_json(
    job_id,
    payload
):

    os.makedirs(
        SAVE_DIR,
        exist_ok=True
    )

    filepath = os.path.join(
        SAVE_DIR,
        f"{job_id}.json"
    )

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )

def crawl_jobkorea(
    source_url
):

    job_id = extract_job_id(
        source_url
    )

    iframe_url = build_iframe_url(
        job_id
    )

    try:

        response = httpx.get(

            iframe_url,

            headers=HEADERS,

            timeout=10.0
        )

        response.raise_for_status()

    except Exception as e:

        return {

            "job_id": job_id,

            "source_url": source_url,

            "error": str(e),

            "data": EMPTY_DATA.copy()
        }

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    lines = [

        normalize_text(
            line
        )

        for line in soup.stripped_strings
    ]

    metadata = {

        "headcount": None,

        "english_resume_required": False
    }

    result = {

        key: []

        for key in EMPTY_DATA
    }

    current_section = None

    for line in lines:

        headcount = extract_headcount(
            line
        )

        if headcount:

            metadata[
                "headcount"
            ] = headcount

            continue

        if (
            "영문" in line
            and "이력서" in line
        ):

            metadata[
                "english_resume_required"
            ] = True

            continue

        found = False

        for korean, english in SECTION_KEYS.items():

            if korean in line:

                current_section = english

                found = True

                break

        if found:
            continue

        if current_section is None:
            continue

        cleaned = re.sub(

            r"^[ㆍ·\-●•①②③\d.]+\s*",

            "",

            line

        ).strip()

        if not cleaned:
            continue

        result[
            current_section
        ].append(
            cleaned
        )

    return {

        "job_id": job_id,

        "source_url": source_url,

        "iframe_url": iframe_url,

        "metadata": metadata,

        "error": None,

        "data": result
    }

def crawl_and_save(
    source_url
):

    payload = crawl_jobkorea(
        source_url
    )

    if payload.get(
        "error"
    ):

        return payload

    save_json(

        payload["job_id"],
        payload
    )
    return payload