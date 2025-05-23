# search_to_context_builder.py (Hybrid Entity Extraction: Pattern + GPT)

from datetime import datetime
from typing import Optional, Dict, Any, List
import re
from dateutil.parser import parse
from openai import OpenAI
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import OPENAI_API_KEY

class SearchToContextBuilder:
    def __init__(self):
        self.today = datetime.today().strftime("%d %B %Y")
        self.exclusion_keywords = ["1 ปี", "ทั้งปี", "ทุกสนาม", "ฤดูกาล"]
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def contains_exclusion_keyword(self, text: str) -> bool:
        return any(kw in text for kw in self.exclusion_keywords)

    def extract_dates(self, text: str, max_results: int = 3) -> List[str]:
        results = []
        thai_to_eng_months = {
            "มกราคม": "January", "กุมภาพันธ์": "February", "มีนาคม": "March", "เมษายน": "April",
            "พฤษภาคม": "May", "มิถุนายน": "June", "กรกฎาคม": "July", "สิงหาคม": "August",
            "กันยายน": "September", "ตุลาคม": "October", "พฤศจิกายน": "November", "ธันวาคม": "December",
            "ม.ค.": "January", "ก.พ.": "February", "มี.ค.": "March", "เม.ย.": "April",
            "พ.ค.": "May", "มิ.ย.": "June", "ก.ค.": "July", "ส.ค.": "August",
            "ก.ย.": "September", "ต.ค.": "October", "พ.ย.": "November", "ธ.ค.": "December"
        }

        # แปลงเดือนให้ parser รู้จัก
        for match in re.findall(r"\d{1,2}\s+[^\s]+\s+\d{4}", text):
            if self.contains_exclusion_keyword(match):
                continue

            replaced = match
            for th, en in thai_to_eng_months.items():
                if th in replaced:
                    replaced = replaced.replace(th, en)
                    break

            try:
                parsed = parse(replaced, fuzzy=True, dayfirst=True)
                iso = parsed.strftime("%Y-%m-%d")
                results.append(iso)
                if len(results) >= max_results:
                    break
            except Exception as e:
                print(f"❌ Failed to parse date from phrase '{match}': {e}")

        return results

    def extract_with_pattern(self, text: str) -> Dict[str, Any]:
        result = {
            "detected_entities": [],
            "score": 0.0,
            "confidence_reason": ""
        }

        dates = self.extract_dates(text)
        if dates:
            for d in dates:
                result["detected_entities"].append({"type": "date", "value": d})
            result["score"] += 0.3
            result["confidence_reason"] += f"พบวันที่ที่แปลงได้: {', '.join(dates)}\n"

        known_keywords = ["ราคาทอง", "ฟอร์มูล่าวัน", "ข่าวล่าสุด", "PM2.5", "อากาศ"]
        for kw in known_keywords:
            if kw in text:
                result["detected_entities"].append({"type": "topic", "value": kw})
                result["score"] += 0.3
                result["confidence_reason"] += f"พบคีย์เวิร์ด '{kw}'\n"

        if any(domain in text.lower() for domain in ["trueid", "siamsport", "bangkokbiznews", "tmd.go.th"]):
            result["score"] += 0.4
            result["confidence_reason"] += "แหล่งข้อมูลมีความน่าเชื่อถือ\n"

        return result

    def infer_with_gpt(self, text: str) -> List[Dict[str, str]]:
        try:
            prompt = (
                f"Extract key entities from this text. Return a JSON list of objects like this:\n"
                f"[{{ \"type\": \"topic\", \"value\": \"ฟอร์มูล่าวัน\" }}]\n"
                f"Text:\n{text}"
            )
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = response.choices[0].message.content
            match = re.search(r"\[(.*?)\]", content, re.DOTALL)
            if match:
                json_text = "[" + match.group(1).strip() + "]"
                return eval(json_text)
        except Exception:
            pass
        return []

    def extract_entities(self, text: str) -> Dict[str, Any]:
        result = self.extract_with_pattern(text)

        gpt_entities = self.infer_with_gpt(text)
        if gpt_entities:
            for ent in gpt_entities:
                if ent not in result["detected_entities"]:
                    result["detected_entities"].append(ent)
            result["score"] += 0.2
            result["confidence_reason"] += "GPT ช่วยเพิ่ม entity จากเนื้อหา\n"

        result["raw_text"] = text
        result["score"] = min(result["score"], 1.0)
        return result

    def build_gpt_context(self, extracted: Dict[str, Any]) -> Optional[str]:
        if extracted["score"] < 0.5:
            print("⚠️ Context not used. Score too low:", extracted)
            return None
        else:
            print(f"score = {extracted['score']} , extracted={extracted}")

        context = "ข้อมูลจากเว็บที่สกัดได้:\n"
        for entity in extracted["detected_entities"]:
            context += f"- {entity['type']}: {entity['value']}\n"

        if "raw_text" in extracted:
            context += f"\nเนื้อหาบางส่วน:\n{extracted['raw_text'][:1000]}"

        context += "\nกรุณาใช้ข้อมูลนี้ในการตอบ และหลีกเลี่ยงการคาดเดาหากไม่มีข้อมูลเพียงพอ"
        return context