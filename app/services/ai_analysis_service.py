import os
import json
from openai import AsyncOpenAI
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AIAnalysisService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def analyze_company_only(self, company_name: str, company_info: str) -> Dict[str, Any]:
        """
        기업 정보만을 바탕으로 기업 분석 보고서를 생성합니다.
        """
        system_prompt = """
        당신은 상위 1%의 전문적인 채용 컨설턴트이자 헤드헌터입니다.
        주어진 [최신 기업 정보(뉴스 및 DART)]를 심층 분석하여
        회사의 핵심 사업, 최근 이슈, 조직 방향성, 그리고 면접용 기업 컨텍스트 전략을 JSON 형식으로 작성해주세요.
        
        결과는 반드시 유효한 JSON 포맷이어야 하며 다음 스키마를 엄격히 따르십시오:
        {
            "core_business": "(상세 서술) 회사의 핵심 사업 및 비즈니스 모델",
            "recent_issues": ["최근 주요 이슈 1", "최근 주요 이슈 2", "최근 주요 이슈 3"],
            "organizational_direction": "(상세 서술) 뉴스와 공시를 바탕으로 한 조직의 향후 방향성 및 미래 비전",
            "required_competencies_from_company": ["기업 인재상 기반 요구 핵심 역량 1", "기업 인재상 기반 요구 핵심 역량 2", "기업 인재상 기반 요구 핵심 역량 3"],
            "interview_context": "(상세 서술) 자소서 및 면접에서 기업 컨텍스트로 활용할 수 있는 핵심 인사이트 및 어필 포인트"
        }
        """
        user_prompt = f"""
        [기업명]: {company_name}
        
        [최신 수집된 기업 정보(뉴스 및 공시)]: 
        {company_info}
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
            return {"error": f"기업 분석 실패: {str(e)}"}

    async def analyze_fit_and_jd(self, company_analysis: Dict[str, Any], jd_text: str, resume_text: str) -> Dict[str, Any]:
        """
        기업 분석 결과, JD, 이력서를 바탕으로 채용공고 분석 및 맞춤 이력서 적합도 분석 보고서를 생성합니다.
        """
        system_prompt = """
        당신은 상위 1%의 전문적인 채용 컨설턴트이자 헤드헌터입니다.
        제공된 [기업 분석 정보], [채용 공고(JD)], 그리고 [지원자의 이력서]를 바탕으로
        공고 분석(핵심요구사항, 스택 등)과 이력서 매칭 적합도 분석 및 자소서 수정 방향을 JSON 형식으로 작성해주세요.
        
        **중요**:
        - 공고(JD)를 면밀히 분석하여 채용 직무명(`job_role`)을 구체적으로 추출하십시오. (예: 프론트엔드 개발자, 데이터 엔지니어, 백엔드 개발자 등)
        
        결과는 반드시 유효한 JSON 포맷이어야 하며 다음 스키마를 엄격히 따르십시오:
        {
            "job_analysis": {
                "job_role": "채용 직무명 (예: 백엔드 개발자)",
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
                "modification_direction": ["이력서/자소서 구체적 수정 방향 1", "이력서/자소서 구체적 수정 방향 2"]
            }
        }
        """
        user_prompt = f"""
        [기업 분석 정보]:
        {json.dumps(company_analysis, ensure_ascii=False, indent=2)}
        
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
            return {"error": f"JD 및 적합도 분석 실패: {str(e)}"}

    async def analyze_company_and_jd(self, company_name: str, company_info: str, jd_text: str, resume_text: str) -> Dict[str, Any]:
        """
        하위 호환성을 위해 유지하는 단일 호출 메서드입니다.
        내부적으로 analyze_company_only와 analyze_fit_and_jd를 연속 호출하여 동일한 합본 응답 구조를 반환합니다.
        """
        comp_res = await self.analyze_company_only(company_name, company_info)
        if "error" in comp_res:
            return comp_res
            
        fit_res = await self.analyze_fit_and_jd(comp_res, jd_text, resume_text)
        if "error" in fit_res:
            return fit_res
            
        # 프론트엔드가 기대하는 합본 데이터 포맷 생성
        return {
            "company_analysis": comp_res,
            "job_analysis": fit_res.get("job_analysis", {}),
            "fit_analysis": fit_res.get("fit_analysis", {}),
            "document_optimization": fit_res.get("document_optimization", {})
        }

ai_analysis_service = AIAnalysisService()
