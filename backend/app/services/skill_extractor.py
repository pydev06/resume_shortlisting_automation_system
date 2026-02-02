import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

from ..core.config import get_settings
from ..core.cache_manager import cache_manager, CACHE_CONFIG

logger = logging.getLogger("resume_shortlisting")


class SkillExtractor:
    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
    
    @cache_manager.cached(ttl=CACHE_CONFIG['skill_extraction'], key_prefix="skill_extract")
    async def extract_skills_from_resume(self, resume_text: str) -> Dict[str, Any]:
        """Extract skills and other information from resume using OpenAI"""
        
        prompt = f"""Analyze the following resume text and extract structured information.

Resume Text:
{resume_text[:8000]}

IMPORTANT: Pay special attention to the EDUCATION section. Look for degree information like:
- Bachelor, Master, PhD, B.Tech, M.Tech, MBA, etc.
- Field of study (Computer Science, Engineering, etc.)
- If you find integrated programs, report them as the highest degree achieved

Return a JSON object with the following EXACT structure:
{{
    "skills": ["list of technical and soft skills found"],
    "experience_years": <number or null if not found>,
    "education": "highest education level and field (e.g., 'Master of Technology in Computer Science')",
    "previous_roles": ["list of job titles/roles"],
    "keywords": ["relevant industry keywords"]
}}

Be thorough in extracting skills - include programming languages, frameworks, tools, methodologies, and soft skills.
If education is not found, set it to null, but try hard to find it.
Return ONLY the JSON object, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert HR assistant that extracts structured information from resumes. Always respond with valid JSON only. Be especially careful to extract education information accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up response if it has markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            # Fallback education extraction if OpenAI missed it
            if not result.get('education'):
                result['education'] = self._extract_education_fallback(resume_text)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            # Try fallback extraction
            return {
                "skills": [],
                "experience_years": None,
                "education": self._extract_education_fallback(resume_text),
                "previous_roles": [],
                "keywords": []
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise ValueError(f"Failed to extract skills: {e}")
    
    def _extract_education_fallback(self, resume_text: str) -> Optional[str]:
        """Fallback method to extract education using regex patterns"""
        import re
        
        text_lower = resume_text.lower()
        
        # Look for integrated B.Tech + M.Tech programs first
        integrated_btech_mtech = re.search(r'integrated.*b\.?tech.*m\.?tech.*?(?:in|\()(\w+(?:\s+\w+)*)', resume_text, re.IGNORECASE)
        if integrated_btech_mtech:
            field = integrated_btech_mtech.group(1).strip()
            return f"Master of Technology in {field}"
        
        # Look for common degree patterns
        degree_patterns = [
            (r'\b(m\.?tech|m\.?s\.?|master.*technology|master.*science)\b.*?(\w+(?:\s+\w+)*)', 'Master of Technology in {}'),
            (r'\b(b\.?tech|b\.?s\.?|bachelor.*technology|bachelor.*science)\b.*?(\w+(?:\s+\w+)*)', 'Bachelor of Technology in {}'),
            (r'\b(phd|doctorate|doctoral)\b.*?(\w+(?:\s+\w+)*)', 'PhD in {}'),
            (r'\b(mba|master.*business)\b.*?(\w+(?:\s+\w+)*)', 'MBA in {}'),
            (r'\b(b\.?a\.?|bachelor.*arts)\b.*?(\w+(?:\s+\w+)*)', 'Bachelor of Arts in {}')
        ]
        
        for pattern, template in degree_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                degree = match.group(1).strip()
                field = match.group(2).strip() if len(match.groups()) > 1 else ""
                if field:
                    return template.format(field)
                return degree
        
        # Look for other integrated programs
        integrated_patterns = [
            r'dual.*degree.*(\w+(?:\s+\w+)*)',
            r'integrated.*program.*?(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in integrated_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                field = match.group(1).strip()
                return f"Master's in {field}"
        
        return None
    
    @cache_manager.cached(ttl=CACHE_CONFIG['job_descriptions'], key_prefix="job_requirements")
    async def extract_job_requirements(self, job_description: str) -> List[str]:
        """Extract required skills from job description"""
        
        prompt = f"""Analyze the following job description and extract the required skills and qualifications.

Job Description:
{job_description[:4000]}

Return a JSON object with:
{{
    "required_skills": ["list of required technical skills, tools, and qualifications"],
    "preferred_skills": ["list of nice-to-have skills"],
    "keywords": ["important keywords from the job description"]
}}

Return ONLY the JSON object, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert HR assistant that extracts requirements from job descriptions. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            return result.get("required_skills", []) + result.get("preferred_skills", [])
            
        except Exception as e:
            logger.error(f"Failed to extract job requirements: {e}")
            return []
    
    @cache_manager.cached(ttl=CACHE_CONFIG['openai_responses'], key_prefix="match_evaluation")
    async def evaluate_match(
        self,
        resume_text: str,
        resume_skills: Dict[str, Any],
        job_description: str,
        job_title: str
    ) -> Dict[str, Any]:
        """Evaluate how well a resume matches a job description"""
        
        prompt = f"""You are an expert HR recruiter evaluating a candidate's resume against a job posting.

Job Title: {job_title}

Job Description:
{job_description[:3000]}

Candidate's Extracted Information:
- Skills: {', '.join(resume_skills.get('skills', []))}
- Experience: {resume_skills.get('experience_years', 'Not specified')} years
- Education: {resume_skills.get('education', 'Not specified')}
- Previous Roles: {', '.join(resume_skills.get('previous_roles', []))}

Resume Text (for additional context):
{resume_text[:2000]}

Evaluate this candidate and return a JSON object:
{{
    "match_score": <0-100 percentage score>,
    "status": "<'OK to Proceed' if score >= 60, otherwise 'Not OK'>",
    "justification": "<2-3 sentence explanation of the evaluation>",
    "matched_skills": [
        {{"skill": "skill name", "matched": true/false, "relevance_score": 0.0-1.0}}
    ],
    "strengths": ["list of candidate strengths for this role"],
    "gaps": ["list of missing skills or qualifications"]
}}

Be fair but thorough. Consider both hard skills and soft skills.
Return ONLY the JSON object, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert HR recruiter providing fair and thorough candidate evaluations. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            return json.loads(result_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return {
                "match_score": 0,
                "status": "Not OK",
                "justification": "Failed to evaluate resume due to processing error.",
                "matched_skills": [],
                "strengths": [],
                "gaps": ["Evaluation failed"]
            }
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            raise ValueError(f"Failed to evaluate resume: {e}")


_skill_extractor: Optional[SkillExtractor] = None


def get_skill_extractor() -> SkillExtractor:
    global _skill_extractor
    if _skill_extractor is None:
        _skill_extractor = SkillExtractor()
    return _skill_extractor
