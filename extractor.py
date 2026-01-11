import logging
import re
from typing import Dict, Optional
from schemas import ExtractedEntities, EntityExtractionOutput

logger = logging.getLogger(__name__)

class EntityExtractor:
    def __init__(self):
        self.departments = [
            'dentist', 'dental', 'cardiology', 'cardiologist', 'orthopedic',
            'orthopedics', 'pediatric', 'pediatrics', 'dermatology', 'dermatologist',
            'neurology', 'neurologist', 'ophthalmology', 'eye', 'ent',
            'general', 'surgery', 'physician', 'doctor', 'dr', 'gynecology',
            'psychiatry', 'radiology', 'oncology', 'urology', 'physiotherapy',
            'physio', 'physical therapy', 'rehabilitation', 'rehab'
        ]
        
        self.department_mapping = {
            'dentist': 'Dentistry', 'dental': 'Dentistry', 'cardiology': 'Cardiology',
            'cardiologist': 'Cardiology', 'orthopedic': 'Orthopedics', 'orthopedics': 'Orthopedics',
            'pediatric': 'Pediatrics', 'pediatrics': 'Pediatrics', 'dermatology': 'Dermatology',
            'dermatologist': 'Dermatology', 'neurology': 'Neurology', 'neurologist': 'Neurology',
            'ophthalmology': 'Ophthalmology', 'eye': 'Ophthalmology', 'ent': 'ENT',
            'general': 'General Medicine', 'surgery': 'Surgery', 'physician': 'General Medicine',
            'doctor': 'General Medicine', 'dr': 'General Medicine', 'gynecology': 'Gynecology',
            'psychiatry': 'Psychiatry', 'radiology': 'Radiology', 'oncology': 'Oncology',
            'urology': 'Urology', 'physiotherapy': 'Physiotherapy', 'physio': 'Physiotherapy',
            'physical therapy': 'Physiotherapy', 'rehabilitation': 'Rehabilitation', 'rehab': 'Rehabilitation'
        }
        
        self.time_patterns = [
            r'\b(\d{1,2})\s*(?::|\.)?(\d{2})?\s*(am|pm|AM|PM)\b',
            r'\b(\d{1,2})\s*(?::|\.)?(\d{2})\b',
            r'\b(noon|midnight|morning|evening|afternoon)\b',
        ]
        
        self.date_patterns = [
            r'\b(today|tomorrow|tonight)\b',
            r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b',
            r'\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b',
            r'\bin\s+(\d{1,2})\s+days?\b',
        ]
    
    def extract_entities(self, text: str) -> EntityExtractionOutput:
        text_lower = text.lower()
        department = self._extract_department(text_lower)
        time_phrase = self._extract_time(text_lower)
        date_phrase = self._extract_date(text_lower)
        
        found_count = sum([department is not None, time_phrase is not None, date_phrase is not None])
        confidence = found_count / 3.0
        
        entities = ExtractedEntities(
            date_phrase=date_phrase,
            time_phrase=time_phrase,
            department=department
        )
        
        logger.info(f"Extracted: {entities.dict()} ({confidence:.2f})")
        
        return EntityExtractionOutput(
            entities=entities,
            entities_confidence=round(confidence, 2)
        )
    
    def _extract_department(self, text: str) -> Optional[str]:
        for dept in self.departments:
            pattern = r'\b' + re.escape(dept) + r'\w*\b'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted = match.group(0).lower()
                normalized = self.department_mapping.get(extracted, extracted.title())
                return normalized
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        for pattern in self.time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
