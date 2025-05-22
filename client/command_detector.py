import re
from slugify import slugify
from datetime import datetime
import difflib
from command_entity_map import ENTITY_MAP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import CONFIRMATION_KEYWORDS, CANCEL_KEYWORDS, ACTION_KEYWORDS
from thai_time_parser import parse_thai_time, extract_time_expression

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
        action = command.get("action", "")
        device = command.get("device", "")
        location = command.get("location", "")
        extra_str = self.format_extra(command.get("extra"))
        return f"คุณต้องการ{action}{device}{location}{extra_str} ใช่ไหม?"

    def find_closest(self, text, options):
        match = difflib.get_close_matches(text, options, n=1, cutoff=0.6)
        print(f"match = {match}")
        return match[0] if match else None

    def parse_reminder(self,text: str):
        print(f"check reminder command text={text}")

        # ✅ พยายามดึงเวลาออกมาก่อน
        time_part = extract_time_expression(text)
        print(f"time_part={time_part}")

        if time_part:
            try:
                parsed_time = parse_thai_time(time_part)
                # ✅ เอาเวลาออกจากข้อความ เพื่อเหลือแต่ reminder_text
                cleaned_text = text
                for keyword in ["เตือน", "แจ้งเตือน", "เวลา", "ตอน", time_part]:
                    cleaned_text = cleaned_text.replace(keyword, "")
                reminder_text = cleaned_text.strip()

                print(f"reminder_text={reminder_text}")
                print(f"parsed_time={parsed_time}")

                return {
                    "type": "reminder",
                    "reminder_text": reminder_text,
                    "reminder_time": parsed_time.isoformat(),
                    "raw_text": text
                }

            except Exception as e:
                print(f"❌ Failed to parse time: {e}")
                return None
        else:
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
        command = self.parse_command_to_ha_json(text)
        print(f"command={command}")
        if command['type'] is not None:
            return command

        command = self.parse_reminder(text)
        return command
