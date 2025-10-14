import asyncio
import multiprocessing
import os
import signal
import threading
from asyncio import Semaphore
from typing import Optional

from .async_helpers import run_async_as_sync
from .async_queue import AsyncQueue
from .state import WorkerState

def _worker_process(queue:AsyncQueue, worker_id, shutdown_event, state: WorkerState):
    """Worker process that continuously processes jobs from AsyncQueue"""
    print(f"Worker process {worker_id} started")
    state.unwrap()
    queue.unwrap()
    try:
        while not shutdown_event.is_set():
            try:
                # Get job from AsyncQueue with timeout
                print("getting from queue")
                job = run_async_as_sync(queue.pop(timeout=5.0))
                if job is None:  # No more jobs
                    break

                # Process the job
                result = job.work(state)
                print(f"Job completed in worker {worker_id}")

            except Exception as e:
                print(f"Job failed in worker {worker_id}: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        print(f"Worker process {worker_id} shutting down")

class AsyncThreadPool[T]:
    def __init__(self, max_workers: int, queue: AsyncQueue[T], state: WorkerState, timeout: float = 1.0):
        self.max_workers = max_workers
        self.queue = queue
        self.timeout = timeout
        self.semaphore = Semaphore(max_workers)
        self._shutdown = False
        self._worker_processes: list[multiprocessing.Process] = []
        self._process_lock = threading.Lock()
        self.worker_state = state

        # Shutdown event for worker processes
        self._shutdown_event = multiprocessing.Event()

        # Start worker processes
        self._start_worker_processes()

    def _start_worker_processes(self):
        """Start the worker processes"""
        for i in range(self.max_workers):
            process = multiprocessing.Process(
                target=_worker_process,
                args=(self.queue, i, self._shutdown_event, self.worker_state)
            )
            process.start()
            self._worker_processes.append(process)

    async def work(self):
        """Process all items in the queue using worker processes"""
        # Worker processes will directly consume from the AsyncQueue
        # We just need to wait for them to complete or for shutdown
        while not self._shutdown:
            await asyncio.sleep(0.1)

            # Check if all worker processes are still alive
            alive_processes = [p for p in self._worker_processes if p.is_alive()]
            if not alive_processes:
                print("All worker processes have completed")
                break

    def shutdown(self):
        """Shutdown the process pool immediately"""
        self._shutdown = True

        # Signal all worker processes to shut down
        self._shutdown_event.set()

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

        # Signal all worker processes to shut down
        self._shutdown_event.set()

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
