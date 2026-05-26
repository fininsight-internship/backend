from app.modules.insight_extractor import InsightExtractor
from app.modules.cover_letter_generator import CoverLetterGenerator
from app.modules.evaluator_gpt import EvaluatorGPT
import re


class CoverLetterPipeline:
    def __init__(self):
        self.extractor = InsightExtractor()
        self.generator = CoverLetterGenerator()
        self.evaluator = EvaluatorGPT()

    def run(self, report_text: str, questions: list, user_info: dict, company_name: str, jd_analysis: str = "해당 없음") -> list:
        print("\n[Pipeline] 1단계: 기업 보고서 인사이트 추출")
        insights = self.extractor.extract(report_text)

        results = []

        for i, q in enumerate(questions):
            print(f"\n[Pipeline] 문항 {i+1}/{len(questions)} 처리 중: {q['question'][:20]}...")

            context = {
                "company_name": company_name,
                "insights": insights,
                "jd_analysis": jd_analysis,
                "question": q["question"],
                "char_limit": q["char_limit"],
                "experiences": user_info["experiences"],
                "skills": user_info["skills"],
                "education": user_info["education"],
                "extra": user_info.get("extra", "없음")
            }

            draft = self.generator.generate(context)

            best_draft = draft
            best_evaluation = ""
            best_score = -1

            for attempt in range(3):
                evaluation = self.evaluator.evaluate(draft, context)
                scores = self._parse_scores(evaluation)
                min_score = min(scores) if scores else 0

                print(f"[Pipeline] 시도 {attempt + 1}: 현재 최저 점수 {min_score}점")

                if min_score > best_score:
                    best_score = min_score
                    best_draft = draft
                    best_evaluation = evaluation

                if min_score >= 85 or attempt == 2:
                    break

                print(f"[Pipeline] 점수 미달({min_score} < 85). 피드백 반영하여 재작성합니다.")
                draft = self.generator.refine(draft, evaluation, context)

            results.append({
                "question": q["question"],
                "draft": best_draft,
                "evaluation": best_evaluation,
                "score": best_score
            })

        print("\n[Pipeline] 전체 처리 완료")
        return results

    def _parse_scores(self, evaluation: str) -> list:
        scores = re.findall(r"종합 점수\]: (\d+)점", evaluation)
        return [int(s) for s in scores]
