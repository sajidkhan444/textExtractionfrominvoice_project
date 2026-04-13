"""Qwen invoice parser."""

import re
import json
from app.core.prompts import get_invoice_extraction_prompt


class QwenInvoiceParser:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def extract_fields_with_qwen(self, extracted_json):
        """Use Qwen to intelligently extract specific fields from the OCR JSON"""
        
        # Convert JSON to string
        if isinstance(extracted_json, list):
            json_str = "\n".join(extracted_json)
        else:
            json_str = json.dumps(extracted_json, indent=2, ensure_ascii=False)
        
        prompt = get_invoice_extraction_prompt(json_str)
        
        messages = [
            {"role": "system", "content": "You are a strict invoice parser that only extracts fields matching exact patterns. If a field doesn't match the required format, you set it to null. You never guess or create values."},
            {"role": "user", "content": prompt}
        ]
        
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        generated_ids = self.model.generate(**model_inputs, max_new_tokens=512, temperature=0.1, do_sample=False)
        generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                print("⚠️ Could not extract JSON from Qwen response")
                return None
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing error: {e}")
            return None

    def clean_and_validate(self, parsed_data):
        """Clean and validate extracted fields with strict rules"""

        # Clean phone number - IMPROVED with better pattern matching
        if parsed_data.get("phone_number"):
            phone = str(parsed_data["phone_number"])

            # Remove all non-digit characters first
            digits_only = re.sub(r'\D', '', phone)

            # Normalize prefixes: +92, 0092, 92 -> 0
            if digits_only.startswith('92') and len(digits_only) in [11, 12]: # 923xxxxxxxxx (11 digits after 92) or 924xxxxxxx (10 digits after 92)
                digits_only = '0' + digits_only[2:]
            elif digits_only.startswith('0092') and len(digits_only) in [12, 13]: # 00923xxxxxxxxx (12 digits after 0092) or 00924xxxxxxx (11 digits after 0092)
                digits_only = '0' + digits_only[4:]
            elif digits_only.startswith('0'):
                # Already starts with 0, keep as is
                pass
            elif len(digits_only) == 10 and digits_only.startswith('3'): # e.g. 3xxxxxxxxx, assume mobile, add leading 0
                digits_only = '0' + digits_only
            elif len(digits_only) == 9 and digits_only.startswith(('2', '4', '5')): # e.g. 21xxxxxxx (Karachi), 42xxxxxxx (Lahore), 51xxxxxxx (Islamabad)
                digits_only = '0' + digits_only


            # Validate against Pakistani mobile and landline patterns
            # Mobile: 11 digits, starts with 03
            if len(digits_only) == 11 and digits_only.startswith('03'):
                parsed_data["phone_number"] = digits_only
            # Landline (common areas): 10 digits, starts with 0 followed by 2, 4, 5 etc.
            elif len(digits_only) == 10 and digits_only.startswith(('021', '042', '051', '055', '061', '071', '091')):
                parsed_data["phone_number"] = digits_only
            else:
                parsed_data["phone_number"] = None
        else:
            parsed_data["phone_number"] = None

        # Validate NTN format - STRICT
        if parsed_data.get("ntn"):
            ntn = str(parsed_data["ntn"])
            # Remove any letters at the beginning (like D from D389505-3)
            ntn = re.sub(r'^[A-Za-z]+', '', ntn)
            # Keep only digits and hyphen
            cleaned = re.sub(r'[^\d-]', '', ntn)

            # Check for pattern: 7 digits hyphen 1 digit
            if re.match(r'^\d{7}-\d$', cleaned):
                parsed_data["ntn"] = cleaned
            else:
                # Try to extract 7 digits + 1 digit
                match = re.search(r'(\d{7})-?(\d)', cleaned)
                if match:
                    parsed_data["ntn"] = f"{match.group(1)}-{match.group(2)}"
                else:
                    parsed_data["ntn"] = None
        else:
            parsed_data["ntn"] = None

        # Validate STRN format - IMPROVED with better pattern matching
        if parsed_data.get("strn"):
            strn = str(parsed_data["strn"])

            # First, check if it's already 13 digits
            digits = re.sub(r'\D', '', strn)

            if len(digits) == 13:
                parsed_data["strn"] = digits
            else:
                # Try to find STRN in different formats
                # Format 1: XX-XX-XXXX-XXX-XX (hyphenated)
                hyphen_match = re.search(r'(\d{2})-(\d{2})-(\d{4})-(\d{3})-(\d{2})', strn)
                if hyphen_match:
                    cleaned = ''.join(hyphen_match.groups())
                    if len(cleaned) == 13:
                        parsed_data["strn"] = cleaned
                    else:
                        parsed_data["strn"] = None
                # Format 2: XXXXXXXXXXXXX (13 digits already)
                elif len(digits) == 13:
                    parsed_data["strn"] = digits
                else:
                    parsed_data["strn"] = None
        else:
            parsed_data["strn"] = None

        # Validate Invoice Number - Must contain "INV" or similar pattern
        if parsed_data.get("invoice_number"):
            invoice = str(parsed_data["invoice_number"])
            # Check for INV pattern (case insensitive)
            if re.search(r'inv', invoice, re.IGNORECASE):
                # Remove garbage characters
                invoice = re.sub(r'[{}\\<>]', '', invoice)
                parsed_data["invoice_number"] = invoice.strip()
            else:
                # Check if it looks like an invoice number (alphanumeric, 8-20 chars)
                if re.match(r'^[A-Z0-9]{8,20}$', invoice, re.IGNORECASE):
                    parsed_data["invoice_number"] = invoice
                else:
                    parsed_data["invoice_number"] = None
        else:
            parsed_data["invoice_number"] = None

        # Validate Company Name - reject garbage and clean
        if parsed_data.get("company_name"):
            company = str(parsed_data["company_name"])
            # Remove garbage characters
            company = re.sub(r'[{}\\<>]', '', company)
            # Remove trailing words like "INVOICE", "BILL", etc.
            company = re.sub(r'\s+(INVOICE|BILL|TAX INVOICE|DEBIT NOTE|CREDIT NOTE)$', '', company, flags=re.IGNORECASE)
            company = company.strip()

            if len(company) < 3:
                parsed_data["company_name"] = None
            else:
                parsed_data["company_name"] = company
        else:
            parsed_data["company_name"] = None

        # Validate Date - ensure proper format
        if parsed_data.get("date"):
            date_str = str(parsed_data["date"])
            # Try to extract date pattern
            date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
            if date_match:
                day, month, year = date_match.group(1), date_match.group(2), date_match.group(3)
                if len(year) == 2:
                    year = '20' + year
                parsed_data["date"] = f"{day}/{month}/{year}"
            else:
                parsed_data["date"] = None
        else:
            parsed_data["date"] = None

        # Validate Order Number
        if parsed_data.get("order_number"):
            order = str(parsed_data["order_number"])
            # Remove labels
            order = re.sub(r'(?i)(order|ord|ordr|po|no)[:\s-]*', '', order)
            order = order.strip()
            if len(order) < 3:
                parsed_data["order_number"] = None
            else:
                parsed_data["order_number"] = order
        else:
            parsed_data["order_number"] = None

        return parsed_data


    def reorganize_ocr_by_proximity(self, extracted_json):
        """
        Reorganize OCR text by grouping nearby lines together
        This helps Qwen see labels and values that are close but on different lines
        """

        # Convert JSON lines to list with line numbers
        lines = []
        for key, value in extracted_json.items():
            line_num = int(key.split('_')[1])
            lines.append({
                'number': line_num,
                'text': value
            })

        # Sort by line number
        lines.sort(key=lambda x: x['number'])

        # Group lines into windows of 3 lines
        grouped_lines = []
        for i in range(0, len(lines), 2):  # Step by 2 to create overlap
            window = []
            for j in range(max(0, i-1), min(len(lines), i+3)):
                window.append(lines[j]['text'])
            grouped_lines.append(' '.join(window))

        # Return as a simple list for Qwen
        return grouped_lines

    def process(self, extracted_json):
        """Main processing function - THIS IS THE METHOD THAT GETS CALLED"""
        print("\n" + "="*60)
        print("🤖 QWEN INTELLIGENT INVOICE PARSER")
        print("="*60)

        print("\n🔄 Sending to Qwen for intelligent extraction...")

        # IMPORTANT: Reorganize OCR by proximity BEFORE sending to Qwen
        reorganized_data = self.reorganize_ocr_by_proximity(extracted_json)

        # Extract with Qwen using reorganized data
        parsed_data = self.extract_fields_with_qwen(reorganized_data)

        if parsed_data:
            # Clean and validate with strict rules
            parsed_data = self.clean_and_validate(parsed_data)

            print("\n✅ Qwen extraction complete!")
            return parsed_data
        else:
            print("❌ Qwen extraction failed")
            return None

    def print_clean_json(self, data):
        """Print the clean JSON output"""
        print("\n" + "="*60)
        print("📊 CLEAN STRUCTURED JSON OUTPUT")
        print("="*60)
        print(json.dumps(data, indent=2, ensure_ascii=False))