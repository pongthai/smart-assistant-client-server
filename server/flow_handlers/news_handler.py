import feedparser
from urllib.parse import quote
from logger_config import get_logger
from ..gpt_integration import GPTClient

logger = get_logger(__name__)

class NewsHandler:
    def __init__(self, session):
        self.session = session
        self.gpt_client = GPTClient()

    def handle(self, user_input: str):
        logger.info(f"[NewsHandler] 📰 Handling user input: {user_input}")

        query = quote(user_input)
        rss_sources = [
            f"https://news.google.com/rss/search?q={query}+when:1d&hl=th&gl=TH&ceid=TH:th",
            "https://www.thairath.co.th/rss/news",
            "https://www.bangkokbiznews.com/rss"
        ]

        headlines = []
        filtered_headlines = []
        keywords = user_input.lower().split()

        for url in rss_sources:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title.strip()
                headlines.append(title)
                if any(kw in title.lower() for kw in keywords):
                    filtered_headlines.append(title)

        top_headlines = filtered_headlines[:5] if filtered_headlines else headlines[:5]
        bulletized_headlines = "\n".join(f"- {h}" for h in top_headlines)

        prompt = (
            f"ต่อไปนี้คือหัวข้อข่าวที่เกี่ยวข้องกับ \"{user_input}\"\n\n"
            f"{bulletized_headlines}\n\n"
            f"กรุณาสรุปเนื้อหาโดยรวมเป็นภาษาไทย ในรูปแบบ:\n"
            f"- ...\n- ...\n- ...\n\nสรุปภาพรวม: ..."
        )

        try:
            summary_text = self.gpt_client.ask_raw(prompt)
            logger.info(f"[NewsHandler] summary_text: {summary_text}")
            result = {
                "status": "complete",
                "message": summary_text.strip(),
                "news_headlines": top_headlines
            }
        except Exception as e:
            logger.warning(f"[NewsHandler] ⚠️ GPT summarization failed: {e}")
            summary = "สรุปข่าวเด่น:\n" + bulletized_headlines
            result = {
                "status": "complete",
                "message": summary,
                "news_headlines": top_headlines
            }

        logger.info(f"[NewsHandler] ✅ Result: {result}")
        return result
