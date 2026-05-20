# app/parser/qwen_document_parser.py

import re
import json
from app.core.documents_prompts import get_document_extraction_prompt


class QwenDocumentParser:
    """Document parser that reuses the existing Qwen model from dependencies"""
    
    def __init__(self, model, tokenizer):
        """
        Initialize document parser with existing Qwen model and tokenizer.
        
        Args:
            model: Existing Qwen model from dependencies
            tokenizer: Existing Qwen tokenizer from dependencies
        """
        self.model = model
        self.tokenizer = tokenizer

    def extract_fields_with_qwen(self, ocr_text):
        """Extract fields from OCR text using document-specific prompt"""
        
        if self.model is None or self.tokenizer is None:
            raise Exception("❌ No model available.")

        # Get the document extraction prompt
        prompt = get_document_extraction_prompt(ocr_text)
        
        messages = [
            {"role": "system", "content": "You are a strict financial document parser for Pakistani receipts, bank cheques, and deposit slips. Extract only exact matches from the text. Return ONLY valid JSON with all fields. Never create or guess values."},
            {"role": "user", "content": prompt}
        ]

        try:
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=False,
                repetition_penalty=1.2
            )

            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]

            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                print("⚠️ Could not extract JSON from Qwen response")
                return self._empty_result()

        except Exception as e:
            print(f"⚠️ Qwen extraction error: {e}")
            return self._empty_result()

    def _empty_result(self):
        """Return empty result structure"""
        return {
            "bank_name": None,
            "account_title": None,
            "total_amount": None,
            "ref_id": None,
            "sender_name": None,
            "sender_mobile": None,
            "receiver_name": None,
            "receiver_mobile": None,
            "transaction_date": None,
            "transaction_time": None,
            "pay": None,
            "check_number": None,
            "account_number": None,
            "depositor_name": None,
            "contact_number": None,
            "iban": None
        }

    def clean_and_validate(self, ocr_text, parsed_data):
        """Clean and validate extracted fields with fallback"""
        if not parsed_data:
            return self._empty_result()

        # Ensure all fields exist
        required_fields = ["bank_name", "account_title", "total_amount", "ref_id",
                          "sender_name", "sender_mobile", "receiver_name", 
                          "receiver_mobile", "transaction_date", "transaction_time",
                          "pay", "check_number", "account_number", "depositor_name", 
                          "contact_number", "iban"]

        for field in required_fields:
            if field not in parsed_data:
                parsed_data[field] = None

        # Clean bank_name - fallback to keyword detection
        if not parsed_data.get("bank_name") or parsed_data["bank_name"] in [None, "null", "None"]:
            if ocr_text:
                if re.search(r'easypaisa', ocr_text, re.IGNORECASE):
                    parsed_data["bank_name"] = "Easypaisa"
                elif re.search(r'jazzcash', ocr_text, re.IGNORECASE):
                    parsed_data["bank_name"] = "JazzCash"
                elif re.search(r'sadapay', ocr_text, re.IGNORECASE):
                    parsed_data["bank_name"] = "SadaPay"
                elif re.search(r'nayapay', ocr_text, re.IGNORECASE):
                    parsed_data["bank_name"] = "NayaPay"

        # Clean total_amount - remove commas, keep decimals
        if parsed_data.get("total_amount") and parsed_data["total_amount"] not in [None, "null", "None"]:
            amount = str(parsed_data["total_amount"])
            amount = re.sub(r'[^\d\.]', '', amount)
            try:
                if float(amount) > 0:
                    parsed_data["total_amount"] = amount
                else:
                    parsed_data["total_amount"] = None
            except:
                parsed_data["total_amount"] = None

        # Fallback amount extraction from OCR
        if not parsed_data.get("total_amount") and ocr_text:
            amount_patterns = [
                r'Total Amount[\s:]*([0-9,]+\.?[0-9]*)',
                r'Transaction Amount[\s:]*([0-9,]+\.?[0-9]*)',
                r'Amount[\s:]*([0-9,]+\.?[0-9]*)',
                r'PKR[\s]*([0-9,]+\.?[0-9]*)',
                r'Rs\.?[\s]*([0-9,]+\.?[0-9]*)',
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, ocr_text, re.IGNORECASE)
                if match:
                    amount = match.group(1).replace(',', '')
                    parsed_data["total_amount"] = amount
                    break

        # Clean sender_mobile
        if parsed_data.get("sender_mobile") and parsed_data["sender_mobile"] not in [None, "null", "None"]:
            mobile = str(parsed_data["sender_mobile"])
            digits = re.sub(r'\D', '', mobile)
            if digits.startswith('92') and len(digits) == 12:
                digits = '0' + digits[2:]
            if len(digits) == 11 and digits.startswith('03'):
                parsed_data["sender_mobile"] = digits
            else:
                parsed_data["sender_mobile"] = None

        # Clean receiver_mobile
        if parsed_data.get("receiver_mobile") and parsed_data["receiver_mobile"] not in [None, "null", "None"]:
            mobile = str(parsed_data["receiver_mobile"])
            digits = re.sub(r'\D', '', mobile)
            if digits.startswith('92') and len(digits) == 12:
                digits = '0' + digits[2:]
            if len(digits) == 11 and digits.startswith('03'):
                parsed_data["receiver_mobile"] = digits
            else:
                parsed_data["receiver_mobile"] = None

        # Copy account_title to sender_name if sender_name is empty
        if not parsed_data.get("sender_name") and parsed_data.get("account_title"):
            parsed_data["sender_name"] = parsed_data["account_title"]

        # Clean receiver_name (remove extra text)
        if parsed_data.get("receiver_name") and parsed_data["receiver_name"] not in [None, "null", "None"]:
            name = str(parsed_data["receiver_name"])
            name = re.sub(r'\([^)]*\)', '', name)
            name = name.strip()
            parsed_data["receiver_name"] = name if len(name) > 2 else None

        return parsed_data

    def process(self, ocr_text):
        """Process OCR text and return extracted fields"""
        print("\n" + "="*60)
        print("🏦 QWEN DOCUMENT PARSER")
        print("📱 Bank Cheques | Deposit Slips | Digital Receipts")
        print("="*60)

        if not ocr_text or len(ocr_text) < 10:
            print("❌ No valid text extracted from input")
            return self._empty_result()

        print(f"📊 Total characters: {len(ocr_text)}")
        print(f"📄 OCR Text Preview: {ocr_text[:300]}...")

        # Extract fields using Qwen
        parsed_data = self.extract_fields_with_qwen(ocr_text)

        if parsed_data:
            # Clean and validate
            parsed_data = self.clean_and_validate(ocr_text, parsed_data)
            print("✅ Extraction complete!")
            return parsed_data
        else:
            print("❌ Extraction failed")
            return self._empty_result()

    def print_clean_json(self, data):
        """Print clean JSON output"""
        if not data:
            print("No data to print")
            return

        print("\n" + "="*60)
        print("📊 EXTRACTED FIELDS - CLEAN JSON")
        print("="*60)
        
        # Filter out null values for cleaner display
        non_null = {k: v for k, v in data.items() if v is not None}
        
        print(json.dumps(non_null, indent=2, ensure_ascii=False))
        
        # Summary
        print("\n" + "="*60)
        print("📈 EXTRACTION SUMMARY")
        print("="*60)
        found_fields = {k: v for k, v in data.items() if v is not None}
        missing_fields = {k: v for k, v in data.items() if v is None}

        print(f"✅ Found ({len(found_fields)} fields): {', '.join(found_fields.keys())}")
        if missing_fields:
            print(f"❌ Missing ({len(missing_fields)} fields): {', '.join(missing_fields.keys())}")
        print("="*60)