# reminder_manager.py

import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict
import dateparser
from logger_config import get_logger
import audio_controller

logger = get_logger(__name__)

class ReminderManager:
    def __init__(self, audio_controller):
        self.reminders: List[Dict] = []
        self.lock = threading.Lock()
        self.running = True
        self.audio_controller = audio_controller    
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

    def add_reminder(self, reminder_data: str) -> bool:
        # Example: "เตือนฉันตอน 9 โมงเช้าให้กินยา"
        reminder_time = datetime.fromisoformat(reminder_data["reminder_time"])

        reminder_text = reminder_data["reminder_text"]
        now = datetime.now()

        if reminder_time <= now:                
            logger.warning("⏰ เวลาที่ระบุอยู่ในอดีต: %s", reminder_time)
            return

        delay = (reminder_time - now).total_seconds()
        logger.info("📌 ตั้งการเตือน: '%s' ที่ %s (อีก %.1f วินาที)", reminder_text, reminder_time, delay)
       
        with self.lock:
            self.reminders.append({"time": reminder_time, "message": reminder_text, "spoken": False})
        logger.info(f"Reminder added: {reminder_time} - {reminder_text}")
        return True

    def process_triggered_alarm(self,text):
        self.audio_controller.speak(text=text)     

    def _reminder_loop(self):
        while self.running:
            now = datetime.now()
            with self.lock:
                for reminder in self.reminders:
                    if not reminder["spoken"] and reminder["time"] <= now:
                        logger.info(f"Triggering reminder: {reminder['message']}")
                        self.process_triggered_alarm(reminder['message'])               
                        reminder["spoken"] = True
            time.sleep(10)  # check every 10 seconds

    def stop(self):
        self.running = False

    def list_reminders(self):
        with self.lock:
            return [r for r in self.reminders if not r["spoken"]]
