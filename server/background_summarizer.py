import threading
import time

from openai import OpenAI
from config import OPENAI_MODEL, OPENAI_API_KEY
from logger_config import get_logger

logger = get_logger(__name__)

class MemoryBackgroundSummarizer:
    def __init__(self, memory_manager, api_key=OPENAI_API_KEY, model=OPENAI_MODEL, interval_sec=30):
        logger.info("MemoryBackgroundSummarizer Initialized")
        self.memory_manager = memory_manager
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.interval_sec = interval_sec
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

    def test_check(self):
        logger.info("Enter test_check->start")
    def start(self):
        logger.info("Enter MemoryBackgroundSummarizer->start")
        if not self._thread.is_alive():
            logger.info("🚀 Memory summarizer started.")
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()
        logger.info("🛑 Memory summarizer stopped.")

    def run_once(self):
        logger.debug("Enter MemoryBackgroundSummarizer->run_once")
        unprocessed = self.memory_manager.get_unsummarized(limit=5)
        if not unprocessed:
            return

        logger.debug(f"unprocessed = {unprocessed}")
        # ✅ ใช้ dict access แทน index
        text = "\n".join(f"{row['role']}: {row['content']}" for row in reversed(unprocessed))

        prompt = (
            "คุณคือ AI ที่ช่วยสรุปบทสนทนาก่อนหน้าให้กระชับแต่คงสาระสำคัญไว้\n"
            "ต่อไปนี้คือบทสนทนา:\n"
            f"{text}\n"
            "\nสรุปประเด็นสำคัญในบทสนทนาให้กระชับไม่เกิน 5 บรรทัด"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "คุณคือ AI ช่วยสรุปข้อมูล"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
            )
            summary = response.choices[0].message.content.strip()
            self.memory_manager.add_summary(summary)
            # ✅ Mark the processed ones as summarized
            ids = [row["id"] for row in unprocessed]
            self.memory_manager.mark_as_summarized(ids)
            logger.debug(f"summary={summary}")
            logger.debug("📝 Memory summarized.")
        except Exception as e:
            logger.error(f"❌ Failed to summarize memory: {e}")
    
    def _run_loop(self):
        logger.debug("🔁 Loop started.")
        while not self._stop_event.is_set():
            logger.debug("💤 Waiting for next round...")
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"❌ Error: {e}")
            self._stop_event.wait(self.interval_sec)
        logger.debug("✅ Loop exited cleanly.")
    
class HistoryBackgroundSummarizer:
    def __init__(self, memory_manager, api_key=OPENAI_API_KEY, model=OPENAI_MODEL, interval_sec=60):
        logger.info("MemoryBackgroundSummarizer Initialized")
        self.memory_manager = memory_manager
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.interval_sec = interval_sec
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

    def start(self):
        if not self._thread.is_alive():
            logger.info("🚀 History summarizer started.")
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()
        logger.info("🛑 History summarizer stopped.")

    def _run_loop(self):
        logger.debug("🔁 Loop started.")
        while not self._stop_event.is_set():
            logger.debug("💤 Waiting for next round...")
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"❌ Error: {e}")
            self._stop_event.wait(self.interval_sec)
        logger.debug("✅ Loop exited cleanly.")

    def run_once(self):
        logger.debug("Enter HistoryBackgroundSummarizer->run_once")
        unprocessed = self.memory_manager.get_unsummarized_history(limit=5)
        if not unprocessed:
            return

        logger.debug(f"(HistoryBackgroundSummarizer) unprocessed = {unprocessed}")
        text = "\n".join(f"{role}: {content}" for role, content in reversed(unprocessed))

        prompt = (
            "คุณคือ AI ที่ช่วยสรุปบทสนทนาให้กระชับเข้าใจง่าย โดยคงประเด็นสำคัญไว้\n"
            "ต่อไปนี้คือบทสนทนา:\n"
            f"{text}\n"
            "\nช่วยสรุปบทสนทนานี้ให้สั้นไม่เกิน 5 บรรทัด"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "คุณคือผู้ช่วย AI"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
            )
            summary = response.choices[0].message.content.strip()
            self.memory_manager.add_history_summary(summary)
            # ✅ Mark the processed ones as summarized
            ids = [row["id"] for row in unprocessed]
            self.memory_manager.mark_as_summarized(ids)
            
            logger.debug(f"📝 History summarized. : {summary}")
        except Exception as e:
            logger.error(f"❌ Failed to summarize history: {e}")
