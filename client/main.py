# main.py

from assistant_manager import AssistantManager
import signal
import traceback
import threading
import sys

def dump_threads(signum, frame):
    print("\n🧵 === Thread Dump ===")
    for thread in threading.enumerate():
        print(f"\nThread: {thread.name} (id: {thread.ident})")
        stack = sys._current_frames().get(thread.ident)
        if stack:
            traceback.print_stack(stack)
    print("🧵 === End Dump ===")

signal.signal(signal.SIGUSR1, dump_threads)


if __name__ == "__main__":
    assistant_manager = AssistantManager()
    #assistant_manager.run()
    # ✅ รัน assistant ใน background thread
    import threading
    threading.Thread(target=assistant_manager.run, daemon=True).start()

    # ✅ รัน GUI loop ใน main thread (ปลอดภัยบน macOS)
    if hasattr(assistant_manager.audio_manager, "avatar") and assistant_manager.audio_manager.avatar:
        assistant_manager.audio_manager.avatar.run()
    

    