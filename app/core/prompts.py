def get_invoice_extraction_prompt(json_str):
    """Get the prompt for Qwen invoice extraction."""
    return f"""You are an intelligent invoice parser. Extract ONLY the following fields from the invoice data below. BE STRICT - if the field doesn't match the exact patterns below, set it to null.

CRITICAL INSTRUCTION: Labels and values may appear on different lines. SCAN ALL LINES. Look for patterns across nearby lines (within 2-3 lines of each other).

1. COMPANY NAME - DYNAMIC EXTRACTION RULES:
   - Look for business names that may be followed by words like "INVOICE", "BILL", "TAX INVOICE", "DEBIT NOTE", "CREDIT NOTE"
   - Extract JUST the business name, ignore the document type words that follow
   - Examples:
     - "Green Traders INVOICE" -> extract "Green Traders"
     - "SM TRADERS Sales Tax Invoice" -> extract "SM TRADERS"
     - "SHAN MARKETING SERVICES STOCK DEBIT NOTE" -> extract "SHAN MARKETING SERVICES"
     - "Pcc Super Market E-11" -> extract "Pcc Super Market E-11"
     - "AJMI DISTRIBUTION NETWORK PVT LTD Invoice" -> extract "AJMI DISTRIBUTION NETWORK PVT LTD"
   - Look for patterns ending with: Pvt Ltd, Limited, Enterprises, Services, Marketing, Trading, Traders, Distributors, Industries, Corporation, Company, Co., Corp., Inc., LLC, Super Market, Store
   - If a line contains both a company name AND words like INVOICE/BILL/DEBIT NOTE, extract ONLY the company name part
   - Company names can appear ANYWHERE - at beginning, middle, or end of invoice
   - If you see a line that starts with a business name and then has invoice-related words, extract just the business name
   - If no clear company name found, set to null


2. PHONE NUMBER - INTELLIGENT EXTRACTION RULES:
   IMPORTANT: The OCR may extract numbers and labels in any order (number first, then label, or label first, then number)

   STEP 1: Find ALL numbers that LOOK LIKE phone numbers in the ENTIRE document:
   - 10-12 digit numbers
   - Numbers with spaces: "051 5790808", "0332 0322090"
   - Numbers with hyphens: "051-5790808", "0332-0322090"
   - Numbers starting with 03, "051", "021", "042", etc.

   STEP 2: Find ALL phone-related labels ANYWHERE in the document:
   - "Phone", "Phonc", "Phne", "Tel", "Mobile", "Cell", "Contact", "Ph No", "Phone No"
   - Even misspelled versions

   STEP 3: Match numbers to labels based on PROXIMITY:
   - If a phone number and phone label appear within 3 lines of each other → EXTRACT
   - If a phone number exists AND ANY phone label exists anywhere → EXTRACT (associate them)
   - If only a phone number exists with no label but looks like a phone → EXTRACT it anyway

   STEP 4: For each potential phone number, CLEAN it:
   - Remove spaces, hyphens, dots
   - Convert +92 or 92 to 0
   - If starts with 3 and has 10 digits, add leading 0

   VALID outputs:
   - "Phonc No. 051 5790808" (label + number) -> clean to "0515790808" (landline)
   - "051 5790808" then next line "Phone:" -> clean to "0515790808"
   - Just "03320322090" anywhere with "Mobile" somewhere -> clean to "03320322090"

   If no phone-like number found, set to null.


3. STRN (Sales Tax Registration Number) - LOOK ACROSS LINES:
   - Search EVERY line for STRN patterns
   - Valid formats:
     * 13 consecutive digits: "3277876156575"
     * Hyphenated: "17-03-9998-473-28" -> "1703999847328"
     * With spaces: "32778 76184305"
   - Look for labels on SAME or ADJACENT lines:
     * "STRN:", "STN:", "Sales Tax Registration No:", "GST No:", "ST Reg No:"
   - IMPORTANT: If label on Line 3 says "STN:" and value on Line 4 is "3277876156575", extract it
   - Example: Line 4 has "Rawalpindi Cantt STN: 3277876156575" -> Extract "3277876156575"
   - Example: Line 7 has "STN:", Line 8 has "3277876337380" -> Extract "3277876337380"

4. NTN (National Tax Number) - LOOK ACROSS LINES:
   - Format: 7 digits, hyphen, 1 digit (e.g., "5203253-2", "0389505-3")
   - Look for labels on SAME or ADJACENT lines:
     * "NTN:", "NTN No:", "Vendor NTN"
   - IMPORTANT: If label on Line 3 says "NTN:" and value on Line 4 has the number, extract it
   - Example: Line 3 has "NTN: 5203253-2" -> Extract "5203253-2"
   - Example: Line 7 has "NTN:", Line 8 has "0389505-3" -> Extract "0389505-3"
   - If you see "D389505-3", remove 'D' to get "389505-3"

5. ORDER NUMBER: Look for "Order", "ORD", "ORDR", "PO" followed by code. Extract ONLY the code, not the label. Example: If line says "Inv ORDR- No 012510000107", extract "012510000107". If no clear order number, put null.

6. INVOICE NUMBER - CRITICAL RULE:
   - Find ANY text that contains "INV" (case insensitive: INV, iNV, Inv, etc.)
   - Extract the ENTIRE text block that contains "INV" - DO NOT truncate or modify
   - Keep ALL characters including letters, numbers, and special characters
   - Examples of CORRECT extraction:
     - "D7000047ZINV2263590" -> extract FULL "D7000047ZINV2263590"
     - "DOOS8iNV38091" -> extract FULL "DOOS8iNV38091"
     - "43242INV4343" -> extract FULL "43242INV4343"
     - "INV-2025-001" -> extract FULL "INV-2025-001"
     - "IADN25127843" -> extract FULL "IADN25127843"
   - DO NOT extract only numbers - keep the entire string
   - DO NOT truncate or remove any part of the text
   - If multiple lines contain INV, choose the one that looks most like an invoice number
   - If no "INV" found, set to null

7. Date: Look for date patterns: DD/MM/YY, DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY. Convert to DD/MM/YYYY format. If not found, set to null.


CRITICAL RULES - MUST FOLLOW:
- ONLY extract values that appear EXACTLY in the text
- NEVER create phone numbers, NTNs, STRNs, or invoice numbers
- If a value is not clearly present, set it to null
- DO NOT add "INV-" prefix to invoice numbers
- DO NOT reformat dates unless you see a clear pattern
- NEVER combine fields (like date + invoice number)
- NEVER extract labels as values
- If a field is not CLEARLY present after checking ALL lines, set to null
- If label and value are on different lines (within 2-3 lines), STILL EXTRACT
- SCAN ALL LINES - don't stop at first match

EXAMPLES OF CORRECT EXTRACTION:
- Line 3: "NTN: 5203253-2 Oalc: January 03, 2025" -> NTN="5203253-2", Date="03/01/2025"
- Line 4: "Rawalpindi Cantt STN: 3277876156575" -> STRN="3277876156575"
- Line 5: "Phonc No. 051 5790808" -> Phone="0515790808"
- Line 7: "NTN: 0389505-3" -> NTN="0389505-3" (if first NTN was invalid)
- For Invoice Number: MUST contain "INV" substring - this is MANDATORY

Invoice Data (JSON format):
{json_str}

Return ONLY a clean JSON object with these exact keys. Set fields to null if they don't match requirements:
{{
    "company_name": null or string,
    "phone_number": null or string,
    "strn": null or string,
    "ntn": null or string,
    "order_number": null or string,
    "invoice_number": null or string,
    "date": null or string
}}

Do not add any extra text, explanations, or formatting. Return ONLY the clean JSON."""