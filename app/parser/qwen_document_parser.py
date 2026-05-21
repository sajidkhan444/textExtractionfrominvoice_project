# app/parser/qwen_document_parser.py

import re
import json
import torch
import concurrent.futures
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
        self.model.eval()
        print("✅ Document Qwen parser initialized")

    def _convert_to_text(self, ocr_input):
        """Convert various input formats to text string"""
        if isinstance(ocr_input, dict):
            # Convert dictionary to text lines
            lines = []
            for key, value in ocr_input.items():
                if isinstance(value, str) and value.strip():
                    lines.append(value.strip())
            return '\n'.join(lines)
        elif isinstance(ocr_input, str):
            return ocr_input
        elif isinstance(ocr_input, list):
            return '\n'.join([str(item) for item in ocr_input])
        else:
            return str(ocr_input)

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

            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # Only use compatible parameters
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            generated_ids = generated_ids[0][len(inputs['input_ids'][0]):]
            response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                print("⚠️ Could not extract JSON from Qwen response")
                print(f"   Response preview: {response[:200]}...")
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

    def _fallback_extraction(self, ocr_text):
        """Fallback extraction using regex when Qwen fails"""
        extracted = self._empty_result()
        
        if not ocr_text:
            return extracted
        
        # Extract amount
        amount_match = re.search(r'Amount[\s:]*([0-9,]+\.?[0-9]*)', ocr_text, re.IGNORECASE)
        if amount_match:
            extracted['total_amount'] = amount_match.group(1).replace(',', '')
        
        # Extract reference ID
        ref_match = re.search(r'ID#([0-9]+)', ocr_text)
        if ref_match:
            extracted['ref_id'] = ref_match.group(1)
        
        # Extract bank name
        if 'easypaisa' in ocr_text.lower():
            extracted['bank_name'] = 'Easypaisa'
        elif 'jazzcash' in ocr_text.lower():
            extracted['bank_name'] = 'JazzCash'
        elif 'sadapay' in ocr_text.lower():
            extracted['bank_name'] = 'SadaPay'
        
        # Extract sender name (after "Sent by")
        sender_match = re.search(r'Sent by[\s:]*([A-Za-z\s]+)', ocr_text, re.IGNORECASE)
        if sender_match:
            extracted['sender_name'] = sender_match.group(1).strip()
            extracted['account_title'] = extracted['sender_name']
        
        # Extract sender mobile
        mobile_match = re.search(r'Sent by.*?(03[0-9]{9})', ocr_text, re.IGNORECASE)
        if mobile_match:
            extracted['sender_mobile'] = mobile_match.group(1)
        
        # Extract receiver name
        receiver_match = re.search(r'Sent to[\s:]*([A-Za-z\s]+)', ocr_text, re.IGNORECASE)
        if receiver_match:
            extracted['receiver_name'] = receiver_match.group(1).strip()
        
        # Extract receiver mobile
        receiver_mobile_match = re.search(r'Sent to.*?(03[0-9]{9})', ocr_text, re.IGNORECASE)
        if receiver_mobile_match:
            extracted['receiver_mobile'] = receiver_mobile_match.group(1)
        
        # Extract date
        date_match = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})', ocr_text)
        if not date_match:
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', ocr_text)
        if date_match:
            extracted['transaction_date'] = date_match.group(1)
        
        # Extract time
        time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', ocr_text, re.IGNORECASE)
        if time_match:
            extracted['transaction_time'] = time_match.group(1)
        
        return extracted

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

        # Clean total_amount
        if parsed_data.get("total_amount") and parsed_data["total_amount"] not in [None, "null", "None"]:
            amount = str(parsed_data["total_amount"])
            amount_match = re.search(r'([\d,]+\.?\d*)', amount)
            if amount_match:
                amount = amount_match.group(1).replace(',', '')
                try:
                    if float(amount) > 0:
                        parsed_data["total_amount"] = amount
                    else:
                        parsed_data["total_amount"] = None
                except:
                    parsed_data["total_amount"] = None
            else:
                parsed_data["total_amount"] = None

        # Clean sender_mobile
        if parsed_data.get("sender_mobile") and parsed_data["sender_mobile"] not in [None, "null", "None"]:
            mobile = str(parsed_data["sender_mobile"])
            digits = re.sub(r'\D', '', mobile)
            if digits.startswith('92') and len(digits) == 12:
                digits = '0' + digits[2:]
            elif digits.startswith('3') and len(digits) == 10:
                digits = '0' + digits
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
            elif digits.startswith('3') and len(digits) == 10:
                digits = '0' + digits
            if len(digits) == 11 and digits.startswith('03'):
                parsed_data["receiver_mobile"] = digits
            else:
                parsed_data["receiver_mobile"] = None

        # Copy account_title to sender_name if sender_name is empty
        if not parsed_data.get("sender_name") and parsed_data.get("account_title"):
            parsed_data["sender_name"] = parsed_data["account_title"]

        # Clean receiver_name
        if parsed_data.get("receiver_name") and parsed_data["receiver_name"] not in [None, "null", "None"]:
            name = str(parsed_data["receiver_name"])
            name = re.sub(r'\([^)]*\)', '', name)
            name = name.strip()
            parsed_data["receiver_name"] = name if len(name) > 2 else None

        # Clean account_title
        if parsed_data.get("account_title") and parsed_data["account_title"] not in [None, "null", "None"]:
            name = str(parsed_data["account_title"])
            name = re.sub(r'\s+\d+$', '', name)
            name = name.strip()
            parsed_data["account_title"] = name if len(name) > 2 else None

        # Clean check_number
        if parsed_data.get("check_number") and parsed_data["check_number"] not in [None, "null", "None"]:
            digits = re.sub(r'\D', '', str(parsed_data["check_number"]))
            parsed_data["check_number"] = digits if digits else None

        # Clean account_number
        if parsed_data.get("account_number") and parsed_data["account_number"] not in [None, "null", "None"]:
            digits = re.sub(r'\D', '', str(parsed_data["account_number"]))
            parsed_data["account_number"] = digits if digits else None

        return parsed_data

    def process(self, ocr_input):
        """Process OCR input (string or dict) and return extracted fields"""
        print("\n" + "="*60)
        print("🏦 QWEN DOCUMENT PARSER")
        print("📱 Bank Cheques | Deposit Slips | Digital Receipts")
        print("="*60)

        # Convert input to text string
        ocr_text = self._convert_to_text(ocr_input)

        if not ocr_text or len(ocr_text) < 10:
            print("❌ No valid text extracted from input")
            return self._empty_result()

        print(f"📊 Total characters: {len(ocr_text)}")
        print(f"📄 OCR Text Preview: {ocr_text[:300]}...")

        # Try Qwen extraction with timeout
        parsed_data = None
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.extract_fields_with_qwen, ocr_text)
                parsed_data = future.result(timeout=45)  # 45 second timeout
        except concurrent.futures.TimeoutError:
            print("⚠️ Qwen extraction timed out after 45 seconds, using fallback")
            parsed_data = None
        except Exception as e:
            print(f"⚠️ Qwen extraction error: {e}")
            parsed_data = None

        if parsed_data and any(v for v in parsed_data.values() if v):
            # Clean and validate
            parsed_data = self.clean_and_validate(ocr_text, parsed_data)
            print("✅ Extraction complete!")
            return parsed_data
        else:
            print("⚠️ Qwen extraction failed, using fallback extraction")
            parsed_data = self._fallback_extraction(ocr_text)
            print("✅ Fallback extraction complete!")
            return parsed_data

    def print_clean_json(self, data):
        """Print clean JSON output"""
        if not data:
            print("No data to print")
            return

        print("\n" + "="*60)
        print("📊 EXTRACTED FIELDS - CLEAN JSON")
        print("="*60)
        
        non_null = {k: v for k, v in data.items() if v is not None}
        print(json.dumps(non_null, indent=2, ensure_ascii=False))
        
        print("\n" + "="*60)
        print("📈 EXTRACTION SUMMARY")
        print("="*60)
        found_fields = {k: v for k, v in data.items() if v is not None}
        missing_fields = {k: v for k, v in data.items() if v is None}

        print(f"✅ Found ({len(found_fields)} fields): {', '.join(found_fields.keys())}")
        if missing_fields:
            print(f"❌ Missing ({len(missing_fields)} fields): {', '.join(missing_fields.keys())}")
        print("="*60)