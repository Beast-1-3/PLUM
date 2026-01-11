# AI-Powered Appointment Scheduler Assistant

## 🎯 Project Overview

An intelligent backend service that converts natural language or image-based appointment requests into structured scheduling JSON using a sophisticated multi-step AI pipeline.


**Tech Stack**: Python, FastAPI, Google Gemini AI, pytesseract  


## 🚀 Live Deployment

The service is live at: [https://ai-appointment-scheduler-ufc4.onrender.com](https://ai-appointment-scheduler-ufc4.onrender.com)

---

## 🏗️ Architecture

### Multi-Step AI Pipeline

```
Input (Text/Image)
    ↓
1. OCR / Text Extraction
    ↓
2. Entity Extraction (date, time, department)
    ↓
3. AI Validation (Gemini)
    ↓
4. Normalization (YYYY-MM-DD, HH:MM)
    ↓
5. Confidence Scoring
    ↓
6. Guardrail Check
    ↓
7. Final Structured JSON
```

### Component Breakdown

| Module | Responsibility |
|--------|----------------|
| `app.py` | FastAPI application, orchestrates pipeline |
| `ocr.py` | Image text extraction using pytesseract |
| `extractor.py` | Regex-based entity extraction |
| `ai_validator.py` | Gemini AI validation & confidence scoring |
| `normalizer.py` | Date/time normalization with dateparser |
| `schemas.py` | Pydantic models for type safety |

---

##  Quick Start

### Prerequisites

1. **Python 3.10+**
2. **Tesseract OCR** installed on your system:
   ```bash
   # macOS
   brew install tesseract
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **Google Gemini API Key**  
   Get it from: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

### Installation

```bash
# 1. Navigate to project directory
cd ai-appointment-scheduler

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run the application
python app.py
```

The server will start at `http://localhost:8000`

---

## 📡 API Endpoints

### 1. Health Check
```bash
GET /
GET /health
```

### 2. Schedule 
```bash
POST /schedule
Content-Type: application/json

{
  "text": "Book dentist next Friday at 3pm"
}
```
```bash
POST /schedule
Content-Type: multipart/form-data

file: <image_file>
```

---

## 🧪 Testing Guide

### Using cURL

#### Text Input
```bash
# Local
curl -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=Book dentist next Friday at 3pm"

# Live
curl -X POST https://ai-appointment-scheduler-ufc4.onrender.com/schedule \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=Book dentist next Friday at 3pm"
```

#### Image Input
```bash
# Local
curl -X POST http://localhost:8000/schedule \
  -F "file=@appointment.png"

# Live
curl -X POST https://ai-appointment-scheduler-ufc4.onrender.com/schedule \
  -F "file=@appointment.png"
```

### Using Postman

1. Import the API endpoints
2. **Text Endpoint**:
   - Method: POST
   - URL: `http://localhost:8000/schedule`
   - Body (JSON):
     ```json
     {
       "text": "Cardiology appointment tomorrow at 10:30am"
     }
     ```

3. **Image Endpoint**:
   - Method: POST
   - URL: `http://localhost:8000/schedule`
   - Body: form-data
   - Key: `file` (type: File)
   - Value: Select image file

### Sample Test Cases

```json
// Test 1: Complete information
{
  "text": "Book dentist appointment next Friday at 3pm"
}

// Test 2: Ambiguous time
{
  "text": "Schedule cardiology sometime tomorrow"
}

// Test 3: Missing department
{
  "text": "Appointment on January 15th at 2:30pm"
}

// Test 4: Past date (should fail guardrail)
{
  "text": "Book dentist yesterday at 3pm"
}
```

---

## 📋 Response Format

### Success Response

```json
{
  "step1_ocr": {
    "raw_text": "Book dentist next Friday at 3pm",
    "confidence": 1.0
  },
  "step2_extraction": {
    "entities": {
      "date_phrase": "next Friday",
      "time_phrase": "3pm",
      "department": "dentist"
    },
    "entities_confidence": 1.0
  },
  "step3_validation": {
    "ai_validation": {
      "status": "valid",
      "confidence": 0.95,
      "notes": "All entities clear and unambiguous",
      "suggestions": []
    }
  },
  "step4_normalization": {
    "normalized": {
      "date": "2026-01-17",
      "time": "15:00",
      "tz": "Asia/Kolkata"
    },
    "normalization_confidence": 0.9
  },
  "guardrail": {
    "status": "ok"
  },
  "final": {
    "appointment": {
      "department": "dentist",
      "date": "2026-01-17",
      "time": "15:00",
      "tz": "Asia/Kolkata"
    },
    "status": "ok",
    "message": "Appointment scheduled successfully"
  }
}
```

### Clarification Needed Response

```json
{
  "guardrail": {
    "status": "needs_clarification",
    "message": "Clarification needed: Time is ambiguous or not specified"
  },
  "final": {
    "appointment": null,
    "status": "needs_clarification",
    "message": "Clarification needed: Time is ambiguous or not specified"
  }
}
```

---

## Gemini AI Integration

### Purpose

Gemini AI is used as a **validation and reasoning layer**, NOT as a direct replacement for logic.

### Specific Use Cases

1. **Entity Validation**: Verifies if extracted entities are correct
2. **Ambiguity Detection**: Identifies unclear date/time references
3. **Confidence Scoring**: Provides AI-driven confidence assessment
4. **Cross-Checking**: Validates normalization against original text

### Implementation Strategy

```python
# Gemini receives structured prompts with:
# 1. Original text
# 2. Extracted entities
# 3. Specific validation questions

# Returns structured response:
# - STATUS: valid/invalid/ambiguous
# - CONFIDENCE: 0.0-1.0
# - NOTES: Explanation
# - SUGGESTIONS: Corrections needed
```


---

##  Guardrail Strategy

### Purpose
Prevent incorrect appointments by catching issues before final scheduling.

### Checks Performed

1. **Entity Completeness**: All required fields present (date, time, department)
2. **Confidence Threshold**: Overall confidence ≥ 0.5
3. **DateTime Validity**: Date/time is in the future
4. **Normalization Success**: Date ≠ "UNKNOWN", Time ≠ "UNKNOWN"

### Decision Logic

```python
if any([
    missing_entity,
    low_confidence,
    past_datetime,
    failed_normalization
]):
    return "needs_clarification"
else:
    return "ok"
```

---

## 📁 Project Structure

```
ai-appointment-scheduler/
├── app.py                 # Main FastAPI application
├── ocr.py                 # OCR text extraction
├── extractor.py           # Entity extraction
├── ai_validator.py        # Gemini AI validation
├── normalizer.py          # Date/time normalization
├── schemas.py             # Pydantic models
├── requirements.txt       # Dependencies
├── .env.example           # Environment template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── tests/                # Test files
│   ├── sample_text.json
    └── sample_image.png

```

---

