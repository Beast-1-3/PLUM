import logging
import os
import google.generativeai as genai
from typing import List, Dict, Optional, Any
from schemas import ExtractedEntities

logger = logging.getLogger(__name__)

class GeminiValidator:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        genai.configure(api_key=api_key)
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        except:
            self.model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
    
    def validate_entities(self, raw_text: str, entities: ExtractedEntities) -> Dict[str, Any]:
        try:
            prompt = self._build_validation_prompt(raw_text, entities)
            response = self.model.generate_content(prompt)
            validation_result = self._parse_gemini_response(response.text)
            return {"ai_validation": validation_result}
        except Exception as e:
            logger.error(f"AI validation failed: {e}")
            return {
                "ai_validation": {
                    "status": "error",
                    "notes": str(e),
                    "fallback": True
                }
            }
    
    def _build_validation_prompt(self, raw_text: str, entities: ExtractedEntities) -> str:
        return f"""You are validating appointment data.
Original text: "{raw_text}"
Extracted entities:
- Date phrase: {entities.date_phrase or 'NOT FOUND'}
- Time phrase: {entities.time_phrase or 'NOT FOUND'}
- Department: {entities.department or 'NOT FOUND'}

Respond in this format:
STATUS: [valid/invalid/ambiguous]
CONFIDENCE: [0.0-1.0]
NOTES: [reasoning]
SUGGESTIONS: [corrections]
"""
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        result = {"status": "valid", "confidence": 0.8, "notes": "", "suggestions": []}
        try:
            lines = response_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('STATUS:'):
                    result["status"] = line.split(':', 1)[1].strip().lower()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        result["confidence"] = float(line.split(':', 1)[1].strip())
                    except:
                        pass
                elif line.startswith('NOTES:'):
                    result["notes"] = line.split(':', 1)[1].strip()
                elif line.startswith('SUGGESTIONS:'):
                    s = line.split(':', 1)[1].strip()
                    if s and s.lower() != 'none':
                        result["suggestions"] = [s]
        except Exception as e:
            logger.warning(f"Parse error: {e}")
        return result

    def calculate_confidence_score(self, ocr_confidence, entities_confidence, ai_validation):
        ai_confidence = ai_validation.get("confidence", 0.5)
        status = ai_validation.get("status", "valid").lower()
        if status == "invalid":
            ai_confidence *= 0.3
        elif status == "ambiguous":
            ai_confidence *= 0.6
        
        score = (ocr_confidence * 0.2 + entities_confidence * 0.4 + ai_confidence * 0.4)
        return round(score, 2)
