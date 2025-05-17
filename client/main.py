# main.py

from assistant_manager import AssistantManager

if __name__ == "__main__":
    assistant_manager = AssistantManager()
    #assistant_manager.run()
    # ✅ รัน assistant ใน background thread
    import threading
    threading.Thread(target=assistant_manager.run, daemon=True).start()

    # ✅ รัน GUI loop ใน main thread (ปลอดภัยบน macOS)
    if hasattr(assistant_manager.audio_manager, "avatar") and assistant_manager.audio_manager.avatar:
        assistant_manager.audio_manager.avatar.run()
    

    