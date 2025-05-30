# entity_map_ha.py
from logger_config import get_logger

logger = get_logger(__name__)

ENTITY_MAP = {
    "ไฟ": {
        "ห้องนอน": {
            "หัวเตียง": "switch.bedroom_bedside",
            "ห้องน้ำ": "switch.bedroom_toilet",
            "เพดาน": "switch.bedroom_ceiling",
            "_default": "switch.bedroom_main"
        },
        "โต๊ะอาหาร": {
            "_default": "switch.switch_ota_aahaar_switch_1"
        },
        "หน้าบ้าน": {
            "_default": "switch.front_door_light"
        },
        "ห้องนั่งเล่น": {
            "_default": "switch.switch_h_ngrabaekhk_switch_3",
            "มุมทีวี": "switch.livingroom_tv_corner"
        },
        "โรงจอดรถ": {
            "_default": "switch.carpark_main",
            "หน้าประตู": "switch.carpark_infrontdoor"
        },
        "เครื่องทำน้ำแข็ง": {
            "_default": "switch.icemaker_machine_plug"
        }
    },
    "แอร์": {
        "ห้องนอน": {
            "_default": "climate.bedroom_ac"
        },
        "ห้องนั่งเล่น": {
            "_default": "climate.livingroom_ac"
        }
    },
    "ปลั๊ก": {
        "เครื่องทำน้ำแข็ง": {
            "_default": "switch.icemaker_machine_plug"
        }
    },
    "ทีวี": {
        "ห้องนั่งเล่น": {
            "_default": "media_player.livingroom_tv"
        }
    }
}

ACTION_KEYWORDS = {
    "turn_on": ["เปิด"],
    "turn_off": ["ปิด"],
    "increase": ["เพิ่ม", "เร่ง"],
    "decrease": ["ลด"]
}
# สร้าง reverse mapping จาก action_en → คำไทย
def get_action_th(ai_action):
    for en_action, th_keywords in ACTION_KEYWORDS.items():
        if en_action == ai_action and th_keywords:
            return th_keywords[0]  # ใช้คำแรกเป็นตัวแทน
    return ai_action  # fallback ถ้าไม่พบ

def parse_command_to_ha_json(text):
    text = text.lower().strip()
    logger.debug(f"parse_command_to_ha_json: {text}")
    result = {
        "type": None,
        "action": None,
        "device": None,
        "entity_id": None,
        "location": None,
        "extra": None
    }

    # 1. ตรวจจับ action
    for action, keywords in ACTION_KEYWORDS.items():
        if any(word in text for word in keywords):
            result["action"] = action
            result["type"] = "unknow_entity"
            break

    if not result["action"]:
        return result

    # 2. ตรวจจับอุปกรณ์ + ตำแหน่ง
    for device_key, locations in ENTITY_MAP.items():
        if device_key in text:
            result["device"] = device_key
            logger.debug(f"Found device: {device_key}")
            for location_key, entity in locations.items():
                if location_key in text:
                    result["location"] = location_key
                    logger.debug(f"Found location: {location_key}")
                                 
                    if isinstance(entity, dict):
                        for sub_key, sub_entity in entity.items():
                            if sub_key != "_default" and sub_key in text:
                                result.update({
                                    "type": "home_assistant_command",
                                    "entity_id": sub_entity,
                                    "extra": sub_key
                                })
                                return result
                        if "_default" in entity:
                            result.update({
                                "type": "home_assistant_command",
                                "entity_id": entity["_default"]
                            })
                            return result
                    else:
                        result.update({
                            "type": "home_assistant_command",
                            "entity_id": entity
                        })
                        return result
    return result