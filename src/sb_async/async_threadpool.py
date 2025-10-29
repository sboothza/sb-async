import asyncio
import concurrent.futures
from asyncio import Semaphore

from async_queue import AsyncQueue
from state import WorkerState

class AsyncThreadPool[T]:
    def __init__(self, max_workers: int, queue: AsyncQueue[T], state: WorkerState, timeout: float = 1.0):
        self.max_workers = max_workers
        self.queue = queue
        self.timeout = timeout
        self.semaphore = Semaphore(max_workers)
        self._shutdown = False
        self._tasks = []
        self.worker_state = state
        
        # Create asyncio executor (thread pool)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._futures = []  # Track running futures

    async def work(self):
        """Process all items in the queue using thread pool"""
        # Create async workers that consume from the queue
        self._tasks = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]
        
        # Wait for all tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _worker(self, worker_id: int):
        """Worker coroutine that processes jobs from the queue"""
        print(f"Worker {worker_id} started")
        try:
            while not self._shutdown:
                try:
                    async with self.semaphore:
                        # Get job from queue
                        job = await self.queue.pop(self.timeout)
                        if job is None:  # No more jobs
                            break
                        
                        print(f"Worker {worker_id} processing job")
                        
                        # Submit job to thread pool for execution
                        loop = asyncio.get_event_loop()
                        future = loop.run_in_executor(self._executor, job.work, self.worker_state)
                        self._futures.append(future)
                        
                        try:
                            # Wait for job completion
                            await future
                            print(f"Worker {worker_id} completed job")
                        except Exception as e:
                            print(f"Worker {worker_id} job failed: {e}")
                        finally:
                            # Remove future from tracking
                            if future in self._futures:
                                self._futures.remove(future)
                                
                except asyncio.TimeoutError:
                    if self._shutdown:
                        break
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self._shutdown:
                        break
                    print(f"Worker {worker_id} error: {e}")
                    
        finally:
            print(f"Worker {worker_id} shutting down")

    def shutdown(self):
        """Shutdown the thread pool"""
        self._shutdown = True
        
        # Cancel all async tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Shutdown executor (will wait for running tasks to complete)
        self._executor.shutdown(wait=False)
        
        print("shutdown complete")

    async def shutdown_async(self):
        """Async version of shutdown for proper cleanup"""
        self._shutdown = True
        
        # Cancel all async tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Shutdown executor
        self._executor.shutdown(wait=False)
