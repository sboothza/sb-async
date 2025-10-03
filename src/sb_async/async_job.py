class AsyncJob[T]:
    def __init__(self, state, item: T):
        self.state = state
        self.item = item

    def work(self):
        ...