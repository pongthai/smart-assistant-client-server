# reminder_manager.py

import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict
import dateparser
from logger_config import get_logger

logger = get_logger(__name__)

class ReminderManager:
    def __init__(self, speak_callback):
        self.reminders: List[Dict] = []
        self.lock = threading.Lock()
        self.running = True
        self.speak_callback = speak_callback  # Function to call when reminder is triggered
        threading.Thread(target=self._reminder_loop, daemon=True).start()
    def parse_reminder_command(self,text):
        # ตัวอย่าง: "เตือนฉันอีก 3 นาทีให้ไปกินข้าว"
        m = re.search(r"เตือน(?:ฉัน)?อีก\s*(\d+)\s*(วินาที|นาที|ชั่วโมง)(?:ว่า|ให้)?(.+)", text)
        if not m:
            return None

        amount = int(m.group(1))
        unit = m.group(2)
        message = m.group(3).strip()

        delta = timedelta()
        if "วินาที" in unit:
            delta = timedelta(seconds=amount)
        elif "นาที" in unit:
            delta = timedelta(minutes=amount)
        elif "ชั่วโมง" in unit:
            delta = timedelta(hours=amount)

        trigger_time = datetime.now() + delta
        return (message, trigger_time)

    def add_reminder(self, text: str) -> bool:
        # Example: "เตือนฉันตอน 9 โมงเช้าให้กินยา"
        parsed_time = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
        if not parsed_time:
            logger.warning("Unable to parse time from: " + text)
            return False

        message = text  # For simplicity, we use the whole text for now
        with self.lock:
            self.reminders.append({"time": parsed_time, "message": message, "spoken": False})
        logger.info(f"Reminder added: {parsed_time} - {message}")
        return True

    def _reminder_loop(self):
        while self.running:
            now = datetime.now()
            with self.lock:
                for reminder in self.reminders:
                    if not reminder["spoken"] and reminder["time"] <= now:
                        logger.info(f"Triggering reminder: {reminder['message']}")
                        self.speak_callback(reminder["message"])
                        reminder["spoken"] = True
            time.sleep(10)  # check every 10 seconds

    def stop(self):
        self.running = False

    def list_reminders(self):
        with self.lock:
            return [r for r in self.reminders if not r["spoken"]]
