# assistant/search_manager.py (refactored with context builder integration)

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from config import SERPER_API_KEY
from logger_config import get_logger
from langdetect import detect
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed
from latency_logger import LatencyLogger
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


from .search_to_context_builder import SearchToContextBuilder

logger = get_logger(__name__)

import re
from datetime import datetime, timedelta
from typing import List, Union

# Mapping of Thai months to month numbers
THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3,
    "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9,
    "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3,
    "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9,
    "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12
}


class SearchManager:
    def __init__(self, gpt_client):
        logger.info("SearchManager initialized")
        self.serper_api_key = SERPER_API_KEY
        self.gpt_client = gpt_client
        self.context_builder = SearchToContextBuilder()

    import re

    def normalize_thai_date(self,text: str) -> str:
        if not isinstance(text, str):
            return text

        thai_months = {
            "ม.ค.": "01", "ก.พ.": "02", "มี.ค.": "03", "เม.ย.": "04",
            "พ.ค.": "05", "มิ.ย.": "06", "ก.ค.": "07", "ส.ค.": "08",
            "ก.ย.": "09", "ต.ค.": "10", "พ.ย.": "11", "ธ.ค.": "12",
            "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03", "เมษายน": "04",
            "พฤษภาคม": "05", "มิถุนายน": "06", "กรกฎาคม": "07", "สิงหาคม": "08",
            "กันยายน": "09", "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12"
        }

        pattern = r"(\d{1,2})\s?(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s(\d{4})"

        def replace_date(match):
            day, month_th, year = match.groups()
            month = thai_months.get(month_th)
            if not month:
                return match.group(0)  # ไม่สามารถแปลงได้
            try:
                year = int(year)
                if year > 2500:
                    year -= 543
                iso = f"{year:04d}-{month}-{int(day):02d}"
                return iso
            except:
                return match.group(0)

        return re.sub(pattern, replace_date, text)

    def detect_language(self, text):
        try:
            return detect(text)
        except:
            return 'th'  # default fallback

    def translate_for_search(self,query: str, target_lang: str = "en") -> str:
        """
        Detects the language of the input query.
        If the query is in Thai and the target_lang is English, translate it.
        Otherwise, return the original query.
        """
        try:
            detected_lang = detect(query)
            if detected_lang == "th" and target_lang == "en":
                translated = GoogleTranslator(source='th', target='en').translate(query)
                return translated
            else:
                return query
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return query
    
    def search_dual_language(self, query, top_k=5):
        lang = self.detect_language(query)

        # Primary: Original language
        if lang == 'en':
            results_primary = self.search_serper(query, top_k=top_k, lang_code='en')
        else:
            results_primary = self.search_serper(query, top_k=top_k, lang_code='th')
            results_secondary = self.search_serper(self.translate_for_search(query), top_k=top_k, lang_code="en")


        # # Secondary: Parallel search in other language
        # alt_lang = 'th' if lang == 'en' else 'en'
        # results_secondary = self.search_serper(query, top_k=top_k, lang_code=alt_lang)

        # Combine & de-duplicate by URL
        seen = set()
        combined = []
        for item in results_primary + results_secondary:
            url = item.get("link")
            if url and url not in seen:
                seen.add(url)
                combined.append(item)

        return combined[:top_k * 2]  # return up to 2x top_k entries


    def search_serper(self, query, top_k=5, lang_code="th"):
        #logger.debug(f"Enter search_serper : query = {query} : top_k={top_k}")
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": self.serper_api_key}
        payload = {"q": query, "hl": lang_code, "gl": lang_code, "num": top_k}

        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        results = data.get("organic", [])[:top_k]
        # logger.debug("calling normalize_thai_date")
        # for item in results:
        #     original_snippet = item.get("snippet", "")
        #     normalized_snippet = self.normalize_thai_date(original_snippet)
        #     item["snippet"] = normalized_snippet  # 🔁 แทนที่ snippet เดิมด้วยข้อความที่ normalize แล้ว

        # logger.debug("Exit search_serper")
        return results

    def should_fetch(self, link, snippet):
        if not snippet or len(snippet) < 80:
            return True
        whitelist = ["siamsport.co.th", "tmd.go.th", "bangkokbiznews.com"]
        return any(site in link for site in whitelist)

    def fetch_with_requests(self, url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")

            print(f"\n✅ Successfully fetched: {url}\n")
            print("=" * 80)
            print(html_content[:3000])
            print("=" * 80)
            print("📌 Page Title:", soup.title.string if soup.title else "N/A")

            return html_content, soup

        except requests.exceptions.RequestException as e:
            print(f"\n❌ Failed to fetch {url}")
            print("   Reason:", str(e))
            return None, None

    def fetch_with_playwright(self, url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        }
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=15000)
                page.wait_for_load_state("networkidle")
                html_content = page.content()
                soup = BeautifulSoup(html_content, "html.parser")

                print(f"\n✅ Successfully rendered with Playwright: {url}\n")
                print("=" * 80)
                print(html_content[:3000])
                print("=" * 80)
                print("📌 Page Title:", soup.title.string if soup.title else "N/A")

                browser.close()
                return html_content, soup

        except Exception as e:
            print(f"\n❌ Failed to render {url} with Playwright")
            print("   Reason:", str(e))
            return None, None

    def fetch_webpage_content(self, url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        }
        try:
            logger.debug("Enter fetch_webpage_content")
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs)
            logger.debug("Exit fetch_webpage_content")
            return text.strip()
        except Exception as e:
            logger.error(f"â Error fetching {url}: {e}")
            return ""



    def fetch_all_webpages(self, urls, max_workers=5):
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.fetch_webpage_content, url): url for url in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                results[url] = future.result()
        return results
    
    def build_context_from_search_results(self, search_results, enable_fetch=True):
        logger.debug("Enter build_context_from_search_results")
        context_parts = []

        urls = [item.get('link') for item in search_results if item.get('link')] if enable_fetch else []
        webpage_contents = self.fetch_all_webpages(urls) if enable_fetch else {}

        for idx, item in enumerate(search_results, 1):
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            link = item.get('link', '')
            page_content = webpage_contents.get(link, '') if enable_fetch else ''

            if page_content:
                page_content = page_content.split("\n")[0][:500]

            context_entry = f"""
                {idx}. {title}:
                {snippet}
                Extracted Content: {page_content if page_content else 'N/A'}
                """.strip()

            context_parts.append(context_entry)

        logger.debug("Exit build_context_from_search_results")
        return "\n\n".join(context_parts).strip()

    def build_context_from_search_results_org(self, results):
        logger.debug("Enter build_context_from_search_results")
        context = ""
        for idx, item in enumerate(results, 1):
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("link", "")

            content = self.fetch_webpage_content(url)
            if not content:
                content = snippet

            context += f"{idx}. {title}\n{content[:1000]}\n\n"
        logger.debug(f"context={context}")
        return context.strip()
    
    def summarize_web_context(self, context_str, user_question):
        logger.debug("Enter summarize_web_context")        
        logger.debug(f"context_str={context_str}")
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
        #print(f"context_str={context_str[:3000]}")
        today_th = datetime.today().strftime("%-d %B %Y")  # เช่น '23 May 2025'

        prompt = (
            f"คุณเป็นผู้ช่วยที่สามารถสรุปข้อมูลจากเว็บได้อย่างแม่นยำ และเข้าใจภาษาไทยอย่างลึกซึ้ง\n"
            f"วันนี้คือวันที่ {today_th} กรุณาใช้บริบทนี้ประกอบการตีความคำว่า 'วันนี้' หรือ 'ล่าสุด'\n\n"
            f"คำถามของผู้ใช้:\n{user_question}\n\n"
            f"ข้อมูลที่ได้จากเว็บ (บางส่วน):\n{context_str[:3000]}\n\n"
            f"กรุณาสรุปคำตอบแบบกระชับ ชัดเจน ภายใน 3-5 บรรทัด\n"
            f"- ถ้ามีข้อมูลที่เกี่ยวข้อง ให้ตอบโดยอ้างอิงอย่างมั่นใจ\n"
            f"- ถ้าไม่เจอข้อมูล ให้ตอบว่า 'ยังไม่พบข้อมูลล่าสุดจ้า'\n"
            f"- ห้ามคาดเดาเกินจริงหรือพูดคลุมเครือ"
        )


        try:
            summary = self.gpt_client.chat_manager.ask_simple(prompt)
            print(f"summarized = {summary}")
            return summary.strip() if summary else ""
        except Exception as e:
            logger.error(f"❌ Error summarizing context: {e}")
            return ""
