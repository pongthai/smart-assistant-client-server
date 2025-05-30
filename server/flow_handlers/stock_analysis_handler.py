import yfinance as yf
from logger_config import get_logger

logger = get_logger(__name__)

class StockAnalysisHandler:
    def __init__(self, session):
        self.session = session

    def handle(self, user_input: str):
        logger.info(f"[StockAnalysisHandler] 📈 Handling user input: {user_input}")

        # พยายามดึงข้อมูลหุ้นจาก yfinance
        try:
            stock = yf.Ticker(user_input.upper())
            hist = stock.history(period="5d")

            if hist.empty:
                message = f"❌ ไม่พบข้อมูลหุ้นสำหรับ '{user_input}'"
            else:
                latest_close = hist["Close"].iloc[-1]
                change = hist["Close"].iloc[-1] - hist["Close"].iloc[-2]
                pct_change = (change / hist["Close"].iloc[-2]) * 100

                message = (
                    f"📊 หุ้น {user_input.upper()} ปิดล่าสุดที่ {latest_close:.2f} USD "
                    f"({change:+.2f}, {pct_change:+.2f}%) จากวันก่อนหน้า"
                )

        except Exception as e:
            logger.error(f"[StockAnalysisHandler] ⚠️ Error: {e}")
            message = f"เกิดข้อผิดพลาดในการดึงข้อมูลหุ้น: {str(e)}"

        result = {
            "status": "complete",
            "message": message
        }

        logger.info(f"[StockAnalysisHandler] ✅ Result: {result}")
        return result
