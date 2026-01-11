import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
import dateparser
import re
from schemas import NormalizedData, NormalizationOutput, ExtractedEntities

logger = logging.getLogger(__name__)

class DateTimeNormalizer:
    def __init__(self):
        self.timezone = ZoneInfo("Asia/Kolkata")
        self.now = datetime.now(self.timezone)
        self.dateparser_settings = {
            'TIMEZONE': 'Asia/Kolkata',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': self.now
        }
    
    def normalize(self, entities: ExtractedEntities) -> NormalizationOutput:
        date_str, date_confidence = self._normalize_date(entities.date_phrase)
        time_str, time_confidence = self._normalize_time(entities.time_phrase)
        
        if date_str == "UNKNOWN" and time_str != "UNKNOWN":
            date_str, date_confidence = self._infer_date_from_time(time_str)
        
        normalization_confidence = (date_confidence + time_confidence) / 2.0
        
        return NormalizationOutput(
            normalized=NormalizedData(date=date_str, time=time_str, tz="Asia/Kolkata"),
            normalization_confidence=round(normalization_confidence, 2)
        )
    
    def _preprocess_date_phrase(self, date_phrase: str) -> Tuple[str, int]:
        d = date_phrase.lower().strip()
        if d.startswith("next "):
            return d.replace("next ", "", 1).strip(), 1
        if d.startswith("this "):
            return d.replace("this ", "", 1).strip(), 0
        if d.startswith("last "):
            return d.replace("last ", "", 1).strip(), -1
        return date_phrase, 0
    
    def _infer_date_from_time(self, time_str: str) -> Tuple[str, float]:
        try:
            h, m = map(int, time_str.split(':'))
            t = self.now.replace(hour=h, minute=m, second=0, microsecond=0)
            if t > self.now:
                return self.now.strftime("%Y-%m-%d"), 0.85
            else:
                return (self.now + timedelta(days=1)).strftime("%Y-%m-%d"), 0.85
        except:
            return "UNKNOWN", 0.0
    
    def _normalize_date(self, date_phrase: Optional[str]) -> Tuple[str, float]:
        if not date_phrase:
            return "UNKNOWN", 0.0
        try:
            p, offset = self._preprocess_date_phrase(date_phrase)
            dt = dateparser.parse(p, settings=self.dateparser_settings)
            if dt:
                if offset != 0:
                    dt = dt + timedelta(weeks=offset)
                return dt.strftime("%Y-%m-%d"), 0.9
            return "UNKNOWN", 0.0
        except:
            return "UNKNOWN", 0.0
    
    def _normalize_time(self, time_phrase: Optional[str]) -> Tuple[str, float]:
        if not time_phrase:
            return "UNKNOWN", 0.0
        try:
            p = time_phrase.lower().strip()
            named = {'noon':'12:00', 'midnight':'00:00', 'morning':'09:00', 'afternoon':'14:00', 'evening':'18:00'}
            if p in named:
                return named[p], 0.7
            
            dt = dateparser.parse(f"today at {p}", settings=self.dateparser_settings)
            if dt:
                return dt.strftime("%H:%M"), 0.9
            
            m = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', p)
            if m:
                h = int(m.group(1))
                min = int(m.group(2) or 0)
                mer = m.group(3)
                if mer == 'pm' and h != 12: h += 12
                elif mer == 'am' and h == 12: h = 0
                return f"{h:02d}:{min:02d}", 0.85
            return "UNKNOWN", 0.0
        except:
            return "UNKNOWN", 0.0
    
    def validate_datetime(self, date_str: str, time_str: str) -> bool:
        if date_str == "UNKNOWN" or time_str == "UNKNOWN": return False
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=self.timezone)
            return dt > self.now
        except:
            return False
