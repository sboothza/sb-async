import asyncio
import multiprocessing
import random
import time

from src.sb_async.async_job import AsyncJob
from src.sb_async.async_queue import AsyncQueue
from src.sb_async.async_threadpool import AsyncThreadPool

class Worker(AsyncJob[float]):
    def __init__(self, item):
        super().__init__(None, item)

    def work(self):
        print(f"waiting: {self.item}")
        time.sleep(self.item)
        print(f"waited: {self.item}")

class Q(AsyncQueue[float]):
    def __init__(self, items):
        super().__init__()
        self.items = items

    async def push(self, item: float):
        self.items.append(item)

    async def _pop(self) -> AsyncJob[float] | None:
        if len(self.items) > 0:
            item = self.items.pop(0)
            return Worker(item)
        return None

    async def pop(self, timeout: float = 0) -> AsyncJob[float] | None:
        if timeout == 0:
            return await self._pop()
        else:
            return await asyncio.wait_for(self._pop(), timeout=timeout)

    def count(self) -> int:
        return len(self.items)

    def clear(self):
        self.items.clear()

async def main():
    r = random.Random()
    items = [r.randint(1, 10) for i in range(100)]
    q = Q(items)
    pool = AsyncThreadPool(5, q)

    # Create a task for the thread pool work
    task = asyncio.create_task(pool.work())

    # Wait for 10 seconds, then shutdown
    await asyncio.sleep(10)
    print("shutting down!!!!!")
    pool.shutdown()

    # Wait for the task to complete
    await task
    print("finished")

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn', force=True)
    asyncio.run(main())
