"""
Normalizer Module - Step 4: Date/Time Normalization
Converts extracted date and time phrases into standardized formats
Uses dateparser and timezone handling for Asia/Kolkata
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
import dateparser
import re
from schemas import NormalizedData, NormalizationOutput, ExtractedEntities

logger = logging.getLogger(__name__)


class DateTimeNormalizer:
    """Normalizes date and time phrases to standard formats"""
    
    def __init__(self):
        """Initialize normalizer with Asia/Kolkata timezone"""
        self.timezone = ZoneInfo("Asia/Kolkata")
        self.now = datetime.now(self.timezone)
        
        # Dateparser settings
        self.dateparser_settings = {
            'TIMEZONE': 'Asia/Kolkata',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': self.now
        }
    
    def normalize(self, entities: ExtractedEntities) -> NormalizationOutput:
        """
        Normalize extracted date and time entities
        
        Args:
            entities: Extracted entities with date/time phrases
            
        Returns:
            NormalizationOutput with normalized date/time and confidence
        """
        date_str, date_confidence = self._normalize_date(entities.date_phrase)
        time_str, time_confidence = self._normalize_time(entities.time_phrase)
        
        # Smart date inference: If no date provided but time is available
        if date_str == "UNKNOWN" and time_str != "UNKNOWN":
            date_str, date_confidence = self._infer_date_from_time(time_str)
            logger.info(f"Smart date inference applied: {date_str}")
        
        # Overall normalization confidence
        normalization_confidence = (date_confidence + time_confidence) / 2.0
        
        normalized_data = NormalizedData(
            date=date_str,
            time=time_str,
            tz="Asia/Kolkata"
        )
        
        logger.info(
            f"Normalized to: {date_str} {time_str} "
            f"(confidence: {normalization_confidence:.2f})"
        )
        
        return NormalizationOutput(
            normalized=normalized_data,
            normalization_confidence=round(normalization_confidence, 2)
        )
    
    def _preprocess_date_phrase(self, date_phrase: str) -> Tuple[str, int]:
        """
        Preprocess date phrase to extract modifiers and calculate offsets
        
        Args:
            date_phrase: Original date phrase (e.g., "next friday")
            
        Returns:
            Tuple of (cleaned_phrase, week_offset)
            - cleaned_phrase: phrase without modifier (e.g., "friday")
            - week_offset: number of weeks to add (0, 1, or -1)
        """
        date_phrase_lower = date_phrase.lower().strip()
        
        # Check for "next" modifier (add 1 week)
        if date_phrase_lower.startswith("next "):
            cleaned = date_phrase_lower.replace("next ", "", 1).strip()
            logger.info(f"Detected 'next' modifier: '{date_phrase}' -> '{cleaned}' + 1 week")
            return cleaned, 1
        
        # Check for "this" modifier (current week, no offset)
        if date_phrase_lower.startswith("this "):
            cleaned = date_phrase_lower.replace("this ", "", 1).strip()
            logger.info(f"Detected 'this' modifier: '{date_phrase}' -> '{cleaned}' + 0 weeks")
            return cleaned, 0
        
        # Check for "last" modifier (subtract 1 week)
        if date_phrase_lower.startswith("last "):
            cleaned = date_phrase_lower.replace("last ", "", 1).strip()
            logger.info(f"Detected 'last' modifier: '{date_phrase}' -> '{cleaned}' - 1 week")
            return cleaned, -1
        
        # No modifier detected
        return date_phrase, 0
    
    def _infer_date_from_time(self, time_str: str) -> Tuple[str, float]:
        """
        Infer date from time when no date is specified
        
        Logic:
        - If appointment time is in the future today → use today
        - If appointment time has passed today → use tomorrow
        
        Args:
            time_str: Normalized time in HH:MM format
            
        Returns:
            Tuple of (inferred_date_string, confidence)
        """
        try:
            # Parse the appointment time
            hour, minute = map(int, time_str.split(':'))
            
            # Create datetime for today at the appointment time
            today_appointment = self.now.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            
            # Check if appointment time is in the future
            if today_appointment > self.now:
                # Time is still ahead today, use today
                date_str = self.now.strftime("%Y-%m-%d")
                logger.info(
                    f"Time {time_str} is in the future today "
                    f"(current: {self.now.strftime('%H:%M')}), using today's date"
                )
                return date_str, 0.85
            else:
                # Time has passed today, use tomorrow
                tomorrow = self.now + timedelta(days=1)
                date_str = tomorrow.strftime("%Y-%m-%d")
                logger.info(
                    f"Time {time_str} has passed today "
                    f"(current: {self.now.strftime('%H:%M')}), using tomorrow's date"
                )
                return date_str, 0.85
                
        except Exception as e:
            logger.error(f"Date inference error: {e}")
            return "UNKNOWN", 0.0
    
    def _normalize_date(self, date_phrase: Optional[str]) -> Tuple[str, float]:
        """
        Normalize date phrase to YYYY-MM-DD format
        
        Returns:
            Tuple of (normalized_date_string, confidence)
        """
        if not date_phrase:
            logger.warning("No date phrase provided")
            return "UNKNOWN", 0.0
        
        try:
            # Preprocess to handle "next", "this", "last" modifiers
            cleaned_phrase, week_offset = self._preprocess_date_phrase(date_phrase)
            
            # Use dateparser for natural language date parsing
            parsed_date = dateparser.parse(
                cleaned_phrase,
                settings=self.dateparser_settings
            )
            
            if parsed_date:
                # Apply week offset if modifier was detected
                if week_offset != 0:
                    parsed_date = parsed_date + timedelta(weeks=week_offset)
                    logger.info(f"Applied offset of {week_offset} week(s) to date")
                
                date_str = parsed_date.strftime("%Y-%m-%d")
                confidence = 0.9
                logger.info(f"Date '{date_phrase}' normalized to {date_str}")
                return date_str, confidence
            else:
                logger.warning(f"Could not parse date: {date_phrase}")
                return "UNKNOWN", 0.0
                
        except Exception as e:
            logger.error(f"Date normalization error: {e}")
            return "UNKNOWN", 0.0
    
    def _normalize_time(self, time_phrase: Optional[str]) -> Tuple[str, float]:
        """
        Normalize time phrase to HH:MM format (24-hour)
        
        Returns:
            Tuple of (normalized_time_string, confidence)
        """
        if not time_phrase:
            logger.warning("No time phrase provided")
            return "UNKNOWN", 0.0
        
        try:
            time_phrase = time_phrase.lower().strip()
            
            # Check for named times
            named_times = {
                'noon': '12:00',
                'midnight': '00:00',
                'morning': '09:00',
                'afternoon': '14:00',
                'evening': '18:00',
            }
            
            if time_phrase in named_times:
                return named_times[time_phrase], 0.7
            
            # Try parsing with dateparser
            parsed_time = dateparser.parse(
                f"today at {time_phrase}",
                settings=self.dateparser_settings
            )
            
            if parsed_time:
                time_str = parsed_time.strftime("%H:%M")
                confidence = 0.9
                logger.info(f"Time '{time_phrase}' normalized to {time_str}")
                return time_str, confidence
            
            # Manual parsing for common formats
            # Format: 3pm, 3:30pm, 15:30
            time_match = re.match(
                r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
                time_phrase
            )
            
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2) or 0)
                meridiem = time_match.group(3)
                
                # Convert to 24-hour format
                if meridiem == 'pm' and hours != 12:
                    hours += 12
                elif meridiem == 'am' and hours == 12:
                    hours = 0
                
                time_str = f"{hours:02d}:{minutes:02d}"
                logger.info(f"Time '{time_phrase}' manually parsed to {time_str}")
                return time_str, 0.85
            
            logger.warning(f"Could not parse time: {time_phrase}")
            return "UNKNOWN", 0.0
            
        except Exception as e:
            logger.error(f"Time normalization error: {e}")
            return "UNKNOWN", 0.0
    
    def validate_datetime(self, date_str: str, time_str: str) -> bool:
        """
        Validate that the normalized date/time is in the future
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format
            
        Returns:
            True if valid and in future, False otherwise
        """
        if date_str == "UNKNOWN" or time_str == "UNKNOWN":
            return False
        
        try:
            # Combine date and time
            dt_str = f"{date_str} {time_str}"
            appointment_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            appointment_dt = appointment_dt.replace(tzinfo=self.timezone)
            
            # Check if in future
            if appointment_dt <= self.now:
                logger.warning(
                    f"Appointment time {appointment_dt} is in the past"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"DateTime validation error: {e}")
            return False
