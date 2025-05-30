from datetime import datetime
from collections import defaultdict
import json
import os
from config import OPENAI_MODEL
from logger_config import get_logger

logger = get_logger(__name__)

class UsageTracker:
    def __init__(self, log_file="usage_log.json"):
        self.log_file = log_file

    def log_gpt_usage(self, prompt_tokens, completion_tokens, model=OPENAI_MODEL):
        total = prompt_tokens + completion_tokens
        self._write_log({
            "type": "gpt",
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total
        })

    def log_tts_usage(self, char_count, is_ssml=True):
        self._write_log({
            "type": "tts",
            "char_count": char_count,
            "is_ssml": is_ssml
        })

    def _write_log(self, entry):
        entry["timestamp"] = datetime.now().isoformat()
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.debug(f"📊 GPT Usage Logged: {entry}")

    def summarize(self, by="day"):
        if not os.path.exists(self.log_file):
            return {}

        with open(self.log_file) as f:
            logs = [json.loads(line) for line in f]

        summary = defaultdict(lambda: {"gpt_tokens": 0, "tts_chars": 0})
        for entry in logs:
            ts = datetime.fromisoformat(entry["timestamp"])
            if by == "day":
                key = ts.strftime("%Y-%m-%d")
            elif by == "week":
                key = f"{ts.year}-W{ts.isocalendar().week}"
            elif by == "month":
                key = ts.strftime("%Y-%m")
            else:
                continue

            if entry["type"] == "gpt":
                summary[key]["gpt_tokens"] += entry.get("total_tokens", 0)
            elif entry["type"] == "tts":
                summary[key]["tts_chars"] += entry.get("char_count", 0)

        return dict(summary)