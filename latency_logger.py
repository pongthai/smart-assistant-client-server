import time

class LatencyLogger:
    def __init__(self):
        self.checkpoints = []
        self.start_time = time.perf_counter()

    def mark(self, label):
        now = time.perf_counter()
        elapsed = now - self.start_time
        self.checkpoints.append((label, elapsed))

    def report(self):
        print("📊 Latency Report:")
        for i in range(len(self.checkpoints)):
            label, elapsed = self.checkpoints[i]
            if i == 0:
                print(f"  {label}: {elapsed:.2f}s (from start)")
            else:
                _, prev_elapsed = self.checkpoints[i - 1]
                delta = elapsed - prev_elapsed
                print(f"  {label}: {delta:.2f}s (since previous)")
                