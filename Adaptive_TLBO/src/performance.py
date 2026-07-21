import time


class Performance:

    def __init__(self):

        self.start_time = None
        self.end_time = None

        self.history = []

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    def execution_time(self):

        if self.start_time is None or self.end_time is None:
            return 0

        return self.end_time - self.start_time

    def add_history(self, iteration, fitness):

        self.history.append({
            "Iteration": iteration,
            "Fitness": fitness
        })

    def get_history(self):

        return self.history