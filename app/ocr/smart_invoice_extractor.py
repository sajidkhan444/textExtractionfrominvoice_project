"""Smart invoice extractor using EasyOCR."""

import easyocr
import re
import json
import cv2
import numpy as np
# from IPython.display import display, Image as IPImage
from app.core.constants import TABLE_STOP_WORDS, INVOICE_METADATA_INDICATORS
from app.config import OCR_GPU, OCR_LANGUAGES


class SmartInvoiceExtractor:
    def __init__(self):
        """Initialize EasyOCR"""
        print("🔄 Initializing Smart Invoice Extractor...")
        self.reader = easyocr.Reader(OCR_LANGUAGES, gpu=OCR_GPU)
        print("✅ Ready!")

        # Table headers that signal STOP extraction
        self.table_stop_words = TABLE_STOP_WORDS
        self.min_line_length = 2

    def display_invoice(self, image_path):
        """Show the invoice"""
        # Commented out - not needed
        # print("\n📄 Input Invoice:")
        # img = IPImage(filename=image_path)
        # display(img)
        pass

    def is_table_header(self, text):
        """Check if this line indicates start of data table."""
        text_lower = text.lower()
        
        # Check if this is invoice metadata (NOT a table header)
        for indicator in INVOICE_METADATA_INDICATORS:
            if indicator in text_lower:
                return False
        
        # Count matches from table_stop_words
        matches = 0
        matched_words = []
        
        for word in self.table_stop_words:
            word_lower = word.lower()
            if word_lower in text_lower.split():
                matches += 1
                matched_words.append(word_lower)
            elif word_lower in text_lower:
                matches += 1
                matched_words.append(word_lower)
        
        # Only stop if 3 or more table keywords are found
        if matches >= 2:
            print(f"      [DEBUG] Found {matches} table keywords: {matched_words[:3]}...")
            return True
        
        # Check for pipe-separated table format
        if '|' in text and len(text.split('|')) >= 4:
            return True
        
        # Check for multiple numeric columns
        numeric_columns = len(re.findall(r'\d+\.?\d*', text))
        if numeric_columns >= 4 and len(text.split()) >= 5:
            if any(word in text_lower for word in ["price", "qty", "total", "amount", "discount"]):
                return True
        
        return False

    def sort_blocks_by_reading_order(self, blocks):
        """Sort blocks by reading order (top to bottom, left to right)"""
        if not blocks:
            return []
        
        blocks.sort(key=lambda x: x["center_y"])
        
        rows = []
        current_row = []
        current_y = blocks[0]["center_y"] if blocks else 0
        y_threshold = 30
        
        for block in blocks:
            if abs(block["center_y"] - current_y) <= y_threshold:
                current_row.append(block)
            else:
                if current_row:
                    current_row.sort(key=lambda x: x["center_x"])
                    rows.append(current_row)
                current_row = [block]
                current_y = block["center_y"]
        
        if current_row:
            current_row.sort(key=lambda x: x["center_x"])
            rows.append(current_row)
        
        return rows

    def merge_lines(self, image_path):
        """Main merging function with proper reading order"""
        print("\n🔍 Extracting text lines with enhanced merging...")

        image = cv2.imread(image_path)
        if image is None:
            print("❌ Could not read image")
            return []

        result = self.reader.readtext(image, paragraph=False)
        
        blocks = []
        for detection in result:
            bbox = detection[0]
            text = detection[1]
            
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            x_center = sum(x_coords) / len(x_coords)
            y_center = sum(y_coords) / len(y_coords)
            
            blocks.append({
                "text": text,
                "center_y": y_center,
                "center_x": x_center,
                "bbox": bbox
            })
        
        blocks.sort(key=lambda x: (x["center_y"], x["center_x"]))
        line_groups = self.sort_blocks_by_reading_order(blocks)
        print(f"✅ Found {len(line_groups)} line groups")
        
        final_lines = []
        for line_blocks in line_groups:
            line_blocks.sort(key=lambda x: x["center_x"])
            line_text = " ".join([block["text"] for block in line_blocks])
            line_text = re.sub(r'\s+', ' ', line_text.strip())
            
            if line_text:
                final_lines.append({
                    "text": line_text,
                    "y_position": line_blocks[0]["center_y"]
                })
        
        return final_lines

    def clean_line(self, text):
        """Clean up the line text"""
        text = re.sub(r'\s+', ' ', text.strip())
        text = text.replace('|', 'I')
        text = text.replace('O', '0') if re.match(r'^[\d\s]+$', text) else text
        text = text.replace('JINV', 'INV')
        text = text.replace('linv', 'INV')
        text = text.replace('_', '')
        text = text.replace('+((=', '')
        text = text.replace('ROSTED', '')
        text = re.sub(r'[=\(\)\+]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def process_invoice(self, image_path):
        """Main processing function"""
        print("\n" + "="*60)
        print("🚀 SMART INVOICE EXTRACTOR (Enhanced Alignment)")
        print("="*60)

        # self.display_invoice(image_path)
        lines = self.merge_lines(image_path)

        if not lines:
            print("❌ No lines found!")
            return None

        json_data = {}
        line_counter = 1
        stopped_at_table = False

        print("\n📋 Processing lines...")
        print("-" * 60)

        for line in lines:
            text = line['text']

            if not text or text.isspace() or len(text) < self.min_line_length:
                line_counter += 1
                continue

            if self.is_table_header(text):
                print(f"\n⛔ Data table detected at line {line_counter}: '{text[:80]}...'")
                print("   Stopping extraction (table data excluded)")
                stopped_at_table = True
                break

            clean_text = self.clean_line(text)

            if clean_text:
                key = f"line_{line_counter:02d}"
                json_data[key] = clean_text
                print(f"   ✅ Line {line_counter:02d}: {clean_text[:100]}{'...' if len(clean_text) > 100 else ''}")
                line_counter += 1
            else:
                line_counter += 1

        if not stopped_at_table:
            print(f"\n✅ Extracted {len(json_data)} lines (no table detected)")
        else:
            print(f"\n✅ Extracted {len(json_data)} lines (stopped at table)")
        
        return json_data

    def print_pretty_json(self, data):
        """Print JSON in a clean format"""
        print("\n" + "="*60)
        print("📊 FINAL JSON OUTPUT")
        print("="*60)
        print(json.dumps(data, indent=2, ensure_ascii=False))