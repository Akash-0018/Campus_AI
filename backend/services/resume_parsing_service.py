"""Resume parsing service for Campus AI"""
import logging
from typing import Optional, Dict, List
import re

import pdfplumber
import pytesseract
from PIL import Image
from docx import Document

from services.llm_service import llm_service

logger = logging.getLogger(__name__)


class ResumeParsingService:
    """Service for parsing resume documents with LLM enhancement"""

    SKILL_KEYWORDS = {
        'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust', 'php', 'ruby', 'swift'],
        'web': ['html', 'css', 'react', 'vue', 'angular', 'nodejs', 'express', 'django', 'flask'],
        'databases': ['sql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch', 'oracle'],
        'cloud': ['aws', 'gcp', 'azure', 'kubernetes', 'docker', 'terraform'],
        'data': ['pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'spark', 'hadoop'],
        'tools': ['git', 'jira', 'ci/cd', 'jenkins', 'gitlab', 'github', 'vscode', 'vim']
    }

    EDUCATION_LEVELS = ['high school', 'bachelor', 'master', 'phd', 'doctorate', 'associate']

    MIN_VALID_TEXT_LENGTH = 300  # 🚨 critical guard

    def __init__(self):
        logger.info("ResumeParsingService initialized (LLM-enhanced, OCR-ready)")

    # ------------------------------------------------------------------
    # 1️⃣ PDF EXTRACTION (TEXT + OCR FALLBACK)
    # ------------------------------------------------------------------

    def parse_pdf(self, file_path: str) -> str:
        logger.info(f"[PDF_EXTRACTION_START] Processing PDF file: {file_path}")
        extracted_text = ""

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text(x_tolerance=2)
                    if page_text:
                        extracted_text += page_text + "\n"
                        logger.debug(f"[PDF_TEXT] Page {page_num}: {len(page_text)} chars")
        except Exception as e:
            logger.error(f"[PDF_TEXT_ERROR] pdfplumber failed: {e}", exc_info=True)

        logger.info(f"[PDF_TEXT_RESULT] Extracted {len(extracted_text)} characters using pdfplumber")

        # 🔥 OCR FALLBACK
        if len(extracted_text.strip()) < self.MIN_VALID_TEXT_LENGTH:
            logger.warning("[PDF_OCR_FALLBACK] Text too short, running OCR...")
            extracted_text = self._ocr_pdf(file_path)

        if len(extracted_text.strip()) < self.MIN_VALID_TEXT_LENGTH:
            logger.error("[PDF_EXTRACTION_FAILED] Unable to extract meaningful text from PDF")
            raise ValueError("PDF extraction failed (text + OCR)")

        logger.info(f"[PDF_EXTRACTION_SUCCESS] Final extracted length: {len(extracted_text)} characters")
        return extracted_text.strip()

    def _ocr_pdf(self, file_path: str) -> str:
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    image = page.to_image(resolution=300).original
                    ocr_text = pytesseract.image_to_string(image)
                    if ocr_text:
                        text += ocr_text + "\n"
                        logger.debug(f"[PDF_OCR] Page {page_num}: {len(ocr_text)} chars")
        except Exception as e:
            logger.error(f"[PDF_OCR_ERROR] OCR failed: {e}", exc_info=True)

        logger.info(f"[PDF_OCR_RESULT] Extracted {len(text)} characters using OCR")
        return text

    # ------------------------------------------------------------------
    # 2️⃣ DOCX / TXT
    # ------------------------------------------------------------------

    def parse_docx(self, file_path: str) -> str:
        logger.info(f"[DOCX_EXTRACTION_START] {file_path}")
        doc = Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        logger.info(f"[DOCX_EXTRACTION_SUCCESS] {len(text)} characters")
        return text.strip()

    def parse_txt(self, file_path: str) -> str:
        logger.info(f"[TXT_EXTRACTION_START] {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        logger.info(f"[TXT_EXTRACTION_SUCCESS] {len(text)} characters")
        return text.strip()

    def extract_text(self, file_path: str, file_type: str) -> str:
        if file_type == 'pdf':
            return self.parse_pdf(file_path)
        elif file_type == 'docx':
            return self.parse_docx(file_path)
        elif file_type == 'txt':
            return self.parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    # ------------------------------------------------------------------
    # 3️⃣ LLM CLEANING
    # ------------------------------------------------------------------

    def llm_clean_resume(self, raw_text: str) -> str:
        if len(raw_text.strip()) < self.MIN_VALID_TEXT_LENGTH:
            raise ValueError("Raw resume text too short for LLM processing")

        logger.info(f"[LLM_PROCESSING_START] Raw text length: {len(raw_text)}")

        prompt = f"""
You are an expert resume parser.

Convert the following raw resume text into a clean, well-structured resume.
Preserve ALL information.
Do NOT hallucinate.
Do NOT remove skills, experience, projects, education.

Return plain text only.

RESUME:
{raw_text}
"""

        cleaned_text = llm_service.generate_text(prompt)

        if not cleaned_text or len(cleaned_text.strip()) < self.MIN_VALID_TEXT_LENGTH:
            raise ValueError("LLM failed to reconstruct resume")

        logger.info(f"[LLM_PROCESSING_SUCCESS] Cleaned length: {len(cleaned_text)}")
        logger.debug(f"[LLM_OUTPUT_PREVIEW]\n{cleaned_text[:500]}")
        return cleaned_text.strip()

    # ------------------------------------------------------------------
    # 4️⃣ METADATA EXTRACTION
    # ------------------------------------------------------------------

    def extract_skills(self, text: str) -> List[str]:
        text_lower = text.lower()
        skills = {
            skill
            for group in self.SKILL_KEYWORDS.values()
            for skill in group
            if skill in text_lower
        }
        return sorted(skills)

    def extract_experience(self, text: str) -> Optional[int]:
        match = re.search(r'(\d+)\s*\+?\s*years?\s+(?:of\s+)?experience', text.lower())
        return int(match.group(1)) if match else None

    def extract_education(self, text: str) -> Optional[str]:
        for level in self.EDUCATION_LEVELS:
            if level in text.lower():
                return level.title()
        return None

    def extract_location(self, text: str) -> Optional[str]:
        for line in text.splitlines()[:5]:
            if ',' in line and len(line) < 60:
                return line.strip()
        return None

    # ------------------------------------------------------------------
    # 5️⃣ FINAL PIPELINE
    # ------------------------------------------------------------------

    def parse_resume(self, file_path: str, file_type: str) -> Dict:
        logger.info(f"[PARSE_RESUME_START] {file_path} ({file_type})")

        raw_text = self.extract_text(file_path, file_type)
        logger.info(f"[RAW_TEXT_LENGTH] {len(raw_text)}")

        clean_text = self.llm_clean_resume(raw_text)

        parsed_data = {
            "raw_text": raw_text,
            "clean_text": clean_text,
            "skills": self.extract_skills(clean_text),
            "experience_years": self.extract_experience(clean_text),
            "education": self.extract_education(clean_text),
            "location": self.extract_location(clean_text),
            "summary": clean_text[:500]
        }

        logger.info(f"[PARSE_RESUME_COMPLETE] Extracted skills={parsed_data['skills']}, "
                    f"experience={parsed_data['experience_years']}, "
                    f"education={parsed_data['education']}")

        return parsed_data


# Singleton
resume_parsing_service = ResumeParsingService()


def get_resume_parsing_service() -> ResumeParsingService:
    return resume_parsing_service
