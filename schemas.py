"""
Data schemas for the AI-Powered Appointment Scheduler
Defines Pydantic models for request/response validation and structured outputs
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class OCROutput(BaseModel):
    """Step 1: OCR/Text Extraction Output"""
    raw_text: str = Field(..., description="Extracted text from image or direct input")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score")


class ExtractedEntities(BaseModel):
    """Step 2: Entity Extraction Output"""
    date_phrase: Optional[str] = Field(None, description="Extracted date phrase")
    time_phrase: Optional[str] = Field(None, description="Extracted time phrase")
    department: Optional[str] = Field(None, description="Extracted department/service")


class EntityExtractionOutput(BaseModel):
    """Step 2 Complete Output"""
    entities: ExtractedEntities
    entities_confidence: float = Field(..., ge=0.0, le=1.0)


class NormalizedData(BaseModel):
    """Step 3: Normalized appointment data"""
    date: str = Field(..., description="Normalized date in YYYY-MM-DD format")
    time: str = Field(..., description="Normalized time in HH:MM format")
    tz: str = Field(default="Asia/Kolkata", description="Timezone")


class NormalizationOutput(BaseModel):
    """Step 3 Complete Output"""
    normalized: NormalizedData
    normalization_confidence: float = Field(..., ge=0.0, le=1.0)


class GuardrailOutput(BaseModel):
    """Guardrail check output for ambiguous requests"""
    status: Literal["needs_clarification", "ok"]
    message: Optional[str] = None


class FinalAppointment(BaseModel):
    """Final appointment structure"""
    department: str
    date: str
    time: str
    tz: str = "Asia/Kolkata"


class FinalOutput(BaseModel):
    """Final API response"""
    appointment: Optional[FinalAppointment] = None
    status: Literal["ok", "needs_clarification", "error"]
    message: Optional[str] = None


class TextInput(BaseModel):
    """Input for text-based appointment request"""
    text: str = Field(..., description="Natural language appointment request")
    include_pipeline: bool = Field(default=False, description="Include intermediate pipeline outputs")


class AppointmentResponse(BaseModel):
    """Complete response with all pipeline stages"""
    step1_ocr: Optional[OCROutput] = None
    step2_extraction: Optional[EntityExtractionOutput] = None
    step3_normalization: Optional[NormalizationOutput] = None
    guardrail: Optional[GuardrailOutput] = None
    final: FinalOutput
