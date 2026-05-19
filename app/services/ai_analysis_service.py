import os
import json
from openai import AsyncOpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AIAnalysisService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def analyze_company_and_jd(self, company_name: str, company_info: str, jd_text: str, resume_text: str) -> Dict[str, Any]:
        """
        기업 정보, JD, 이력서를 바탕으로 고도화된 심층 분석 리포트를 생성합니다.
        """
        system_prompt = """
        당신은 상위 1%의 전문적인 채용 컨설턴트이자 헤드헌터입니다.
        주어진 [최신 기업 정보(뉴스 및 DART)], [채용 공고(JD)], 그리고 [지원자의 이력서]를 심층 분석하여
        단순 정보 나열이 아닌, 사용자가 실제 서류 작성 및 면접 준비에 즉시 활용할 수 있는 '실전 지원 전략'을 JSON 형식으로 작성해주세요.

        **작성 지침 (필독)**:
        1. 모든 분석은 '지원자가 지원하는 특정 직무(JD)'와 '지원자의 이력서'를 교차 검증한 결과를 바탕으로 해야 합니다.
        2. 기업 분석 역시 일반론적인 이야기가 아닌, "이 직무에 지원하는 사람이 반드시 알아야 할" 기업의 핵심 사업, 최근 이슈, 조직 방향성으로 서술하십시오.
        3. 단순 요약은 피하고, 최소 3~5문장 이상으로 구체적 사례나 뉴스 이슈, 이력서의 특정 경험을 인용하여 상세히 기술하십시오.
        
        결과는 반드시 유효한 JSON 포맷이어야 하며 다음 스키마를 엄격히 따르십시오:
        {
            "company_analysis": {
                "core_business": "(상세 서술) 직무와 관련된 회사의 핵심 사업 및 비즈니스 모델",
                "recent_issues": ["(직무 연관) 최근 이슈 1", "(직무 연관) 최근 이슈 2"],
                "organizational_direction": "(상세 서술) 뉴스와 공시를 바탕으로 한 조직의 향후 방향성",
                "required_competencies_from_company": ["기업 인재상 기반 요구 역량 1", "기업 인재상 기반 요구 역량 2"],
                "interview_context": "(상세 서술) 자소서 및 면접에서 기업 컨텍스트로 활용할 수 있는 핵심 인사이트 및 어필 포인트"
            },
            "job_analysis": {
                "core_requirements": ["JD 핵심 요구사항 1", "JD 핵심 요구사항 2", "JD 핵심 요구사항 3"],
                "tech_stacks": ["요구 기술 스택 1", "요구 기술 스택 2"],
                "preferred_qualifications": ["우대사항 1", "우대사항 2"],
                "strategic_importance": "(상세 서술) 이 직무가 회사의 핵심 사업/이슈에 어떻게 전략적으로 기여하는지"
            },
            "fit_analysis": {
                "score": 85,
                "evaluation": "(상세 서술) 현재 이력서와 JD/기업 방향성과의 종합 적합도 평가",
                "lacking_competencies": ["이력서 상 부족한 역량 1", "이력서 상 부족한 역량 2"]
            },
            "document_optimization": {
                "experiences_to_highlight": ["이력서에서 반드시 강조해야 할 경험 1 (이유 포함)", "이력서에서 반드시 강조해야 할 경험 2 (이유 포함)"],
                "modification_direction": ["이력서/자소서 구체적 수정 방향 1 (STAR 기법 등 적용)", "이력서/자소서 구체적 수정 방향 2"]
            }
        }
        """

        user_prompt = f"""
        [기업명]: {company_name}
        
        [최신 수집된 기업 정보(뉴스 및 공시)]: 
        {company_info}
        
        [채용 공고(JD)]: 
        {jd_text}
        
        [지원자 이력서]: 
        {resume_text}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            
            result_json_str = response.choices[0].message.content
            return json.loads(result_json_str)
        except Exception as e:
            return {"error": str(e)}

ai_analysis_service = AIAnalysisService()
