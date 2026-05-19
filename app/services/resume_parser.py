import io
import PyPDF2
import docx
from typing import Dict, Any

class ResumeParser:
    def parse(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        업로드된 이력서 파일(PDF, DOCX)에서 텍스트를 추출합니다.
        """
        ext = filename.split('.')[-1].lower()
        extracted_text = ""
        success = False
        error_message = None

        try:
            if ext == 'pdf':
                reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
                success = True
            elif ext in ['doc', 'docx']:
                doc = docx.Document(io.BytesIO(file_bytes))
                for para in doc.paragraphs:
                    extracted_text += para.text + "\n"
                success = True
            else:
                error_message = f"지원하지 않는 파일 형식입니다: {ext}"
        except Exception as e:
            error_message = f"파일 파싱 중 오류 발생: {str(e)}"

        return {
            "success": success,
            "filename": filename,
            "text": extracted_text.strip() if success else "",
            "error": error_message
        }

resume_parser = ResumeParser()
