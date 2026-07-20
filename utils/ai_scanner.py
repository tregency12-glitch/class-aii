import json
import re
import os
from PIL import Image
import google.generativeai as genai

# 🚨 ใส่ Gemini API Key ของระบบส่วนกลางที่คุณสมัครไว้ที่นี่ที่เดียว
CENTRAL_GEMINI_API_KEY = os.environ.get("CENTRAL_GEMINI_API_KEY") or "ใส่_GEMINI_KEY_ส่วนกลางตรงนี้"

PROMPT = """
ดึงข้อมูลตารางเรียนจากภาพนี้ แล้วตอบเป็น JSON array เท่านั้น ไม่มีข้อความอื่น
แต่ละรายการต้องมี key: subject, day, start_time, end_time, room
- day ใช้ภาษาไทย: จันทร์, อังคาร, พุธ, พฤหัสบดี, ศุกร์, เสาร์, อาทิตย์
- start_time/end_time รูปแบบ HH:MM (24 ชม.)
ตัวอย่าง:
[
  {"subject":"คณิตศาสตร์","day":"จันทร์","start_time":"09:00","end_time":"10:30","room":"301"}
]
"""


def extract_json(text: str) -> list:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("AI response is not a JSON array")
    return data


def validate_entry(entry: dict) -> dict:
    required = ("subject", "day", "start_time", "end_time", "room")
    for key in required:
        if key not in entry or not str(entry[key]).strip():
            raise ValueError(f"Missing field: {key}")
    return {
        "subject": str(entry["subject"]).strip(),
        "day": str(entry["day"]).strip(),
        "start_time": str(entry["start_time"]).strip(),
        "end_time": str(entry["end_time"]).strip(),
        "room": str(entry["room"]).strip(),
    }


# 🌟 แก้ไข: ตั้งค่าใช้งานสิทธิ์ด้วย API Key ส่วนกลางโดยอัตโนมัติ
def scan_schedule_image(image: Image.Image, api_key: str = None) -> list:
    active_key = api_key or CENTRAL_GEMINI_API_KEY
    if not active_key or active_key == "ใส่_GEMINI_KEY_ส่วนกลางตรงนี้":
        raise ValueError("❌ ระบบยังไม่ได้ติดตั้ง Central Gemini API Key ในโค้ดหลังบ้าน (utils/ai_scanner.py)")
        
    # ตั้งค่าใช้งานสิทธิ์ด้วย API Key
    genai.configure(api_key=active_key)
    
    # โมเดลกลุ่ม Flash ที่ต้องการทดลองเชื่อมต่อไล่ตามลำดับเวอร์ชันใหม่ไปเก่า
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash"
    ]
    
    last_err = None
    response = None
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([PROMPT, image])
            if response:
                break
        except Exception as e:
            last_err = e
            continue
            
    if response is None:
        raise last_err or ValueError("Failed to initialize any of the Gemini Flash models.")
    
    raw = response.text or ""
    parsed = extract_json(raw)
    
    # ตรวจสอบและคลีนข้อมูลในอาร์เรย์ก่อนส่งกลับไปแสดงผลบน Dashboard
    return [validate_entry(item) for item in parsed]