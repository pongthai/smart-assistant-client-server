# assistant/home_assistant_bridge.py

import requests

def transform_command_for_ha(command):
    action_map = {
        "เปิด": "turn_on",
        "ปิด": "turn_off",
        "เพิ่ม": "increase",
        "ลด": "decrease",
        "ตั้ง": "set"
    }

    action = action_map.get(command.get("action"))
    entity_id = command.get("entity_id")
    extra = command.get("extra", {})

    if not action or not entity_id:
        return None

    return {
        "action": action,
        "entity_id": entity_id,
        "extra": extra
    }

def send_command_to_ha(command_json, ha_url, ha_token):
    try:

        headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        }

        action = command_json["action"]
        entity_id = command_json["entity_id"]
        extra = command_json.get("extra", {})
        

        payload = {
            "entity_id": entity_id        
        }

        response = requests.post(f"{ha_url}/api/services/homeassistant/{action}", headers=headers, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error sending command to Home Assistant: {e}")
        return False

    