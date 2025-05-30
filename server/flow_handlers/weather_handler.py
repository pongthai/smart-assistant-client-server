

from logger_config import get_logger

logger = get_logger(__name__)

class WeatherHandler:
    def __init__(self, session):
        self.session = session

    def handle(self, user_input: str):
        import requests
        logger.info(f"[WeatherHandler] ⛅ Handling user input: {user_input}")

        # TODO: Replace with your actual OpenWeatherMap API key
        api_key = "YOUR_OPENWEATHERMAP_API_KEY"

        try:
            # Default to Bangkok if no city found in user input
            city = "Bangyai"
            if "เชียงใหม่" in user_input:
                city = "Chiang Mai"
            elif "ภูเก็ต" in user_input:
                city = "Phuket"
            elif "กรุงเทพ" in user_input:
                city = "Bangkok"

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=th"
            response = requests.get(url)
            data = response.json()

            logger.info(f"[WeatherHandler] 🌐 Weather API response: {data}")

            if response.status_code == 200:
                weather_desc = data["weather"][0]["description"]
                temp = data["main"]["temp"]
                humidity = data["main"]["humidity"]
                summary = f"สภาพอากาศที่ {city} ตอนนี้: {weather_desc}, อุณหภูมิ {temp}°C, ความชื้น {humidity}%"
                result = {"status": "complete", "message": summary}
            else:
                logger.warning(f"[WeatherHandler] ❌ Weather API error: {data}")
                result = {"status": "complete", "message": f"ขออภัย ไม่สามารถตรวจสอบอากาศที่ {city} ได้ในขณะนี้"}

        except Exception as e:
            logger.error(f"[WeatherHandler] ❌ Exception: {e}")
            result = {"status": "complete", "message": "เกิดข้อผิดพลาดระหว่างตรวจสอบสภาพอากาศ"}

        logger.info(f"[WeatherHandler] ✅ Result: {result}")
        return result