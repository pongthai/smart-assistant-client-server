from command_detector import CommandDetector
from home_assistant_bridge import transform_command_for_ha, send_command_to_ha

HA_URL = "http://192.168.100.101:8123"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhOGViNmJlOWIyOGM0MDRlYWYyYTE2NjQzODcwNjgwOSIsImlhdCI6MTc0Njg4MTEwNSwiZXhwIjoyMDYyMjQxMTA1fQ.RINEIFA6EhRPYW_G5mXLL0-URazWVKcENG_07A4Jsnc"

if __name__ == "__main__":

    command_detector = CommandDetector()

    text = "ช่วยเตือนว่าต้องกินยาเวลา 5 โมง 15 นาที ได้มั๊ย"
    command = command_detector.detect_command(text)
    print(f"command = {command}")
    
    # ha_command_json = transform_command_for_ha(command)
    # print(f"ha_command_json = {ha_command_json}")

    # response = send_command_to_ha(ha_command_json,HA_URL,HA_TOKEN)
    
    # print(f"response = {response}")
    
    


    
