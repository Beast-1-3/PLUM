import logging
import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

load_dotenv()

from ocr import OCRProcessor
from extractor import EntityExtractor
from normalizer import DateTimeNormalizer
from schemas import (
    AppointmentResponse,
    FinalOutput,
    FinalAppointment,
    GuardrailOutput,
    OCROutput,
    EntityExtractionOutput,
    NormalizationOutput
)
from ai_validator import GeminiValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI-Powered Appointment Scheduler...")
    logger.info("Initializing pipeline components...")
    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title="Appointment Scheduler",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_processor = OCRProcessor()
entity_extractor = EntityExtractor()
normalizer = DateTimeNormalizer()
try:
    ai_validator = GeminiValidator()
except Exception as e:
    logger.warning(f"Failed to initialize validator: {e}")
    ai_validator = None

def run_guardrail_check(normalized_output, entities):
    issues = []
    
    if not entities.entities.department:
        issues.append("Department not specified")
    
    if normalized_output.normalized.date == "UNKNOWN":
        issues.append("Date is ambiguous or not specified")
    
    if normalized_output.normalized.time == "UNKNOWN":
        issues.append("Time is ambiguous or not specified")
    
    if normalized_output.normalized.date != "UNKNOWN" and normalized_output.normalized.time != "UNKNOWN":
        if not normalizer.validate_datetime(normalized_output.normalized.date, normalized_output.normalized.time):
            issues.append("Appointment time is in the past or invalid")
    
    if issues:
        message = "Clarification needed: " + "; ".join(issues)
        logger.warning(f"Guardrail triggered: {message}")
        return GuardrailOutput(status="needs_clarification", message=message)
    
    return GuardrailOutput(status="ok")

def process_appointment_pipeline(raw_text, ocr_confidence=1.0, include_pipeline=True):
    logger.info(f"Processing: '{raw_text}'")
    
    step1_ocr = OCROutput(raw_text=raw_text, confidence=ocr_confidence)
    step2_extraction = entity_extractor.extract_entities(raw_text)
    step3_normalization = normalizer.normalize(step2_extraction.entities)
    
    guardrail = run_guardrail_check(step3_normalization, step2_extraction)
    
    if guardrail.status == "needs_clarification":
        final_output = FinalOutput(
            appointment=None,
            status="needs_clarification",
            message=guardrail.message
        )
    else:
        appointment = FinalAppointment(
            department=step2_extraction.entities.department or "General",
            date=step3_normalization.normalized.date,
            time=step3_normalization.normalized.time,
            tz="Asia/Kolkata"
        )
        final_output = FinalOutput(
            appointment=appointment,
            status="ok",
            message="Appointment scheduled successfully"
        )
    
    response = AppointmentResponse(
        step1_ocr=step1_ocr if include_pipeline else None,
        step2_extraction=step2_extraction if include_pipeline else None,
        step3_normalization=step3_normalization if include_pipeline else None,
        guardrail=guardrail if include_pipeline else None,
        final=final_output
    )
    
    return response

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Appointment Scheduler",
        "version": "1.0.0",
        "endpoints": {
            "schedule": "/schedule",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "ocr_processor": "ok",
            "entity_extractor": "ok",
            "normalizer": "ok"
        }
    }

@app.post("/schedule", response_model=AppointmentResponse)
async def schedule_appointment(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    include_pipeline: bool = Form(True)
):
    try:
        has_text = text is not None and text.strip()
        has_file = file is not None
        
        if not has_text and not has_file:
            raise HTTPException(status_code=400, detail="No input provided")
        
        if has_text and has_file:
            raise HTTPException(status_code=400, detail="Multiple inputs detected")
        
        if has_text:
            ocr_output = ocr_processor.process_text_input(text)
            return process_appointment_pipeline(ocr_output.raw_text, ocr_output.confidence, include_pipeline)
        else:
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Invalid file type")
            
            image_bytes = await file.read()
            ocr_output = ocr_processor.extract_text_from_image(image_bytes)
            
            if not ocr_output.raw_text:
                raise HTTPException(status_code=400, detail="No text extracted")
            
            return process_appointment_pipeline(ocr_output.raw_text, ocr_output.confidence, include_pipeline)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True, log_level="info")
