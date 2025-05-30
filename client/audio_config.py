# audio_config.py
import platform
import sounddevice as sd

def configure_audio_device():
    system_name = platform.system()
    node_name = platform.node()

    if system_name == "Linux":
        sd.default.device = (1, 2)  # input, output for Raspberry Pi
    elif system_name == "Darwin":
        sd.default.device = (3, 2)  # input, output for Mac
    else:
        print("⚠️ Unknown system. Please configure audio device manually.")

# Apply at import
configure_audio_device()

