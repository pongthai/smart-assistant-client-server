import re
from slugify import slugify
from datetime import datetime,timedelta
import difflib
from command_entity_map import ENTITY_MAP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CONFIRMATION_KEYWORDS, CANCEL_KEYWORDS, ACTION_KEYWORDS
from thai_time_parser import parse_thai_time, extract_time_expression, extract_time_digit, extract_extra_minutes, extract_relative_time

class CommandDetector:
    def __init__(self):
        self.confirm_keywords = CONFIRMATION_KEYWORDS
        self.cancel_keywords = CANCEL_KEYWORDS
        self.action_keywords = ACTION_KEYWORDS

    def is_confirmation(self, text):
        return any(self._is_full_word_match(text, word) for word in self.confirm_keywords)

    def is_cancellation(self, text):
        return any(self._is_full_word_match(text, word) for word in self.cancel_keywords)

    def _is_full_word_match(self, text, word):
        if not isinstance(text, str):
            return False
        pattern = rf"(?:^|\s|[^ก-๙]){re.escape(word)}(?:$|\s|[^ก-๙])"
        return re.search(pattern, text) is not None

    def format_extra(self, extra):
        if not extra:
            return ""
        if isinstance(extra, str):
            return extra
        if isinstance(extra, dict):
            parts = []
            if "temperature" in extra:
                parts.append(f"ที่ {extra['temperature']} องศา")
            if "volume" in extra:
                parts.append(f"ระดับเสียง {extra['volume']}")
            if "mode" in extra:
                parts.append(f"โหมด {extra['mode']}")
            if not parts:
                parts.append(str(extra))
            return " ".join(parts)
        return str(extra)

    def summarize_command(self, command):
        
        if command['type'] == "home_assistant_command":
            action = command.get("action", "")
            device = command.get("device", "")
            location = command.get("location", "")
            extra_str = self.format_extra(command.get("extra"))
            return f"คุณต้องการ{action}{device}{location}{extra_str} ใช่ไหม?"
        elif command['type'] == "reminder":
            return command['raw_text']

    def find_closest(self, text, options):
        match = difflib.get_close_matches(text, options, n=1, cutoff=0.6)
        print(f"match = {match}")
        return match[0] if match else None

    def parse_reminder(self,text: str):
        print(f"check reminder command text={text}")
         # ✅ 1. Relative time: "อีก 2 ชั่วโมง"
        relative = extract_relative_time(text)
        if relative:
            parsed_time = datetime.now() + relative
            cleaned_text = re.sub(r"(อีก\s*\d+\s*(ชั่วโมง|นาที))", "", text)
            for kw in ["เตือน", "ช่วยเตือน", "แจ้งเตือน", "ว่า", "เวลานี้", "เวลา", "ตอน"]:
                cleaned_text = cleaned_text.replace(kw, "")
            reminder_text = cleaned_text.strip()
            return {
                "type": "reminder",
                "reminder_text": reminder_text,
                "reminder_time": parsed_time.isoformat(),
                "raw_text": text
            }
            
        # ลองจับเวลาแบบไทยก่อน
        time_part = extract_time_expression(text)
        if time_part:
            try:
                parsed_time = parse_thai_time(time_part)
                extra_minutes = extract_extra_minutes(text)
                if extra_minutes:
                    parsed_time += timedelta(minutes=extra_minutes)

                # ลบ keyword และ time_part ออกจากข้อความ
                cleaned_text = text
                for keyword in ["เตือน", "ช่วยเตือน", "แจ้งเตือน", "ว่า", "เวลานี้", "เวลา", "ตอน", time_part]:
                    cleaned_text = cleaned_text.replace(keyword, "")
                reminder_text = cleaned_text.strip()

                return {
                    "type": "reminder",
                    "reminder_text": reminder_text,
                    "reminder_time": parsed_time.isoformat(),
                    "raw_text": text
                }
            except Exception as e:
                print(f"❌ parse_thai_time failed: {e}")

        # ถ้าไม่เจอเวลาแบบไทย → ลองเวลาแบบดิจิทัล
        time_tuple = extract_time_digit(text)
        if time_tuple:
            hour, minute = time_tuple
            parsed_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)

            cleaned_text = text
            cleaned_text = re.sub(r"(เวลา)?\s*\d{1,2}[:.]\d{1,2}\s*(น\.?|am|pm)?", "", cleaned_text)
            for keyword in ["เตือน", "ช่วยเตือน", "แจ้งเตือน", "ว่า", "ว่าต้อง", "เวลา"]:
                cleaned_text = cleaned_text.replace(keyword, "")
            reminder_text = cleaned_text.strip()

            return {
                "type": "reminder",
                "reminder_text": reminder_text,
                "reminder_time": parsed_time.isoformat(),
                "raw_text": text
            }

        # ไม่พบรูปแบบเวลาใด ๆ
        print("❌ ไม่พบเวลาในคำสั่ง")
        return None


    def parse_command_to_ha_json(self, text):
        text = text.lower().strip()
        print(f"input={text}")
        result = {
            "type": None,
            "action": None,
            "device": None,
            "entity_id": None,
            "location": None,
            "extra": None
        }

        # 1. ตรวจจับ action
        for a in self.action_keywords.keys():
            if a in text:
                result["action"] = a
                result["type"] = "unknow_entity"
                break

        if not result["action"]:
            print("❌ ไม่พบ action ที่รู้จัก")
            return result

        # 2. ตรวจ device/location/entity
        for device_key, locations in ENTITY_MAP.items():
            if device_key in text:
                result["device"] = device_key
                for location_key, entity in locations.items():
                    if location_key in text:
                        result["location"] = location_key
                        if isinstance(entity, dict):
                            for sub_key, sub_entity in entity.items():
                                if sub_key != "_default" and sub_key in text:
                                    result.update({
                                        "type": "home_assistant_command",
                                        "entity_id": sub_entity,
                                        "extra": sub_key
                                    })
                                    return result
                            if "_default" in entity:
                                result.update({
                                    "type": "home_assistant_command",
                                    "entity_id": entity["_default"]
                                })
                                return result
                        else:
                            result.update({
                                "type": "home_assistant_command",
                                "entity_id": entity
                            })
                            return result
        return result

    def detect_command(self, text):

        command = self.parse_reminder(text)
        if (command is not None):
            if command['type'] is not None:
                return command
           
        command = self.parse_command_to_ha_json(text)        

        return command
