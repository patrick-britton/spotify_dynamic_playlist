import time
from datetime import datetime

class ProgressTracker:
    def __init__(self):
        self.start_time = time.time()
        self.last_time = self.start_time
        self.call_count = 0

    def log(self, message):
        """
        Logs progress with timestamp and elapsed time information.

        Args:
            message (str): The message to display with the timing information
        """
        current_time = time.time()
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Calculate elapsed times
        elapsed_since_last = current_time - self.last_time
        elapsed_since_start = current_time - self.start_time

        # Update call count
        self.call_count += 1

        # Print the progress information
        if self.call_count == 1:
            print(f"[{current_datetime}] START: {message}")
        else:
            print(f"[{current_datetime}] +{elapsed_since_last:.2f}s (total: {elapsed_since_start:.2f}s): {message}")

        # Update last_time for the next call
        self.last_time = current_time

    def reset(self):
        """Resets the timer to start fresh"""
        self.__init__()
