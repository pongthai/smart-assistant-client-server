

ENTITY_MAP2 = {
    ("ไฟ", "ห้องนั่งเล่น", "ซ้าย"): "switch.livingroom_light_1",
    ("ไฟ", "ห้องนั่งเล่น", "กลาง"): "switch.livingroom_light_2",
    ("ไฟ", "ห้องนั่งเล่น", None): "switch.livingroom_light_2",
    ("ไฟ", "ห้องนอน", None): "switch.livingroom_light_2",
    ("ไฟ", "หน้าบ้าน", None): "switch.livingroom_light_2",
    ("พัดลม", "ห้องนั่งเล่น", None): "switch.livingroom_fan",
    ("ปลั๊ก", "ห้องครัว", None): "switch.kitchen_plug"
}

# --- ENTITY_MAP แบบเต็มตัวอย่าง ---
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

# --- คำที่แสดงถึง action ---
ACTION_KEYWORDS = {
    "turn_on": ["เปิด"],
    "turn_off": ["ปิด"],
    "increase": ["เพิ่ม", "เร่ง"],
    "decrease": ["ลด"]
}

