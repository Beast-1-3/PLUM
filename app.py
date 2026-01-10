"""
Main FastAPI Application - AI-Powered Appointment Scheduler
Orchestrates the multi-step AI pipeline for appointment scheduling
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

# Import pipeline modules
from ocr import OCRProcessor
from extractor import EntityExtractor
from normalizer import DateTimeNormalizer
from schemas import (
    TextInput,
    AppointmentResponse,
    FinalOutput,
    FinalAppointment,
    GuardrailOutput,
    OCROutput,
    EntityExtractionOutput,
    NormalizationOutput
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting AI-Powered Appointment Scheduler...")
    logger.info("Initializing pipeline components...")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Initialize FastAPI app
app = FastAPI(
    title="AI-Powered Appointment Scheduler",
    description="Backend service for natural language appointment scheduling using AI pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline components
ocr_processor = OCRProcessor()
entity_extractor = EntityExtractor()
normalizer = DateTimeNormalizer()


def run_guardrail_check(
    normalized_output: NormalizationOutput,
    entities: EntityExtractionOutput
) -> GuardrailOutput:
    """
    Step 4: Guardrail check to detect if clarification is needed
    
    Args:
        normalized_output: Normalized date/time data
        entities: Extracted entities
        
    Returns:
        GuardrailOutput indicating if clarification is needed
    """
    issues = []
    
    # Check for missing entities
    if not entities.entities.department:
        issues.append("Department not specified")
    
    if normalized_output.normalized.date == "UNKNOWN":
        issues.append("Date is ambiguous or not specified")
    
    if normalized_output.normalized.time == "UNKNOWN":
        issues.append("Time is ambiguous or not specified")
    
    # Check if normalized datetime is valid and in future
    if normalized_output.normalized.date != "UNKNOWN" and normalized_output.normalized.time != "UNKNOWN":
        is_valid = normalizer.validate_datetime(
            normalized_output.normalized.date,
            normalized_output.normalized.time
        )
        if not is_valid:
            issues.append("Appointment time is in the past or invalid")
    
    # Return guardrail result
    if issues:
        message = "Clarification needed: " + "; ".join(issues)
        logger.warning(f"Guardrail triggered: {message}")
        return GuardrailOutput(
            status="needs_clarification",
            message=message
        )
    
    return GuardrailOutput(status="ok")


def process_appointment_pipeline(
    raw_text: str,
    ocr_confidence: float = 1.0
) -> AppointmentResponse:
    """
    Run the complete appointment scheduling pipeline
    
    Args:
        raw_text: Input text (from OCR or direct input)
        ocr_confidence: OCR confidence score
        
    Returns:
        Complete AppointmentResponse with all pipeline stages
    """
    logger.info(f"Processing appointment request: '{raw_text}'")
    
    # Step 1: OCR (already done, create output object)
    step1_ocr = OCROutput(raw_text=raw_text, confidence=ocr_confidence)
    
    # Step 2: Entity Extraction
    logger.info("Step 2: Entity Extraction")
    step2_extraction = entity_extractor.extract_entities(raw_text)
    
    # Step 3: Normalization
    logger.info("Step 3: Normalization")
    step3_normalization = normalizer.normalize(step2_extraction.entities)
    
    # Step 4: Guardrail Check
    logger.info("Step 4: Guardrail Check")
    guardrail = run_guardrail_check(
        normalized_output=step3_normalization,
        entities=step2_extraction
    )
    
    # Step 5: Generate Final Output
    logger.info("Step 5: Generating Final Output")
    
    if guardrail.status == "needs_clarification":
        final_output = FinalOutput(
            appointment=None,
            status="needs_clarification",
            message=guardrail.message
        )
    else:
        # Create final appointment
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
    
    # Assemble complete response
    response = AppointmentResponse(
        step1_ocr=step1_ocr,
        step2_extraction=step2_extraction,
        step3_normalization=step3_normalization,
        guardrail=guardrail,
        final=final_output
    )
    
    logger.info(f"Pipeline completed with status: {final_output.status}")
    return response


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AI-Powered Appointment Scheduler",
        "version": "1.0.0",
        "endpoints": ["/schedule/text", "/schedule/image"]
    }


@app.post("/schedule/text", response_model=AppointmentResponse)
async def schedule_from_text(input_data: TextInput):
    """
    Schedule appointment from natural language text
    
    Args:
        input_data: TextInput with appointment request
        
    Returns:
        Complete AppointmentResponse with all pipeline stages
    """
    try:
        logger.info(f"Received text request: '{input_data.text}'")
        
        # Process text input
        ocr_output = ocr_processor.process_text_input(input_data.text)
        
        # Run pipeline
        response = process_appointment_pipeline(
            raw_text=ocr_output.raw_text,
            ocr_confidence=ocr_output.confidence
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Text processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e), detail=f"Processing failed: {str(e)}")


@app.post("/schedule/image", response_model=AppointmentResponse)
async def schedule_from_image(file: UploadFile = File(...)):
    """
    Schedule appointment from image (OCR)
    
    Args:
        file: Uploaded image file
        
    Returns:
        Complete AppointmentResponse with all pipeline stages
    """
    try:
        logger.info(f"Received image upload: {file.filename}")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an image."
            )
        
        # Read image bytes
        image_bytes = await file.read()
        
        # Process OCR
        ocr_output = ocr_processor.extract_text_from_image(image_bytes)
        
        if not ocr_output.raw_text:
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the image"
            )
        
        # Run pipeline
        response = process_appointment_pipeline(
            raw_text=ocr_output.raw_text,
            ocr_confidence=ocr_output.confidence
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e), detail=f"Processing failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check"""
    health_status = {
        "status": "healthy",
        "components": {
            "ocr_processor": "ok",
            "entity_extractor": "ok",
            "normalizer": "ok"
        }
    }
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
