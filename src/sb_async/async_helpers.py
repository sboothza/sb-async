import asyncio
import concurrent.futures

def run_async_as_sync(call):
    """
    Run an async function from a synchronous context.
    Returns the result of the async function.
    """
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, call)
            return future.result()
    except RuntimeError:
        return asyncio.run(call)

async def run_sync_as_async(call, *parameters):
    """
    Run a synchronous function in a thread pool executor from an async context.
    """
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, call, *parameters)
    except RuntimeError:
        raise RuntimeError("No running event loop found. This function must be called from an async context.")
