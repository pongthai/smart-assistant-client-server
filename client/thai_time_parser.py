
import re
from datetime import datetime, timedelta
from typing import Optional

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
    
def extract_relative_time(text: str):
    match = re.search(r"(อีก)\s*(\d{1,2})\s*(ชั่วโมง|นาที)", text)
    if match:
        value = int(match.group(2))
        unit = match.group(3)
        if "ชั่วโมง" in unit:
            return timedelta(hours=value)
        elif "นาที" in unit:
            return timedelta(minutes=value)
    return None

def extract_extra_minutes(text: str) -> int:
    match = re.search(r"(?:\s|ตอน|เวลา)?\d{1,2}[^\\d]*(\d{1,2})\s*นาที", text)
    if match:
        return int(match.group(1))
    return 0

def extract_time_digit(text):
    match = re.search(r"(?:เวลา)?\s*(\d{1,2})[:.](\d{1,2})\s*(น\.?)?", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return hour, minute
    return None

def extract_time_expression(text: str) -> Optional[str]:
    text = replace_thai_numbers(text)  # Assumes this function is defined elsewhere

    time_patterns = [
        r"ตี\s*\d+(ครึ่ง)?",
        r"บ่าย\s*\d+(ครึ่ง)?",
        r"\d+\s*ทุ่ม(ครึ่ง)?",
        r"\d+\s*โมง(\s*เช้า|\s*เย็น)?(ครึ่ง)?",
        r"เที่ยงคืน", r"เที่ยง",
        r"บ่าย", r"เช้า", r"เย็น",
        r"ตอน\s*บ่าย", r"ตอน\s*เย็น"
    ]

    # Compile the regex patterns for improved performance
    compiled_patterns = [re.compile(pattern) for pattern in time_patterns]

    for pattern in compiled_patterns:
        match = pattern.search(text)
        if match:
            # Return matched group with spaces removed, if found
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
