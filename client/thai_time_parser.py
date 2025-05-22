
import re
from datetime import datetime

# แปลงเลขไทยและเลขคำเป็นเลขอารบิก
THAI_NUM_TEXT = {
    "หนึ่ง": 1, "สอง": 2, "สาม": 3, "สี่": 4, "ห้า": 5, "หก": 6,
    "เจ็ด": 7, "แปด": 8, "เก้า": 9, "สิบ": 10,
    "๑": 1, "๒": 2, "๓": 3, "๔": 4, "๕": 5,
    "๖": 6, "๗": 7, "๘": 8, "๙": 9, "๐": 0
}

def replace_thai_numbers(text: str) -> str:
    for word, digit in THAI_NUM_TEXT.items():
        text = text.replace(word, str(digit))
    return text

def extract_time_expression(text: str) -> str | None:
    text = replace_thai_numbers(text)  # ทำให้ "บ่ายสอง" → "บ่าย2"
    time_patterns = [
        r"ตี\s*\d+(ครึ่ง)?",
        r"บ่าย\s*\d+(ครึ่ง)?",
        r"\d+\s*ทุ่ม(ครึ่ง)?",
        r"\d+\s*โมง(\s*เช้า|\s*เย็น)?(ครึ่ง)?",
        r"เที่ยงคืน", r"เที่ยง",
        r"บ่าย", r"เช้า", r"เย็น",
        r"ตอน\s*บ่าย", r"ตอน\s*เย็น"
    ]

    for pattern in time_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group().replace(" ", "")
    return None

def parse_thai_time(text: str) -> datetime:
    now = datetime.now()
    text = text.strip().lower()

    if text == "เที่ยงคืน":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if text == "เที่ยง":
        return now.replace(hour=12, minute=0, second=0, microsecond=0)

    patterns = [
        (r"ตี(\d+)(ครึ่ง)?", lambda h, half: (h, 30 if half else 0)),
        (r"บ่าย(\d+)(ครึ่ง)?", lambda h, half: (12 + h, 30 if half else 0)),
        (r"(\d+)ทุ่ม(ครึ่ง)?", lambda h, half: (18 + h, 30 if half else 0)),
        (r"(\d+)โมงเช้า(ครึ่ง)?", lambda h, half: (6 + h, 30 if half else 0)),
        (r"(\d+)โมงเย็น(ครึ่ง)?", lambda h, half: (12 + h, 30 if half else 0)),
        (r"(\d+)โมง(ครึ่ง)?", lambda h, half: (6 + h if h <= 6 else h, 30 if half else 0))
    ]
    
    for pattern, converter in patterns:
        match = re.match(pattern, text)
        if match:
            
            h = int(match.group(1))           
            half = match.group(2) is not None
            hour, minute = converter(h, half)
            result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            print(f"result={result}")
            return result

    raise ValueError(f"ไม่สามารถแปลง '{text}' เป็นเวลาได้")
