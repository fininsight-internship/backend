"""
RAG 데이터 레이어 (PoC)
- 실제 서비스에서는 DB/벡터스토어에서 조회
- PoC에서는 KoDATA 기업 신용 위험관리 컨설팅 직무 데이터를 하드코딩으로 내장
"""

# ─────────────────────────────────────────────────────────────
# 1. 평가축 Taxonomy (고정 — LLM이 생성하지 않음!)
# ─────────────────────────────────────────────────────────────
FEATURE_TAXONOMY = {
    "data_analysis": {
        "name": "데이터 분석력",
        "description": "데이터를 수집·정제·분석하여 의미 있는 인사이트를 도출하는 능력",
        "keywords": [
            "EDA", "전처리", "데이터 분석", "SQL", "Python", "pandas", "데이터 정합성",
            "데이터 검증", "중복", "누락값", "이상치", "집계", "추출", "전처리", "정제",
            "클러스터링", "시각화", "Tableau", "Excel", "데이터 품질"
        ],
    },
    "risk_judgment": {
        "name": "리스크 판단력",
        "description": "기업 데이터를 기반으로 신용 위험 요소를 해석하고 판단하는 능력",
        "keywords": [
            "리스크", "위험", "신용", "부도", "건전성", "위험 관리", "재무 흐름",
            "위험 요소", "리스크 분석", "판단", "평가", "신용평가", "안정성"
        ],
    },
    "financial_understanding": {
        "name": "재무/회계 이해",
        "description": "재무제표, 재무비율 등 기업 재무 구조를 이해하고 해석하는 능력",
        "keywords": [
            "재무", "회계", "재무제표", "손익계산서", "재무상태표", "현금흐름표",
            "부채비율", "유동비율", "영업이익률", "재무비율", "재무 데이터", "재무 흐름",
            "KODATA", "기업 정보", "재무계정", "매핑"
        ],
    },
    "logical_reporting": {
        "name": "논리적 보고/커뮤니케이션",
        "description": "분석 결과를 논리적으로 정리하여 이해관계자에게 설명하는 능력",
        "keywords": [
            "보고", "문서", "커뮤니케이션", "발표", "설명", "논리", "정리", "대시보드",
            "인사이트 전달", "시각화", "스토리텔링", "이해관계자", "피드백"
        ],
    },
    "problem_structuring": {
        "name": "문제 구조화",
        "description": "복잡한 데이터에서 핵심 문제를 정의하고 구조적으로 접근하는 능력",
        "keywords": [
            "문제 정의", "가설", "구조화", "문제 해결", "원인 분석", "패턴 발견",
            "인사이트", "검증", "분석 구조", "핵심 요인", "개선 포인트"
        ],
    },
    "collaboration": {
        "name": "협업 및 갈등 해결",
        "description": "팀원 또는 타부서와 협력하고 의견 충돌을 건설적으로 해결하는 능력",
        "keywords": [
            "협업", "갈등", "팀", "소통", "의견 조율", "부서 간", "협력", "팀 프로젝트",
            "의견 충돌", "합의", "공통 언어", "커뮤니케이션"
        ],
    },
    "accuracy_diligence": {
        "name": "정확성/꼼꼼함",
        "description": "오류 없이 데이터를 처리하고 검증하는 꼼꼼한 업무 태도",
        "keywords": [
            "정확성", "꼼꼼", "검증", "신뢰성", "오류", "정합성", "정밀", "완결성",
            "단위 불일치", "타임박싱", "마감 기준", "정제"
        ],
    },
}

# ─────────────────────────────────────────────────────────────
# 2. RAG 문서 (JD + 기업분석 레포트 + 자소서)
#    실제 서비스에서는 DB에서 retrieval → 여기선 고정 데이터
# ─────────────────────────────────────────────────────────────
RAG_DOCUMENTS = [
    {
        "id": "doc-kodata-jd",
        "company": "한국평가데이터",
        "job_role": "기업 신용 위험관리 컨설팅",
        "source_type": "jd",
        "source_label": "채용공고 (JD)",
        "trust_weight": 1.0,
        "content": """
한국평가데이터(KoDATA) 기업 신용 위험관리 컨설팅 직무 채용공고

담당 업무:
- 기업 신용 위험 분석
- 재무 데이터 기반 평가
- 리스크 관리 지원
- 기업 정보 분석
- 보고 및 컨설팅 지원

필수 역량:
- 재무/회계 이해
- 데이터 분석 역량
- Excel 활용 능력
- 문서 작성 능력
- 논리적 사고

우대 역량:
- SQL 활용
- 데이터 분석 경험
- 금융/신용평가 관심
- 협업 및 커뮤니케이션 역량

조직이 원하는 인재상:
- 꼼꼼한 분석형
- 논리적 커뮤니케이션 가능
- 숫자 기반 사고 가능
- 안정적으로 업무 수행 가능

업무 스타일:
- 문서 기반 협업
- 데이터 검증
- 재무 데이터 해석
- 반복적 분석 업무
        """.strip(),
    },
    {
        "id": "doc-kodata-report",
        "company": "한국평가데이터",
        "job_role": "기업 신용 위험관리 컨설팅",
        "source_type": "company_analysis",
        "source_label": "기업 분석 레포트",
        "trust_weight": 0.95,
        "content": """
한국평가데이터(KoDATA) 기업 분석 레포트

핵심 사업:
KoDATA는 기업 데이터 및 신용평가 전문기관으로 기업 신용평가, 기술신용평가(TCB), ESG 평가, 기업 데이터 제공, 리스크 관리 서비스를 제공한다.

최근 방향성:
AI 기반 기업 데이터 분석, 데이터 플랫폼 고도화, 생성형 AI 활용, 리스크 분석 체계 강화 흐름을 보이고 있다.
단순 데이터 저장 기업이 아니라 데이터 기반 의사결정 지원 기업으로 사업 영역을 강화하는 중이다.

핵심 직무 요구 역량 분석:
1. 숫자를 해석하는 역량 — 기업 상태를 읽는 능력, 재무 흐름 이해, 위험 요소 해석이 핵심
2. 논리적 보고 역량 — 분석 내용 설명 가능, 논리적 정리 능력
3. 운영 + 분석 혼합형 성향 — 데이터 운영, 분석, 평가 지원 혼합

강조해야 할 경험 TOP3:
1. 데이터 기반 문제 정의 경험 — 데이터를 통해 위험 요소를 해석하는 역량
2. SQL/Excel 기반 데이터 처리 경험 — 데이터 검증, 정리, 지표 분석
3. 협업 기반 프로젝트 경험 — 현업 담당자와 문제 정의 경험

보완이 필요한 역량:
- 재무/회계 도메인 지식 (재무상태표, 손익계산서, 현금흐름표)
- 금융/신용평가 도메인 이해 (신용평가 구조, 기업 리스크 요소)

면접 예상 질문:
- 왜 신용 위험관리 직무를 선택했나요?
- 데이터 분석과 리스크 분석의 차이는 무엇이라고 생각하나요?
- 기업 리스크를 판단할 때 중요한 요소는 무엇이라고 생각하나요?
- 금융 경험이 부족한데 왜 적합하다고 생각하나요?
- 재무제표를 실제로 읽을 수 있나요?
- 반복적 분석 업무도 괜찮나요?
- SQL은 어느 수준까지 가능한가요?
- 데이터 검증은 어떻게 수행했나요?
- 현업 담당자와 의견 충돌 시 어떻게 대응했나요?
        """.strip(),
    },
    {
        "id": "doc-kodata-resume",
        "company": "한국평가데이터",
        "job_role": "기업 신용 위험관리 컨설팅",
        "source_type": "resume",
        "source_label": "지원자 자기소개서",
        "trust_weight": 1.0,
        "content": """
지원자 자기소개서 (KoDATA 기업 신용 위험관리 컨설팅 직무)

[문항 1. 지원 동기]
데이터가 틀리면 분석도 틀린다는 것을 몸으로 배운 경험이 KODATA 재무/회계 데이터 관리 직무에 지원하게 된 출발점입니다.
청년취업사관학교 데이터 분석 부트캠프에서 쥬얼리 브랜드의 고객 데이터를 분석하던 중, 전처리 단계에서 매출 데이터의 단위 불일치를 발견한 적이 있습니다. 수치 하나가 잘못 분류된 것이었지만, 그것이 수정되기 전까지 팀 전체의 분석 방향이 흔들렸습니다. 그 경험을 통해 분석의 화려함보다 데이터의 정확성과 신뢰성이 모든 의사결정의 근간임을 깊이 느꼈습니다.
SQL과 Python을 활용한 데이터 정합성 검증 경험과 SQLD 자격증을 바탕으로 빠르게 실무에 적응하고, 장기적으로는 KODATA의 재무 데이터 상품 신뢰도를 높이는 데 기여하겠습니다.

[문항 2. 성격의 장단점]
장점은 데이터로 먼저 확인하고 판단하는 습관입니다. 직관보다 근거를 우선하는 성격 덕분에, 팀 프로젝트에서 분석 결과에 대한 신뢰도가 높다는 평가를 받아왔습니다. 쥬얼리 브랜드 프로젝트에서 메타광고 비효율 구간을 발견할 때도 단순한 수치 비교가 아닌 EDA 분석과 가설 검정을 통해 원인을 규명했습니다.
단점은 완결성을 추구하다 보니 의사결정 속도가 느려질 때가 있다는 점입니다. 이후 타임박싱 방식을 도입하면서 정확성과 효율 사이의 균형을 맞춰가고 있습니다.

[문항 3. 데이터 분석 툴 활용 사례]
Python(pandas, scikit-learn), SQL(SQLD 자격증, 복합 조인, 서브쿼리), Excel, Tableau를 활용합니다.
쥬얼리 브랜드 프로젝트에서 고객 데이터와 매출 데이터를 결합하는 과정에서 단위 불일치, 중복값, 누락값 등 다양한 정합성 문제를 SQL과 Python으로 탐지하고 정제하였습니다.

[문항 4. 갈등 극복 사례]
부트캠프 파이널 프로젝트에서 발표 방향을 두고 팀원과 의견이 갈린 적이 있습니다. 정성적 시장 인사이트 중심 vs 정량 분석 결과 중심으로 충돌했습니다. 두 방향의 초안을 각각 작성하여 팀 전체가 직접 비교할 수 있도록 제안했고, 팀원 스스로 데이터 기반 접근의 강점을 확인하며 합의가 이루어졌습니다. 현업 담당자로부터 분석 완성도가 높다는 긍정적인 피드백을 받았습니다.

[문항 5. 창의적 문제 해결 사례]
청년 주거 간담회 프로젝트에서 모두가 '비용 부담'을 핵심 문제로 정의하고 있었지만, 청년삶실태조사 데이터를 직접 분석하여 '사회적 고립'이 주거 만족도에 유의미한 영향을 미친다는 패턴을 발견했습니다. 이를 근거로 '청년 공유형 하우스' 모델을 정책 대안으로 제안했습니다.
        """.strip(),
    },
]

# ─────────────────────────────────────────────────────────────
# 3. 지원 가능한 포지션 목록 (Mock-context 대체)
# ─────────────────────────────────────────────────────────────
AVAILABLE_POSITIONS = [
    {
        "id": "kodata-credit-risk",
        "company": "한국평가데이터(KoDATA)",
        "job_role": "기업 신용 위험관리 컨설팅",
        "description": "기업 데이터를 기반으로 신용 위험을 분석하고, 금융기관 의사결정에 필요한 판단 근거를 제공하는 직무",
        "required_skills": ["데이터 분석", "SQL", "Excel", "재무/회계 이해", "논리적 사고"],
        "company_culture": "데이터 신뢰성과 분석 정확성을 최우선으로 하는 조직. 문서 기반 커뮤니케이션과 리스크 판단 역량을 중요시함.",
        "doc_ids": ["doc-kodata-jd", "doc-kodata-report", "doc-kodata-resume"],
    }
]


# ─────────────────────────────────────────────────────────────
# 4. Feature Tagging — 키워드 기반 (MVP)
# ─────────────────────────────────────────────────────────────
def tag_features(text: str) -> dict[str, float]:
    """
    텍스트에서 평가축 키워드를 탐지하여 {feature_key: raw_count} 반환.
    대소문자·공백 무시 매칭.
    """
    text_lower = text.lower()
    counts: dict[str, float] = {}
    for key, info in FEATURE_TAXONOMY.items():
        hits = sum(1 for kw in info["keywords"] if kw.lower() in text_lower)
        if hits > 0:
            counts[key] = hits
    return counts


# ─────────────────────────────────────────────────────────────
# 5. Weight 계산
# ─────────────────────────────────────────────────────────────
def compute_feature_weights(company: str, job_role: str, include_resume: bool = False) -> dict[str, float]:
    """
    해당 company+job_role의 RAG 문서 전체를 스캔하여
    평가축별 가중 빈도를 계산하고 0~1 normalize해서 반환.
    """
    # 해당 포지션 문서 필터링
    docs = [d for d in RAG_DOCUMENTS if d["company"] == company and d["job_role"] == job_role]

    if not include_resume:
        docs = [d for d in docs if d["source_type"] != "resume"]

    if not docs:
        # fallback: 전체 문서
        docs = RAG_DOCUMENTS
        if not include_resume:
            docs = [d for d in docs if d["source_type"] != "resume"]

    aggregated: dict[str, float] = {}
    for doc in docs:
        trust = doc["trust_weight"]
        counts = tag_features(doc["content"])
        for feat, cnt in counts.items():
            aggregated[feat] = aggregated.get(feat, 0) + cnt * trust

    if not aggregated:
        return {}

    max_val = max(aggregated.values())
    if max_val == 0:
        return {}

    return {k: round(v / max_val, 3) for k, v in sorted(aggregated.items(), key=lambda x: -x[1])}


# ─────────────────────────────────────────────────────────────
# 6. Retrieval — 관련 문서 텍스트 조합
# ─────────────────────────────────────────────────────────────
def retrieve_context(company: str, job_role: str) -> dict:
    """
    JD, 기업분석, 자소서 문서를 retrieval하여 반환.
    """
    docs = [d for d in RAG_DOCUMENTS if d["company"] == company and d["job_role"] == job_role]
    result = {
        "jd": "",
        "company_analysis": "",
        "resume": "",
        "all_combined": "",
        "sources": [],
    }
    for doc in docs:
        result["sources"].append({"id": doc["id"], "label": doc["source_label"]})
        if doc["source_type"] == "jd":
            result["jd"] = doc["content"]
        elif doc["source_type"] == "company_analysis":
            result["company_analysis"] = doc["content"]
        elif doc["source_type"] == "resume":
            result["resume"] = doc["content"]

    result["all_combined"] = "\n\n---\n\n".join([
        f"[{doc['source_label']}]\n{doc['content']}" for doc in docs
    ])
    return result
