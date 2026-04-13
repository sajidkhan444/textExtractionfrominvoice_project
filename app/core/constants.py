"""Constants used throughout the application."""

# Model name
MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"

# Table stop words for detecting table headers
TABLE_STOP_WORDS = [
    "sku description", "trade price", "quantity", "free", "total", 
    "basic", "discount", "gst", "net amount", "unit price", 
    "product name", "item code", "cost price", "order qty",
    "net value", "pcs", "s.no", "sr no", "description of goods",
    "item name", "sales qty", "replace qty", "bar code",
    "value exclusive sale tax", "sale tax rate", "total sale tax payable",
    "wh tax", "net payable", "ctn", "u/m", "art#", "item #",
    "regular disc", "special disc", "gross value", "gst value",
    "tp excl", "t.price exl", "r.p", "ctn", "pcs", "sku code",
    "product name", "qty", "rate", "price", "amount", "discount",
    "%", "value", "net", "tax", "gst%", "disc%", "quantity", "qty.",
    "particulars", "unit", "code", "s.no", "sr no", "particular",
    "items", "products", "description", "QTY.", "SN Products", 
    "Value incl. Sales tax", "Further Tax", "Sales tax", "Net amount", 
    "SKU Description", "item code", "cost price", "product description", 
    "Order qty", "SKU Code", "Product Name", "Net value", "PCS", 
    "Unit price", "Description and products", "SR NO", "Total", 
    "S#", "Bonus", "T.P.", "Sr#", "T-qty", "No.", "Barcode code", 
    "Discount Amount", "on hand", "U/M", "S. article No.", 
    "Value Exclusive Sale Tax", "Sale Tax Rate", "Total Sale Tax Payable", 
    "BARCODE", "ANHAAR PRODUCTS DESCRIPTION", "Bar code", "Replace Qty.", 
    "Sales Qty", "ITEM #", "Art#", "Description of goods", "Item Name", 
    "#", "NO", "Description of Products", "Item Product Name", 
    "Unit/Ctn", "S.", "Voucher Total", "WH Tax", "Sup. WHT %", "Net payable",
    "تفصیل", "مقدار", "رقم", "کل", "نمبر", "سیریل نمبر", "کوڈ", "قیمت", 
    "فیصد", "ڈسکاؤنٹ", "ٹیکس", "مالیات", "وزن", "مصنوعات", "آئٹم", 
    "شرح", "مال", "بیان", "شے", "اجناس", "سامان", "فہرست", "درج", 
    "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹", "۰",
    "كيلا", "كلية", "جزيرة", "حصاد", "درجن", "مدى", "يكلف", "ماليين", 
    "كليتين", "جات", "كاف", "سكرتير"
]

# Invoice metadata indicators (NOT table headers)
INVOICE_METADATA_INDICATORS = [
    "ntn", "gst no", "strn", "vendor", "invoice", "date", "phone", 
    "address", "order date", "delivery date", "voucher", "customer",
    "shop", "dist", "ntn:", "gst:", "cnic", "stock debit note",
    "sales tax invoice", "booker", "customer code", "customer name",
    "salesman", "delivery date", "order date", "voucher date", "voucher no",
    "cash memo", "engrofoods", "ph#", "invoice id", "store name", 
    "owner name", "cnic #", "s.t.r number", "ntn number", "booked by",
    "delivery man", "order no", "payment type", "it status", "filler",
    "dist", "shop", "plot", "basement", "block", "street", "center",
    "sector", "rawalpindi", "islamabad", "lahore", "karachi", "printed",
    "time", "pm", "am", "page", "bill to", "ship to", "phone no",
    "mobile", "contact", "fax", "email", "www", "http", "https"
]