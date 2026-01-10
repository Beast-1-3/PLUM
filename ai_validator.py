"""
AI Validator Module - Step 3: Gemini AI Validation
Uses Google Gemini API to validate extracted entities, detect ambiguity, and provide confidence scoring
"""

import logging
import os
import google.generativeai as genai
from typing import Dict
from schemas import ExtractedEntities, AIValidationOutput

logger = logging.getLogger(__name__)


class GeminiValidator:
    """Uses Gemini AI to validate and enhance entity extraction"""
    
    def __init__(self):
        """Initialize Gemini API client"""
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Please set it with your Google Gemini API key."
            )
        
        genai.configure(api_key=api_key)
        # Try the latest model, fallback to 1.5-flash if needed
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        except:
            self.model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        logger.info("Gemini AI validator initialized successfully")
    
    def validate_entities(
        self, 
        raw_text: str, 
        entities: ExtractedEntities
    ) -> AIValidationOutput:
        """
        Use Gemini to validate extracted entities and detect ambiguity
        
        Args:
            raw_text: Original text input
            entities: Extracted entities to validate
            
        Returns:
            AIValidationOutput with validation status and notes
        """
        try:
            prompt = self._build_validation_prompt(raw_text, entities)
            
            logger.info("Sending validation request to Gemini AI...")
            response = self.model.generate_content(prompt)
            
            # Parse Gemini response
            validation_result = self._parse_gemini_response(response.text)
            
            logger.info(f"Gemini validation result: {validation_result}")
            
            return AIValidationOutput(ai_validation=validation_result)
            
        except Exception as e:
            logger.error(f"Gemini validation failed: {str(e)}")
            # Fallback validation
            return AIValidationOutput(
                ai_validation={
                    "status": "error",
                    "notes": f"AI validation unavailable: {str(e)}",
                    "fallback": True
                }
            )
    
    def _build_validation_prompt(
        self, 
        raw_text: str, 
        entities: ExtractedEntities
    ) -> str:
        """Build prompt for Gemini validation"""
        prompt = f"""You are an AI assistant validating appointment scheduling data.

Original text: "{raw_text}"

Extracted entities:
- Date phrase: {entities.date_phrase or 'NOT FOUND'}
- Time phrase: {entities.time_phrase or 'NOT FOUND'}
- Department: {entities.department or 'NOT FOUND'}

Task: Validate if the extracted entities are correct and unambiguous.

Respond in this exact format:
STATUS: [valid/invalid/ambiguous]
CONFIDENCE: [0.0-1.0]
NOTES: [Brief explanation]
SUGGESTIONS: [Any corrections needed]

Consider:
1. Are all three entities present?
2. Is the date/time clear and unambiguous?
3. Is the department a valid medical department?
4. Does the extraction make sense given the original text?
5. Are there any ambiguities that need clarification?
"""
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse structured response from Gemini"""
        result = {
            "status": "valid",
            "confidence": 0.8,
            "notes": "AI validation completed",
            "suggestions": []
        }
        
        try:
            lines = response_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('STATUS:'):
                    status_text = line.split(':', 1)[1].strip().lower()
                    result["status"] = status_text
                
                elif line.startswith('CONFIDENCE:'):
                    try:
                        conf = float(line.split(':', 1)[1].strip())
                        result["confidence"] = round(conf, 2)
                    except ValueError:
                        pass
                
                elif line.startswith('NOTES:'):
                    result["notes"] = line.split(':', 1)[1].strip()
                
                elif line.startswith('SUGGESTIONS:'):
                    suggestions = line.split(':', 1)[1].strip()
                    if suggestions and suggestions.lower() != 'none':
                        result["suggestions"] = [suggestions]
        
        except Exception as e:
            logger.warning(f"Failed to parse Gemini response: {e}")
        
        return result
    
    def calculate_confidence_score(
        self,
        ocr_confidence: float,
        entities_confidence: float,
        ai_validation: Dict
    ) -> float:
        """
        Calculate overall confidence score combining all pipeline stages
        
        Args:
            ocr_confidence: OCR confidence (0-1)
            entities_confidence: Entity extraction confidence (0-1)
            ai_validation: AI validation result
            
        Returns:
            Overall confidence score (0-1)
        """
        ai_confidence = ai_validation.get("confidence", 0.5)
        
        # Penalize if AI says invalid or ambiguous
        status = ai_validation.get("status", "valid").lower()
        if status == "invalid":
            ai_confidence *= 0.3
        elif status == "ambiguous":
            ai_confidence *= 0.6
        
        # Weighted average: OCR=0.2, Entities=0.4, AI=0.4
        overall_confidence = (
            ocr_confidence * 0.2 +
            entities_confidence * 0.4 +
            ai_confidence * 0.4
        )
        
        return round(overall_confidence, 2)
