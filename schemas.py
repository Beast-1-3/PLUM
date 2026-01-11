from pydantic import BaseModel, Field
from typing import Optional, Literal

class OCROutput(BaseModel):
    raw_text: str
    confidence: float

class ExtractedEntities(BaseModel):
    date_phrase: Optional[str] = None
    time_phrase: Optional[str] = None
    department: Optional[str] = None

class EntityExtractionOutput(BaseModel):
    entities: ExtractedEntities
    entities_confidence: float

class NormalizedData(BaseModel):
    date: str
    time: str
    tz: str = "Asia/Kolkata"

class NormalizationOutput(BaseModel):
    normalized: NormalizedData
    normalization_confidence: float

class GuardrailOutput(BaseModel):
    status: Literal["needs_clarification", "ok"]
    message: Optional[str] = None

class FinalAppointment(BaseModel):
    department: str
    date: str
    time: str
    tz: str = "Asia/Kolkata"

class FinalOutput(BaseModel):
    appointment: Optional[FinalAppointment] = None
    status: Literal["ok", "needs_clarification", "error"]
    message: Optional[str] = None

class AppointmentResponse(BaseModel):
    step1_ocr: Optional[OCROutput] = None
    step2_extraction: Optional[EntityExtractionOutput] = None
    step3_normalization: Optional[NormalizationOutput] = None
    guardrail: Optional[GuardrailOutput] = None
    final: FinalOutput
