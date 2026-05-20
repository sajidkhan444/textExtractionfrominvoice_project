# app/core/documents_prompts.py

def get_document_extraction_prompt(ocr_text):
    """Get the prompt for Qwen document extraction (cheques, deposit slips, receipts)"""
    
    return f"""You are an intelligent financial document parser for Pakistani digital receipts and bank transfers. Extract relevant fields from the OCR text below.

CURRENT DOCUMENT OCR TEXT:
{ocr_text}

═══════════════════════════════════════════════════════════════
⚠️ CRITICAL INSTRUCTIONS - READ CAREFULLY ⚠️
═══════════════════════════════════════════════════════════════
1. THIS IS A NEW DOCUMENT - IGNORE EVERYTHING FROM BEFORE
2. ONLY extract values that appear EXACTLY in the text above
3. DO NOT invent, guess, or imagine any values
4. If a value is NOT in the text above, set it to null
5. The text above is the ONLY source of truth
6. For digital wallets, prioritize sender information over recipient

═══════════════════════════════════════════════════════════════
FIELD EXTRACTION RULES
═══════════════════════════════════════════════════════════════

1️⃣ bank_name - Financial service provider name

   STRICT RULES:
   - Look for digital wallet names: "easypaisa", "jazzcash", "sadapay", "nayapay", "upaisa", "keenpay"
   - Look for bank names: "UBL", "HBL", "MCB", "NBP", "BankIslami", "Allied Bank", "Faysal Bank", "Standard Chartered"
   - Check document header/footer for branding
   - If "easypaisa" appears anywhere → extract "Easypaisa"
   - If "jazzcash" appears anywhere → extract "JazzCash"
   - If no bank/wallet name found → set to null

2️⃣ account_title - Sender/Account holder name

   INTELLIGENT EXTRACTION (Priority Order):
   - For Easypaisa/JazzCash: Look for "Sent by:" → extract the name
   - For digital wallets: Look for "From:", "Sender:", "Payer:", "Customer:"
   - For bank transfers: Look for "From Account Title:", "Sender:", "From:"
   - Look for patterns like "From Account Title: SHAKEEL" → "SHAKEEL"
   - Remove phone numbers if attached (e.g., "Sajid Khan 03325459917" → "Sajid Khan")
   - Remove prefixes like "Mr.", "Ms.", "Dr."
   - If multiple names, priority: "Sent by" > "From Account Title" > "Sender" > "From" > "Customer"
   - If no name found → set to null

3️⃣ total_amount - Transaction amount

   COMPREHENSIVE PATTERNS:
   - Look for: "Total Amount:", "Transaction Amount:", "Amount:", "PKR:", "Rs.:", "PKR"
   - Look for numbers with commas (e.g., "40,000", "361,000")
   - Look for numbers with decimals (e.g., "25.00", "100.50")
   - Look for patterns like "PKR 361,000" or "Rs. 25.00"
   - Extract only numeric value (remove currency symbols, commas)
   - Keep decimal points if present
   - Example: "Rs. 25.00" → "25.00"
   - Example: "PKR 361,000" → "361000"
   - Example: "Transaction Amount: 40,000" → "40000"
   - If multiple amounts, take the largest (usually the total)
   - If no amount found → set to null

4️⃣ ref_id - Reference/Transaction ID

   PATTERNS TO MATCH:
   - "ID#48653077000" → "48653077000"
   - "Ref#FT2433900NZLOBCR" → "FT2433900NZLOBCR"
   - "Transaction ID: 1543553046" → "1543553046"
   - "TID:" followed by digits
   - "TRX ID:" followed by alphanumeric
   - "Order ID:" followed by alphanumeric
   - Any pattern starting with "FT", "TXN", "TRX" followed by alphanumeric
   - Remove prefixes (ID#, Ref#, TID:, etc.) - extract ONLY the value
   - If no reference found → set to null

5️⃣ sender_name - Sender name (same as account_title but for clarity)

   EXTRACTION RULES:
   - Same priority as account_title
   - For digital wallets: "Sent by: Sajid Khan" → "Sajid Khan"
   - For bank transfers: "From Account Title: SHAKEEL" → "SHAKEEL"
   - For receipts with "From:" field
   - Remove phone numbers and extra spaces
   - If not found, copy from account_title or set to null

6️⃣ sender_mobile - Sender's mobile number

   STRICT RULES:
   - FORMAT: 03XXXXXXXXX (11 digits starting with 03)
   - For Easypaisa: Look for number after "Sent by:" (same line)
   - For digital wallets: Look for mobile numbers near sender name
   - Pattern: 03[0-9]{{9}}
   - Remove spaces, dashes, country code (+92 → 0)
   - Example: "03325459917" → "03325459917"
   - Example: "+923325459917" → "03325459917"
   - Example: "Sent by: Sajid Khan 03325459917" → "03325459917"
   - If multiple numbers, prioritize number nearest to sender name
   - If no sender mobile found → set to null

7️⃣ receiver_name - Recipient/Beneficiary name

   EXTRACTION RULES:
   - Look for: "Received by:", "Beneficiary Name:", "To:", "Receiver:", "Payee:"
   - For bank transfers: "Beneficiary Name: SAJID KHAN" → "SAJID KHAN"
   - For digital wallets: "Received by: John Doe" → "John Doe"
   - Remove prefixes and extra spaces
   - Remove phone numbers if attached
   - If multiple recipients, take the first one
   - If no receiver found → set to null

8️⃣ receiver_mobile - Recipient's mobile number

   STRICT RULES:
   - FORMAT: 03XXXXXXXXX (11 digits starting with 03)
   - For Easypaisa: Look for number after "Received by:"
   - Pattern: 03[0-9]{{9}}
   - Example: "Received by: 03348991165" → "03348991165"
   - If no receiver mobile found → set to null

9️⃣ transaction_date - Date of transaction

   PATTERNS:
   - Date formats: "8/4/2025", "18-Apr-2026", "04-Dec-2024"
   - Look for: "Date:", "Transaction Date:", "Posted on:"
   - Keep original format (don't convert)
   - Extract exactly as appears
   - If no date found → set to null

🔟 transaction_time - Time of transaction

   PATTERNS:
   - Time formats: "4:14:08 PM", "2:17 PM", "03:30:18 PM"
   - Look for: "Time:", "Transaction Time:", after date
   - Extract exactly as appears
   - If no time found → set to null

═══════════════════════════════════════════════════════════════
DOCUMENT TYPE DETECTION (Auto-adapt extraction)
═══════════════════════════════════════════════════════════════

Based on keywords in text, auto-detect and prioritize:

• EASYPAISA RECEIPT:
  - bank_name = "Easypaisa"
  - account_title = after "Sent by" (extract name only)
  - sender_mobile = phone number after "Sent by"
  - receiver_mobile = after "Received by"
  - total_amount = after "Total Amount" or "Amount"
  - ref_id = after "ID#"

• JAZZCASH RECEIPT:
  - bank_name = "JazzCash"
  - Similar pattern to Easypaisa
  - Look for "Sent by", "Received by"

• SADAPAY/NAYAPAY:
  - bank_name = "SadaPay" or "NayaPay"
  - Similar pattern to Easypaisa

• BANK TRANSFER RECEIPT:
  - bank_name = extracted from header/bank name
  - account_title = "From Account Title" or "From"
  - total_amount = "Transaction Amount" or after "PKR"
  - beneficiary_name = "Beneficiary Name" or "To"

═══════════════════════════════════════════════════════════════

Return ONLY a valid JSON object with these exact 10 keys:

{{
    "bank_name": null,
    "account_title": null,
    "total_amount": null,
    "ref_id": null,
    "sender_name": null,
    "sender_mobile": null,
    "receiver_name": null,
    "receiver_mobile": null,
    "transaction_date": null,
    "transaction_time": null
}}

EXAMPLES OF CORRECT OUTPUTS:

Example 1 (Easypaisa):
{{
    "bank_name": "Easypaisa",
    "account_title": "Sajid Khan",
    "total_amount": "25.00",
    "ref_id": "48653077000",
    "sender_name": "Sajid Khan",
    "sender_mobile": "03325459917",
    "receiver_name": null,
    "receiver_mobile": "03348991165",
    "transaction_date": "18-Apr-2026",
    "transaction_time": "2:17 PM"
}}

Example 2 (Bank Transfer):
{{
    "bank_name": null,
    "account_title": "SHAKEEL",
    "total_amount": "40000",
    "ref_id": "1543553046",
    "sender_name": "SHAKEEL",
    "sender_mobile": null,
    "receiver_name": "SAJID KHAN",
    "receiver_mobile": null,
    "transaction_date": "8/4/2025",
    "transaction_time": "4:14:08 PM"
}}

Example 3 (Inter Bank):
{{
    "bank_name": null,
    "account_title": "AHMED & SONS",
    "total_amount": "361000",
    "ref_id": "FT2433900NZLOBCR",
    "sender_name": "AHMED & SONS",
    "sender_mobile": null,
    "receiver_name": "UBAID UR REHMAN",
    "receiver_mobile": null,
    "transaction_date": "04-Dec-2024",
    "transaction_time": "03:30:18 PM"
}}

Do not add any extra text, explanations, or markdown formatting. Return ONLY the JSON."""