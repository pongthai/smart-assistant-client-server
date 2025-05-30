# main.py

import signal
import traceback
import threading
import sys
from assistant_manager import AssistantManager
import time


def dump_threads(signum, frame):
    print("\n🧵 === Thread Dump ===")
    for thread in threading.enumerate():
        print(f"\nThread: {thread.name} (id: {thread.ident})")
        stack = sys._current_frames().get(thread.ident)
        if stack:
            traceback.print_stack(stack)
    print("🧵 === End Dump ===")


def main():    
    assistant_manager = AssistantManager()

    # Run assistant logic in a background thread
    threading.Thread(target=assistant_manager.run, daemon=True).start()

    # If an avatar is enabled, run its animation loop on the main thread
    avatar = getattr(assistant_manager.audio_controller, "avatar", None)
    if avatar:
        avatar.run()
    else:
        # Fallback: block main thread
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("? Exiting...")


if __name__ == "__main__":
    main()

