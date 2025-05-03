# --- Tuya Controller Module ---
# File: tuya_controller.py

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tuya_connector import TuyaOpenAPI
from config import TUYA_ACCESS_ID, TUYA_ACCESS_KEY, TUYA_API_ENDPOINT

import os

 

# Mapping between user command and Tuya device function code
device_map = {
    "โต๊ะอาหาร": {
        "device_id": "ebf8854d356650d8d0gcyb",
        "switch_code": "switch_1"
    },
    "ห้องนั่งเล่น 1": {
        "device_id": "eb9026d5f9d0aea048hvse",
        "switch_code": "switch_1"
    },
    "ห้องนั่งเล่น 2": {
        "device_id": "eb9026d5f9d0aea048hvse",
        "switch_code": "switch_2"
    },
    "หน้าบ้าน": {
        "device_id": "eb9026d5f9d0aea048hvse",
        "switch_code": "switch_3"
    },
    "ปลั๊กตู้ทำน้ำแข็ง": {
        "device_id": "eb0c423f747ee5ce924uh4",
        "switch_code": "switch_1"
    }

}

class TuyaController:
    def __init__(self):
        self.api = TuyaOpenAPI(TUYA_API_ENDPOINT, TUYA_ACCESS_ID, TUYA_ACCESS_KEY)
        self.api.connect()

    def turn_on(self, location):
        if location not in device_map:
            return f"ไม่รู้จักอุปกรณ์สำหรับ {location}"

        device = device_map[location]
        commands = [{"code": device["switch_code"], "value": True}]
        self.api.post(f"/v1.0/iot-03/devices/{device['device_id']}/commands", {"commands": commands})
        return f"เปิดไฟ {location} เรียบร้อยแล้วจ้า"

    def turn_off(self, location):
        if location not in device_map:
            return f"ไม่รู้จักอุปกรณ์สำหรับ {location}"

        device = device_map[location]
        commands = [{"code": device["switch_code"], "value": False}]
        self.api.post(f"/v1.0/iot-03/devices/{device['device_id']}/commands", {"commands": commands})
        return f"ปิดไฟ {location} แล้วน้า"

