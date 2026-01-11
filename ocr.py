import logging
from PIL import Image
import pytesseract
from io import BytesIO
from schemas import OCROutput

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        self.min_confidence = 0.3
    
    def extract_text_from_image(self, image_bytes: bytes) -> OCROutput:
        try:
            image = Image.open(BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            extracted_text = pytesseract.image_to_string(image)
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            confidences = [
                int(conf) for conf in ocr_data['conf'] 
                if conf != '-1' and str(conf).strip() != ''
            ]
            
            if confidences:
                avg_confidence = sum(confidences) / len(confidences) / 100.0
            else:
                avg_confidence = 0.5
            
            extracted_text = extracted_text.strip()
            
            if not extracted_text:
                logger.warning("No text extracted from image")
                return OCROutput(raw_text="", confidence=0.0)
            
            logger.info(f"OCR extracted: '{extracted_text}' ({avg_confidence:.2f})")
            
            return OCROutput(
                raw_text=extracted_text,
                confidence=round(avg_confidence, 2)
            )
            
        except Exception as e:
            logger.exception(f"OCR failed: {e}")
            raise ValueError(f"Failed to process image: {e}")
    
    def process_text_input(self, text: str) -> OCROutput:
        text = text.strip()
        if not text:
            return OCROutput(raw_text="", confidence=0.0)
        
        return OCROutput(raw_text=text, confidence=1.0)
