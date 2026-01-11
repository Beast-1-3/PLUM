# AI-Powered Appointment Information Extractor
"""
Entity Extractor Module - Step 2: Entity Extraction
Extracts date, time, and department entities from raw text using regex and NLP
"""

import logging
import re
from typing import Dict, Optional
from schemas import ExtractedEntities, EntityExtractionOutput

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracts structured entities from unstructured text"""
    
    def __init__(self):
        """Initialize entity extractor with regex patterns"""
        
        # Department/Service keywords
        self.departments = [
            'dentist', 'dental', 'cardiology', 'cardiologist', 'orthopedic',
            'orthopedics', 'pediatric', 'pediatrics', 'dermatology', 'dermatologist',
            'neurology', 'neurologist', 'ophthalmology', 'eye', 'ent',
            'general', 'surgery', 'physician', 'doctor', 'dr', 'gynecology',
            'psychiatry', 'radiology', 'oncology', 'urology', 'physiotherapy',
            'physio', 'physical therapy', 'rehabilitation', 'rehab'
        ]
        
        # Department normalization mapping (informal → formal)
        self.department_mapping = {
            'dentist': 'Dentistry',
            'dental': 'Dentistry',
            'cardiology': 'Cardiology',
            'cardiologist': 'Cardiology',
            'orthopedic': 'Orthopedics',
            'orthopedics': 'Orthopedics',
            'pediatric': 'Pediatrics',
            'pediatrics': 'Pediatrics',
            'dermatology': 'Dermatology',
            'dermatologist': 'Dermatology',
            'neurology': 'Neurology',
            'neurologist': 'Neurology',
            'ophthalmology': 'Ophthalmology',
            'eye': 'Ophthalmology',
            'ent': 'ENT',
            'general': 'General Medicine',
            'surgery': 'Surgery',
            'physician': 'General Medicine',
            'doctor': 'General Medicine',
            'dr': 'General Medicine',
            'gynecology': 'Gynecology',
            'psychiatry': 'Psychiatry',
            'radiology': 'Radiology',
            'oncology': 'Oncology',
            'urology': 'Urology',
            'physiotherapy': 'Physiotherapy',
            'physio': 'Physiotherapy',
            'physical therapy': 'Physiotherapy',
            'rehabilitation': 'Rehabilitation',
            'rehab': 'Rehabilitation'
        }
        
        # Time patterns
        self.time_patterns = [
            r'\b(\d{1,2})\s*(?::|\.)?(\d{2})?\s*(am|pm|AM|PM)\b',  # 3pm, 3:30pm
            r'\b(\d{1,2})\s*(?::|\.)?(\d{2})\b',  # 15:30, 3:30
            r'\b(noon|midnight|morning|evening|afternoon)\b',  # Named times
        ]
        
        # Date patterns (relative and absolute)
        self.date_patterns = [
            r'\b(today|tomorrow|tonight)\b',
            r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',  # 12/25/2024
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b',  # Jan 15
            r'\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b',  # 15 Jan
            r'\bin\s+(\d{1,2})\s+days?\b',  # in 3 days
        ]
    
    def extract_entities(self, text: str) -> EntityExtractionOutput:
        """
        Extract date, time, and department entities from text
        
        Args:
            text: Raw text to extract entities from
            
        Returns:
            EntityExtractionOutput with extracted entities and confidence
        """
        text_lower = text.lower()
        
        # Extract department
        department = self._extract_department(text_lower)
        
        # Extract time
        time_phrase = self._extract_time(text_lower)
        
        # Extract date
        date_phrase = self._extract_date(text_lower)
        
        # Calculate confidence based on what we found
        found_count = sum([
            department is not None,
            time_phrase is not None,
            date_phrase is not None
        ])
        
        confidence = found_count / 3.0  # 3 required entities
        
        entities = ExtractedEntities(
            date_phrase=date_phrase,
            time_phrase=time_phrase,
            department=department
        )
        
        logger.info(f"Extracted entities: {entities.dict()}, confidence: {confidence:.2f}")
        
        return EntityExtractionOutput(
            entities=entities,
            entities_confidence=round(confidence, 2)
        )
    
    def _extract_department(self, text: str) -> Optional[str]:
        """Extract and normalize department/service from text"""
        for dept in self.departments:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(dept) + r'\w*\b'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted = match.group(0).lower()
                # Normalize to formal department name
                normalized = self.department_mapping.get(extracted, extracted.title())
                logger.info(f"Extracted department: '{extracted}' → Normalized: '{normalized}'")
                return normalized
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """Extract time phrase from text"""
        for pattern in self.time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date phrase from text"""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
