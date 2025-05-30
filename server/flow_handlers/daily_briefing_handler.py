from logger_config import get_logger
from .news_handler import NewsHandler
from .weather_handler import WeatherHandler
from .stock_analysis_handler import StockAnalysisHandler

logger = get_logger(__name__)

class DailyBriefingHandler:
    def __init__(self, session):
        self.session = session

    def handle(self, user_input: str):
        logger.info(f"[DailyBriefingHandler] 📋 Handling user input: {user_input}")

        # Use actual handlers to fetch data
        news_result = NewsHandler(self.session).handle("ข่าวเด่นวันนี้")
        weather_result = WeatherHandler(self.session).handle("สภาพอากาศกรุงเทพ")
        stock_result = StockAnalysisHandler(self.session).handle("หุ้นที่น่าจับตา")

        news_summary = f"📌 ข่าวเด่น: {news_result.get('message', '')}"
        weather_summary = f"🌤 สภาพอากาศ: {weather_result.get('message', '')}"
        stock_summary = f"📈 หุ้นแนะนำ: {stock_result.get('message', '')}"

        full_message = (
            "สรุปรายงานประจำวันที่คุณร้องขอ:\n\n"
            f"{news_summary}\n"
            f"{weather_summary}\n"
            f"{stock_summary}"
        )

        result = {
            "status": "complete",
            "message": full_message
        }
        logger.info(f"[DailyBriefingHandler] ✅ Result: {result}")
        return result