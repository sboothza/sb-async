# Async Thread Pool Library

A high-performance, async-compatible thread pool implementation that uses processes for true parallelism and forceful job termination capabilities.

## Overview

This library provides an `AsyncThreadPool` class that manages a pool of worker processes to execute jobs asynchronously. Unlike traditional thread pools, this implementation uses separate processes to achieve true parallelism and allows for immediate termination of long-running jobs.

## Key Features

- ✅ **Process-based execution** - True parallelism without GIL limitations
- ✅ **Process reuse** - Efficient worker process pool that reuses processes for multiple jobs
- ✅ **Forceful termination** - Can kill long-running jobs immediately with `shutdown()`
- ✅ **No job timeouts** - Jobs can run for as long as needed (minutes, hours, etc.)
- ✅ **Fire-and-forget** - Jobs are submitted and processed in background without blocking
- ✅ **Process isolation** - Each job runs in its own process for safety
- ✅ **Clean shutdown** - No hanging threads or processes on exit
- ✅ **Async/await compatible** - Works seamlessly with asyncio

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd sb-async

# Install dependencies (if any)
pip install -r requirements.txt
```

## Quick Start

```python
import asyncio
from async_threadpool import AsyncThreadPool
from async_queue import AsyncQueue

# Create a queue and add some jobs
queue = AsyncQueue()
# ... add jobs to queue ...

# Create thread pool with 5 worker processes
pool = AsyncThreadPool(max_workers=5, queue=queue)

# Process all jobs
await pool.work()

# Shutdown when done (kills all running jobs immediately)
pool.shutdown()
```

## Architecture

### Components

- **AsyncThreadPool**: Main class that manages worker processes and job distribution
- **AsyncQueue**: Queue implementation for job management
- **AsyncJob**: Base class for jobs to be executed
- **Worker Processes**: Persistent processes that execute jobs

### Process Flow

```
Main Process
├── Job Queue (multiprocessing.Queue)
├── Result Queue (multiprocessing.Queue) 
└── Worker Processes (persistent)
    ├── Worker 0 (continuous loop)
    ├── Worker 1 (continuous loop)
    └── Worker N (continuous loop)
```

## Usage Examples

### Basic Usage

```python
import asyncio
from async_threadpool import AsyncThreadPool
from async_queue import AsyncQueue
from async_job import AsyncJob

class MyJob(AsyncJob[str]):
    def __init__(self, data):
        super().__init__(None, data)
    
    def work(self):
        print(f"Processing: {self.item}")
        # Your long-running work here
        time.sleep(5)
        print(f"Completed: {self.item}")

async def main():
    # Create queue and add jobs
    queue = AsyncQueue()
    for i in range(10):
        await queue.push(f"job-{i}")
    
    # Create and run thread pool
    pool = AsyncThreadPool(max_workers=3, queue=queue)
    await pool.work()

if __name__ == '__main__':
    asyncio.run(main())
```

### With Shutdown Control

```python
async def main():
    queue = AsyncQueue()
    # ... add jobs ...
    
    pool = AsyncThreadPool(max_workers=4, queue=queue)
    
    # Start processing in background
    task = asyncio.create_task(pool.work())
    
    # Do other work...
    await asyncio.sleep(10)
    
    # Shutdown after 10 seconds (kills all running jobs)
    print("Shutting down...")
    pool.shutdown()
    
    await task
    print("All done!")

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn', force=True)
    asyncio.run(main())
```

## API Reference

### AsyncThreadPool

```python
class AsyncThreadPool[T]:
    def __init__(self, max_workers: int, queue: AsyncQueue[T], timeout: float = 1.0):
        """Initialize thread pool with specified number of worker processes."""
    
    async def work(self):
        """Process all items in the queue using worker processes."""
    
    def shutdown(self):
        """Shutdown the thread pool immediately, killing all running jobs."""
    
    async def shutdown_async(self):
        """Async version of shutdown for proper cleanup."""
```

### AsyncQueue

```python
class AsyncQueue[T]:
    def __init__(self):
        """Initialize empty queue."""
    
    async def push(self, item: T):
        """Add item to queue."""
    
    async def pop(self, timeout: float = 0) -> AsyncJob[T] | None:
        """Remove and return item from queue."""
    
    def count(self) -> int:
        """Return number of items in queue."""
    
    def clear(self):
        """Remove all items from queue."""
```

### AsyncJob

```python
class AsyncJob[T]:
    def __init__(self, state, item: T):
        """Initialize job with state and data."""
    
    def work(self):
        """Execute the job. Override this method in subclasses."""
```

## Performance Characteristics

### Process vs Thread Trade-offs

**Advantages of Process-based Approach:**
- True parallelism (no GIL limitations)
- Process isolation (one crash doesn't affect others)
- Forceful termination capability
- Better for CPU-bound work

**Trade-offs:**
- Higher memory usage (~8-50MB per process)
- Process creation overhead (mitigated by process reuse)
- Data serialization overhead for IPC
- Higher context switching cost

### Performance Tips

1. **Process Reuse**: The library automatically reuses worker processes for efficiency
2. **Memory Management**: Monitor memory usage with many concurrent jobs
3. **Job Size**: Larger jobs benefit more from process isolation
4. **Shutdown Strategy**: Use `shutdown()` for immediate termination when needed

## Error Handling

The library handles various error conditions gracefully:

- **Process crashes**: Isolated to individual processes
- **Queue timeouts**: Configurable timeout for job retrieval
- **Shutdown signals**: Clean termination of all processes
- **Resource cleanup**: Automatic cleanup on shutdown

## Thread Safety

- **Process isolation**: Each job runs in its own process
- **Queue operations**: Thread-safe multiprocessing queues
- **Shutdown coordination**: Thread-safe shutdown mechanisms

## Requirements

- Python 3.12+
- No external dependencies (uses only standard library)

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Changelog

### v1.0.0
- Initial release
- Process-based thread pool implementation
- Forceful job termination capabilities
- Process reuse for efficiency
- Async/await compatibility