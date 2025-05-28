from .base_handler import BaseIntentHandler
from .entity_map_ha import ENTITY_MAP, ACTION_KEYWORDS, parse_command_to_ha_json

class CommandHandler(BaseIntentHandler):
    def __init__(self, context=None):
        super().__init__(context)
    
    def handle(self, user_input):
        parsed = parse_command_to_ha_json(user_input)
        
        if parsed["type"] != "home_assistant_command":
            missing_parts = []
            if not parsed["device"]:
                missing_parts.append("อุปกรณ์")
            if not parsed["action"]:
                missing_parts.append("คำสั่ง")
            return {
                "status": "incomplete",
                "message": f"ขอข้อมูลเพิ่มเติม: กรุณาระบุ {'และ'.join(missing_parts)}",
                "next_state": "awaiting_entity_info"
            }

        # พร้อมเรียกใช้งาน
        action = parsed["action"]
        device = parsed["device"]
        location = parsed["location"]
        entity_id = parsed["entity_id"]

        msg = f"คุณต้องการให้ฉัน {action} {device}"
        if location:
            msg += f" ที่ {location}"
        msg += " ใช่ไหม?"

        return {
            "status": "ready",
            "action": {
                "type": "home_assistant_command",
                "entity_id": entity_id,
                "command": action
            },
            "message": msg,
            "next_state": "confirm_command"
        }