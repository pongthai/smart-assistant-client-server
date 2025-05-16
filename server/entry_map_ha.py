
ENTITY_MAP = {
    "ไฟห้องน้ำในห้องนอน": "light.bedroom_toilet",
    "ไฟหลักห้องนอน": "light.bedroom_main",
    "ปลั๊กตู้ทำน้ำแข็ง": "sswitch.vox_smart_wifi_adapter_socket_1",
    "ทีวีห้องนั่งเล่น": "media_player.living_room_tv",
    "ไฟโต๊ะอาหาร": "switch.switch_ota_aahaar_switch_1",
    "ไฟห้องนั่งเล่น": "switch.switch_h_ngrabaekhk_switch_3",
    "ไฟหน้าบ้าน": "switch.switch_h_ngrabaekhk_switch_1",
    "ไฟตู้ทำน้ำแข็ง": "switch.vox_smart_wifi_adapter_socket_1",
    "ปลั๊กเครื่องทำน้ำแข็ง": "switch.vox_smart_wifi_adapter_socket_1",
    "ไฟเครื่องทำน้ำแข็ง": "switch.vox_smart_wifi_adapter_socket_1",
    "แอร์ห้องนอน": "climate.bedroom_ac",
    "แอร์ห้องนั่งเล่น" : "climate.living_room_ac",
    "ไฟน้ำพุหน้าบ้าน" : "switch.swithchnmaaphu_hnaabaan_switch_1"
}
# --- Schema fields with title+const+description ---
domain_field_schema = {
    "anyOf": [
        {"type": "string", "title": "switch", "const": "switch", "description": "ใช้สำหรับอุปกรณ์เปิด/ปิด เช่น ปลั๊ก ไฟ"},
        {"type": "string", "title": "climate", "const": "climate", "description": "ใช้กับแอร์หรืออุปกรณ์ควบคุมอุณหภูมิ"},
        {"type": "string", "title": "media_player", "const": "media_player", "description": "ใช้กับทีวีหรือลำโพง"}
    ]
}

action_field_schema = {
    "anyOf": [
        {"type": "string", "title": "turn_on", "const": "turn_on", "description": "เปิดอุปกรณ์"},
        {"type": "string", "title": "turn_off", "const": "turn_off", "description": "ปิดอุปกรณ์"},
        {"type": "string", "title": "increase", "const": "increase", "description": "เพิ่มค่าคุณสมบัติ เช่น เพิ่มเสียงหรืออุณหภูมิ"},
        {"type": "string", "title": "decrease", "const": "decrease", "description": "ลดค่าคุณสมบัติ เช่น ลดเสียงหรืออุณหภูมิ"},
        {"type": "string", "title": "set", "const": "set", "description": "ตั้งค่าคุณสมบัติตามค่าที่กำหนด เช่น ตั้งอุณหภูมิหรือระดับเสียง"}
    ]
}

attribute_field_schema = {
    "anyOf": [
        {"type": "string", "title": "state", "const": "state", "description": "สถานะเปิด/ปิดของอุปกรณ์"},
        {"type": "string", "title": "temperature", "const": "temperature", "description": "อุณหภูมิของแอร์หรืออุปกรณ์ควบคุมสภาพอากาศ"},
        {"type": "string", "title": "volume_level", "const": "volume_level", "description": "ระดับเสียงของทีวีหรือลำโพง"},
        {"type": "string", "title": "brightness", "const": "brightness", "description": "ความสว่างของหลอดไฟ"}
    ]
}

control_device_function = {
    "name": "control_device",
    "description": "Control smart home devices.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": domain_field_schema,
            "action": action_field_schema,
            "attribute": attribute_field_schema,
            "device_name": {
                "type": "string",
                "enum": list(ENTITY_MAP.keys()),
                "description": "ชื่ออุปกรณ์ที่ต้องการควบคุม เช่น ไฟห้องนั่งเล่น"
            },
            "value": {
                "type": "number",
                "description": "ค่าที่ต้องการตั้ง เช่น อุณหภูมิหรือระดับเสียง"
            }
        },
        "required": ["domain", "device_name", "action"]
    }
}