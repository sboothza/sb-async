import asyncio
import multiprocessing
import os
import queue
import signal
import threading
from asyncio import Semaphore

from src.sb_async.async_queue import AsyncQueue

def _worker_process(job_queue, result_queue, worker_id):
    """Worker process that continuously processes jobs"""
    print(f"Worker process {worker_id} started")
    try:
        while True:
            try:
                # Get job from queue with timeout
                job = job_queue.get(timeout=1.0)
                if job is None:  # Shutdown signal
                    break
                
                # Process the job
                result = job.work()
                result_queue.put((worker_id, result, None))
                
            except queue.Empty:
                continue
            except Exception as e:
                result_queue.put((worker_id, None, e))
    except KeyboardInterrupt:
        pass
    finally:
        print(f"Worker process {worker_id} shutting down")

class AsyncThreadPool[T]:
    def __init__(self, max_workers: int, queue: AsyncQueue[T], timeout: float = 1.0):
        self.max_workers = max_workers
        self.queue = queue
        self.timeout = timeout
        self.semaphore = Semaphore(max_workers)
        self._shutdown = False
        self._tasks = []
        self._worker_processes = []
        self._process_lock = threading.Lock()
        
        # Inter-process communication
        self._job_queue = multiprocessing.Queue()
        self._result_queue = multiprocessing.Queue()
        
        # Start worker processes
        self._start_worker_processes()

    def _start_worker_processes(self):
        """Start the worker processes"""
        for i in range(self.max_workers):
            process = multiprocessing.Process(
                target=_worker_process,
                args=(self._job_queue, self._result_queue, i)
            )
            process.start()
            self._worker_processes.append(process)

    async def work(self):
        """Process all items in the queue"""
        self._tasks = [
            asyncio.create_task(self._worker())
            for _ in range(self.max_workers)
        ]
        
        # Wait for all tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _worker(self):
        """Worker coroutine that distributes jobs to worker processes"""
        while not self._shutdown:
            try:
                async with self.semaphore:
                    job = await asyncio.wait_for(self.queue.pop(self.timeout), timeout=self.timeout + 1.0)
                    if job is None:
                        break
                    
                    # Submit job to worker process pool
                    self._job_queue.put(job)
                    print(f"Job submitted to worker process pool")
                    
                    # Don't wait for result - let jobs run as long as they need
                    # The worker processes will handle the job execution
                            
            except asyncio.TimeoutError:
                if self._shutdown:
                    break
                print("Job timed out, continuing...")
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._shutdown:
                    break
                print(f"Error processing job: {e}")

    def shutdown(self):
        """Shutdown the process pool immediately"""
        self._shutdown = True
        
        # Cancel all async tasks immediately
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Send shutdown signals to all worker processes
        for _ in self._worker_processes:
            try:
                self._job_queue.put(None)  # Shutdown signal
            except:
                pass  # Queue might be full or closed
        
        # Forcefully kill all worker processes
        with self._process_lock:
            for process in self._worker_processes:
                try:
                    if process.is_alive():
                        print(f"Killing worker process {process.pid}")
                        os.kill(process.pid, signal.SIGTERM)
                        # Give it a moment to terminate gracefully
                        process.join(timeout=1.0)
                        if process.is_alive():
                            # Force kill if it didn't terminate
                            print(f"Force killing worker process {process.pid}")
                            os.kill(process.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    # Process already dead
                    pass
        
        print("shutdown complete")

    async def shutdown_async(self):
        """Async version of shutdown for proper cleanup"""
        self._shutdown = True
        
        # Cancel all async tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Send shutdown signals to all worker processes
        for _ in self._worker_processes:
            self._job_queue.put(None)  # Shutdown signal

        # Forcefully kill all worker processes
        with self._process_lock:
            for process in self._worker_processes:
                try:
                    if process.is_alive():
                        print(f"Killing worker process {process.pid}")
                        os.kill(process.pid, signal.SIGTERM)
                        # Give it a moment to terminate gracefully
                        process.join(timeout=2.0)
                        if process.is_alive():
                            # Force kill if it didn't terminate
                            print(f"Force killing worker process {process.pid}")
                            os.kill(process.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    # Process already dead
                    pass
            
        self._tasks = []
