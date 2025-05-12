import openai
import time
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import OPENAI_API_KEY, OPENAI_MODEL, SYSTEM_TONE
from chat_manager import ChatManager
from memory_manager import MemoryManager
from search_manager import SearchManager

from logger_config import get_logger
from latency_logger import LatencyLogger

logger = get_logger(__name__)


class GPTClient:
    def __init__(self, api_key: str = None, model: str = OPENAI_MODEL):
        logger.info("GPTClient initialized")
        self.api_key = OPENAI_API_KEY
        self.model = model
        openai.api_key = self.api_key

        self.conversation_active = False
        self.previous_question = None
        self.last_interaction_time = time.time()

        self.chat_manager = ChatManager(SYSTEM_TONE)
        self.memory_manager = MemoryManager()
        self.search_manager = SearchManager()        

    def get_conversation_history(self, limit=5):
        memories = self.memory_manager.get_recent_memories(limit=limit)

        if not memories:
            return ""

        context = ""
        for role, summary in reversed(memories):
            context += f"{role.capitalize()}: {summary}\n"

        return context.strip()
    
    def ask(self, user_voice: str) -> str:
        
        try:
            # Analyze need (Web search / Memory / History)
            self.tracker = LatencyLogger()
            self.tracker.mark("analyze_question_all_in_one - start")
            analysis = self.chat_manager.analyze_question_all_in_one(
            current_question=user_voice,
            previous_question=self.previous_question
            )

            need_web = analysis.get("need_web_search", "No") == "Yes"
            need_memory = analysis.get("need_memory", "No") == "Yes"
            need_history = analysis.get("need_conversation_history", "No") == "Yes"

            logger.info(f"📊 Analysis: need_web={need_web}, need_memory={need_memory}, need_history={need_history}")
            self.tracker.mark("analyze_question_all_in_one - done")
            # Build context
            context_parts = []

            if need_web:
                self.tracker.mark("searching web - start")
                logger.info("🌐 Searching web.,")                
                search_results = self.search_manager.search_serper(user_voice, top_k=5)
                web_context = self.search_manager.build_context_from_search_results(search_results)
                context_parts.append(web_context)
                logger.info("S Searching web...done")
                self.tracker.mark("searching web - done")

            if need_memory:
                logger.info("🧠 Loading memory...")
                recent_memories = self.memory_manager.get_recent_memories(limit=5)
                memory_text = "\n".join([f"{role.capitalize()}: {summary}" for role, summary in reversed(recent_memories)])
                context_parts.append(memory_text)

            if need_history:
                logger.info("🗣️ Loading conversation history...")
                history_text = self.get_conversation_history(limit=5)
                context_parts.append(history_text)

            full_context = "\n\n".join(context_parts).strip()

            if not full_context:
                logger.info("🚀 No extra context needed.")

            # Ask GPT
            self.tracker.mark("asking chatGPT - start")
            logger.info("Asking ChatGPT..")
            answer = self.chat_manager.ask_gpt_with_context(user_voice, context=full_context)
            logger.info("ChatGPT: %s",answer) 
            self.tracker.mark("asking chatGPT - done")           
            self.last_interaction_time = time.time()

            # Save to memory
            self.memory_manager.add_message("user", user_voice)
            self.memory_manager.add_message("assistant", answer)
            self.tracker.report()
            # Update previous question
            self.previous_question = user_voice

            return answer   
        
        except Exception as e:
            print(f"❌ GPT Error: {e}")
            return "ขอโทษค่ะ เกิดข้อผิดพลาดในการประมวลผลคำถาม"

