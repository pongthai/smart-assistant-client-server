from .base_handler import BaseIntentHandler
from .entity_map_ha import parse_command_to_ha_json, get_action_th
from logger_config import get_logger
from ..home_assistant_bridge import send_command_to_ha, transform_command_for_ha
from config import HA_URL, HA_TOKEN

logger = get_logger(__name__)


class CommandHandler(BaseIntentHandler):
    def __init__(self, session):
        super().__init__(session=session)
        self.pending_command = None    

    def handle(self, user_input):
        # Check current state from session
        current_state = self.session.state
        logger.debug(f"current_state={current_state}")
        if current_state == "awaiting_confirmation" :
            confirmation_words = ["ใช่", "ใช่แล้ว","ตกลง", "โอเค", "ได้เลย", "yes"]
            cancellation_words = ["ไม่", "ไม่ใช่", "ยกเลิก", "หยุด","no"]
            lowered = user_input.lower()
            if lowered.strip() in confirmation_words:
                
                ha_command = self.context
                logger.debug(f"ha_command={ha_command}")
                if ha_command.get('type') == "home_assistant_command":
                    logger.info(f"Send command to Home Assistant : {ha_command}")
                    send_command_to_ha(ha_command, HA_URL, HA_TOKEN)
                
                return {
                    "status": "confirmed",
                    "reply": "ดำเนินการตามคำสั่งแล้วนะ",
                    "action": self.context.get("action"),
                    "next_state": "complete"
                }
            elif lowered.strip() in cancellation_words:
                return {
                    "status": "cancelled",
                    "reply": "ยกเลิกคำสั่งแล้วนะ",
                    "action": self.context.get("action"),
                    "next_state": "complete"
                }
            else:
                return {
                    "status": "awaiting_confirmation",
                    "reply": "กรุณายืนยันว่าใช่หรือไม่",
                    "action": self.context.get("action"),
                    "next_state": "awaiting_confirmation"
                    
                }

        # Parse new command
        parsed = parse_command_to_ha_json(user_input)
        logger.debug(f"parsed={parsed}")
        if parsed["type"] != "home_assistant_command":
            return {
                "status": "incomplete",
                "reply": "ขออภัย ฉันไม่เข้าใจว่าคุณต้องการควบคุมอุปกรณ์ใด กรุณาระบุให้ชัดเจนขึ้นครับ",
                "action": self.context.get("action"),
                "next_state": "awaiting_entity_info"
            }
    
        action_th = get_action_th(parsed["action"])
        device = parsed.get('device', '')
        location = parsed.get('location', '')
        message = f"คุณต้องการให้ฉัน{action_th}{device}ที่{location}ใช่ไหม?"
        type = parsed.get('type', None)
        return {
            "status": "ready",
            "type": type,
            "action": parsed,
            "reply": message,
            "next_state": "awaiting_confirmation"
        }
