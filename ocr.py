"""
OCR Module - Step 1: Text Extraction
Handles image processing and text extraction using pytesseract
"""

import logging
from PIL import Image
import pytesseract
from io import BytesIO
from schemas import OCROutput

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Handles OCR processing for image-based appointment requests"""
    
    def __init__(self):
        """Initialize OCR processor"""
        self.min_confidence = 0.3  # Minimum acceptable confidence
    
    def extract_text_from_image(self, image_bytes: bytes) -> OCROutput:
        """
        Extract text from image using pytesseract
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            OCROutput with extracted text and confidence score
        """
        try:
            # Open image from bytes
            image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using pytesseract
            extracted_text = pytesseract.image_to_string(image)
            
            # Get detailed OCR data for confidence calculation
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [
                int(conf) for conf in ocr_data['conf'] 
                if conf != '-1' and str(conf).strip() != ''
            ]
            
            if confidences:
                avg_confidence = sum(confidences) / len(confidences) / 100.0
            else:
                avg_confidence = 0.5  # Default if no confidence data
            
            extracted_text = extracted_text.strip()
            
            if not extracted_text:
                logger.warning("No text extracted from image")
                return OCROutput(raw_text="", confidence=0.0)
            
            logger.info(f"OCR extracted text: '{extracted_text}' with confidence: {avg_confidence:.2f}")
            
            return OCROutput(
                raw_text=extracted_text,
                confidence=round(avg_confidence, 2)
            )
            
        except Exception as e:
            logger.exception(f"OCR processing failed: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")
    
    def process_text_input(self, text: str) -> OCROutput:
        """
        Process direct text input (no OCR needed)
        
        Args:
            text: Direct text input
            
        Returns:
            OCROutput with text and perfect confidence
        """
        text = text.strip()
        
        if not text:
            return OCROutput(raw_text="", confidence=0.0)
        
        logger.info(f"Processing direct text input: '{text}'")
        
        return OCROutput(
            raw_text=text,
            confidence=1.0  # Perfect confidence for direct text
        )
