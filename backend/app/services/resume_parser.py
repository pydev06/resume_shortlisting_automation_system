import io
import logging
import re
from typing import Optional

from PyPDF2 import PdfReader
from docx import Document

from ..core.cache_manager import cache_manager, CACHE_CONFIG

logger = logging.getLogger("resume_shortlisting")


@cache_manager.cached(ttl=CACHE_CONFIG['resume_parsing'], key_prefix="pdf_extract")
def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise ValueError(f"Failed to parse PDF: {e}")


@cache_manager.cached(ttl=CACHE_CONFIG['resume_parsing'], key_prefix="docx_extract")
def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc = Document(io.BytesIO(file_content))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {e}")
        raise ValueError(f"Failed to parse DOCX: {e}")


def extract_text(file_content: bytes, file_name: str) -> str:
    """Extract text from resume file based on extension"""
    ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
    
    if ext == 'pdf':
        return extract_text_from_pdf(file_content)
    elif ext == 'docx':
        return extract_text_from_docx(file_content)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def extract_years_of_experience(text: str) -> Optional[float]:
    """Extract years of experience from resume text using patterns"""
    patterns = [
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)',
        r'experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)',
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:in|of)\s*(?:software|development|engineering)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def extract_education(text: str) -> Optional[str]:
    """Extract education information from resume text"""
    education_keywords = [
        'bachelor', 'master', 'phd', 'doctorate', 'b.s.', 'b.a.', 'm.s.', 'm.a.',
        'b.tech', 'm.tech', 'b.e.', 'm.e.', 'mba', 'bba', 'bsc', 'msc',
        'computer science', 'engineering', 'information technology'
    ]
    
    lines = text.split('\n')
    education_lines = []
    
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in education_keywords):
            education_lines.append(line.strip())
    
    if education_lines:
        return "; ".join(education_lines[:3])  # Return top 3 education entries
    
    return None


def extract_candidate_name(text: str, file_name: str) -> str:
    """Try to extract candidate name from resume text or fall back to file name"""
    # Try to get name from first few lines (usually at the top of resume)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if lines:
        # First non-empty line is often the name
        first_line = lines[0]
        # Check if it looks like a name (2-4 words, no special characters except spaces)
        if re.match(r'^[A-Za-z\s]{2,50}$', first_line) and len(first_line.split()) <= 4:
            return first_line
    
    # Fall back to file name
    name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    # Clean up common patterns
    name = re.sub(r'[-_]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()
