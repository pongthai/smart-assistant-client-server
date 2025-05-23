# assistant/search_manager.py (refactored with context builder integration)

import requests
from bs4 import BeautifulSoup
from config import SERPER_API_KEY
from logger_config import get_logger
from search_to_context_builder import SearchToContextBuilder

logger = get_logger(__name__)

class SearchManager:
    def __init__(self, gpt_client):
        logger.info("SearchManager initialized")
        self.serper_api_key = SERPER_API_KEY
        self.gpt_client = gpt_client
        self.context_builder = SearchToContextBuilder()

    def search_serper(self, query, top_k=5):
        logger.debug("Enter search_serper")
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": self.serper_api_key}
        payload = {"q": query, "hl": "th", "gl": "th", "num": top_k}

        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        results = data.get("organic", [])[:top_k]
        logger.debug("Exit search_serper")
        return results

    def should_fetch(self, link, snippet):
        if not snippet or len(snippet) < 80:
            return True
        whitelist = ["siamsport.co.th", "tmd.go.th", "bangkokbiznews.com"]
        return any(site in link for site in whitelist)

    def fetch_webpage_content(self, url):
        try:
            logger.debug("Enter fetch_webpage_content")
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs)
            logger.debug("Exit fetch_webpage_content")
            return text.strip()
        except Exception as e:
            logger.error(f"❌ Error fetching {url}: {e}")
            return ""

    def build_context_from_search_results(self, results):
        logger.debug("Enter build_context_from_search_results")
        context_parts = []

        for idx, item in enumerate(results, 1):
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            link = item.get('link', '')

            if not title and not snippet:
                continue

            page_content = ""
            context_entry = f"""
                {idx}. {title}:
                {snippet}
                Extracted Content: {page_content if page_content else 'N/A'}
                """.strip()

            context_parts.append(context_entry)

        logger.debug("Exit build_context_from_search_results")
        return "\n\n".join(context_parts).strip()

    def summarize_web_context(self, results, user_question):
        logger.debug("Enter summarize_web_context")
        context_str = results
        # context_str = self.build_context_from_search_results(results)

        # if not context_str:
        #     return ""

        # # ✨ New logic: apply structured extraction and scoring
        # logger.debug(f"context_str={context_str}")
        # structured = self.context_builder.extract_entities(context_str)
        # structured_context = self.context_builder.build_gpt_context(structured)
        
        # if structured_context:
        #     return structured_context

        # Fallback: let GPT summarize as before
        prompt = (
            f"คุณเป็นผู้ช่วยที่สามารถสรุปข้อมูลจากเว็บได้อย่างแม่นยำ\n"
            f"คำถาม: {user_question}\n"
            f"ข้อมูลล่าสุดที่พบ:\n{context_str[:3000]}\n"
            f"\nสรุปคำตอบให้กระชับภายใน 3-5 บรรทัด ถ้าไม่เจอข้อมูลให้บอกว่า 'ยังไม่พบข้อมูลล่าสุดจ้า'"
        )

        try:
            summary = self.gpt_client.chat_manager.ask_simple(prompt)
            return summary.strip() if summary else ""
        except Exception as e:
            logger.error(f"❌ Error summarizing context: {e}")
            return ""
