# client/audio_config.py

import sounddevice as sd

def find_device_id(name_keyword: str, is_input=False, is_output=False):
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        if name_keyword.lower() in dev['name'].lower():
            if is_input and dev['max_input_channels'] > 0:
                return idx
            if is_output and dev['max_output_channels'] > 0:
                return idx
    return None

# ???????? keyword ????????????????????
MIC_KEYWORD = "USB Audio"
SPEAKER_KEYWORD = "USB Audio"

mic_id = find_device_id(MIC_KEYWORD, is_input=True)
speaker_id = find_device_id(SPEAKER_KEYWORD, is_output=True)

if mic_id is None or speaker_id is None:
    raise RuntimeError("? ?????????????????????? ????????????????????????")

# ??????? default
sd.default.device = (mic_id, speaker_id)

print(f"? Audio devices set: mic_id={mic_id}, speaker_id={speaker_id}")

