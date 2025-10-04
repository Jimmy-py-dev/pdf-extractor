import pdfplumber
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
import os
import logging
from typing import List, Dict, Union, Any, Optional
from pathlib import Path
import re
from data_exporter import DataExporter
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PDFExtractor:
    """
    Robust PDF Extractor with support for digital and scanned PDFs.
    
    Attributes:
        tesseract_path (Path): Path to the Tesseract executable.
        poppler_path (Path): Path to the Poppler 'bin' directory.
    """
    def __init__(self, tesseract_path: Optional[str] = None, poppler_path: Optional[str] = None):
        
        # Configure Tesseract
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = Path(tesseract_path)
        else:
            default_path = Path("YOUR OCR PATH")
            if default_path.exists():
                pytesseract.pytesseract.tesseract_cmd = default_path
            else:
                logging.warning("Tesseract executable path not provided and default not found.")

        # Configure Poppler
        if poppler_path:
            self.poppler_path = Path(poppler_path)
        else:
            self.poppler_path = Path("YOUR POPPLER PATH")
            if not self.poppler_path.exists():
                logging.warning("Poppler path not provided and default not found.")

        self.text_processor= TextProcessor()
        self.data_exporter = DataExporter()
        self._extraction_mode = 'unknown'  # Default value

        logging.info("✅ PDFExtractor initialized")
        logging.info("   - Digital PDFs: Full text + table extraction")
        logging.info("   - Scanned PDFs: Text extraction only")
    def get_extraction_mode(self) -> str:
        """Get the extraction mode safely"""
        return getattr(self, '_extraction_mode', 'unknown')

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from a PDF, handling both digital and scanned types.
        
        Args:
            pdf_path: The path to the PDF file.
        
        Returns:
            str: The extracted text from all pages.
        """
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            logging.error(f"❌ File not found: {pdf_path}")
            return ""
            
        try:
            pdf_type = self._detect_pdf_type(pdf_path_obj)
            self._extraction_mode = pdf_path
            logging.info(f"📄 Processing {pdf_type} PDF: {pdf_path_obj.name}")
            
            if pdf_type == 'digital':
                text = self._extract_text_digital(pdf_path_obj)
            else:
                text = self._extract_text_scanned(pdf_path_obj)
            
            logging.info(f"✅ {pdf_type.capitalize()} text extraction completed: {len(text)} characters")
            return text
                
        except Exception as e:
            logging.error(f"❌ Error extracting text from {pdf_path}: {e}")
            return ""

    def extract_tables(self, pdf_path: str) -> List[Any]:
        """
        Extract tables from a PDF.
        
        For digital PDFs, this returns a list of tables.
        For scanned PDFs, this returns an empty list with a warning.
        
        Args:
            pdf_path: The path to the PDF file.
        
        Returns:
            list: List of tables (for digital) or an empty list (for scanned).
        """
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            logging.error(f"❌ File not found: {pdf_path}")
            return []
            
        try:
            pdf_type = self._detect_pdf_type(pdf_path_obj)
            self._extraction_mode = pdf_type
            logging.info(f"📊 Processing tables from {pdf_type} PDF: {pdf_path_obj.name}")
            
            if pdf_type == 'digital':
                tables = self._extract_tables_digital(pdf_path_obj)
                logging.info(f"✅ Digital table extraction: {len(tables)} tables found")
                return tables
            else:
                logging.warning("⚠️ TABLE EXTRACTION WARNING:")
                logging.warning("   - Scanned PDF detected. Table extraction not available.")
                logging.warning("   - Retrun Empty List. Use Text Processor for Further Table Context")

                return []
                
        except Exception as e:
            logging.error(f"❌ Error extracting tables from {pdf_path}: {e}")
            return []

    def _detect_pdf_type(self, pdf_path: Path) -> str:
        """Detect if PDF is digital or scanned by checking the first page for text."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    return 'scanned'
                
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                if text and len(text.strip()) > 50:
                    return 'digital'
                else:
                    return 'scanned'
        except Exception as e:
            logging.warning(f"⚠️ PDF detection warning for {pdf_path.name}: {e}. Assuming scanned.")
            return 'scanned'

    def _extract_text_digital(self, pdf_path: Path) -> str:
        """Extract text from digital PDF using pdfplumber."""
        all_text: List[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    all_text.append(text)
                logging.info(f"   📄 Page {page_num + 1}: {len(text) if text else 0} characters")
        
        return "\n".join(all_text)

    def _extract_text_scanned(self, pdf_path: Path) -> str:
        """Extract text from a scanned PDF using OCR."""
        all_text: List[str] = []
        try:
            images = convert_from_path(pdf_path, dpi=300, poppler_path=self.poppler_path)
            
            for page_num, image in enumerate(images):
                img_cv = np.array(image)
                gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                text = pytesseract.image_to_string(thresh, config='--psm 6')
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                page_text = '\n'.join(lines)
                all_text.append(page_text)
                logging.info(f"   📸 OCR Page {page_num + 1}: {len(page_text)} characters")

            return '\n\n'.join(all_text)
        except Exception as e:
            logging.error(f"❌ OCR failed for {pdf_path.name}: {e}")
            return "OCR Functionaliy Not Available On This Platform"
            
    def _extract_tables_digital(self, pdf_path: Path) -> List[List[List[str]]]:
        """Extract tables from digital PDF using pdfplumber."""
        all_tables: List[List[List[str]]] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    for table_num, table in enumerate(tables):
                        cleaned_table = []
                        for row in table:
                            if row:
                                cleaned_row = [cell.strip() if cell else "" for cell in row]
                                cleaned_table.append(cleaned_row)
                        
                        if cleaned_table:
                            all_tables.append(cleaned_table)
                            logging.info(f"   📊 Page {page_num + 1}, Table {table_num + 1} extracted with {len(cleaned_table)} rows")
        return all_tables
    
class TextProcessor:
    """
    Specific methods for common data extraction with fallback to custom patterns
    """
    def extract_date(self, text: str) -> Optional[str]:
        """Extract date using common date patterns"""
        common_patterns = [
            r'Date\s*[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Date\s*[:]?\s*(\d{1,2}\s+(Jan|Feb|Mar)\s+\d{4})'
        ]
        return self._extract_with_patterns(text, common_patterns)
    
    def extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number using common patterns"""
        common_patterns = [
            r'Invoice\s*No\.?\s*[:]?\s*([A-Z0-9-]+)',
            r'INV[-]?(\d+)',
            r'Invoice[\s\S]{0,50}?([A-Z]{2,4}[-]?\d{4,8})'
        ]
        return self._extract_with_patterns(text, common_patterns)
    
    def extract_vendor_name(self, text: str) -> Optional[str]:
        """Extract vendor/supplier name"""
        common_patterns = [
            r'Vendor\s*[:]?\s*([^\n]{5,50})',
            r'Supplier\s*[:]?\s*([^\n]{5,50})',
            r'Sold\s+To\s*[:]?\s*([^\n]{5,50})'
        ]
        return self._extract_with_patterns(text, common_patterns)
    
    def extract_total_amount(self, text: str) -> Optional[str]:
        """Extract total amount"""
        common_patterns = [
            r'Total[\s\S]{0,30}?([$€£]?\s?\d{1,3}(?:,\d{3})*\.?\d{0,2})',
            r'Grand\s+Total[\s\S]{0,30}?([$€£]?\s?\d{1,3}(?:,\d{3})*\.?\d{0,2})'
        ]
        return self._extract_with_patterns(text, common_patterns)
    
    def extract_with_custom_pattern(self, text: str, pattern: str) -> Optional[str]:
        """Extract using custom regex pattern"""
        return self._extract_with_patterns(text, [pattern])
    
    def _extract_with_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """Internal method to try multiple patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return the first capture group
                return match.group(1).strip() if match.lastindex else match.group(0).strip()
        
        # No pattern matched
        logging.warning(f"No pattern matched for extraction")
        return None

