import asyncio

from sb_async.async_job import AsyncJob

class AsyncQueue[T]:
    def __init__(self):
        ...

    def unwrap(self):
        ...

    async def push(self, item: T):
        ...

    async def _pop(self) -> AsyncJob[T] | None:
        ...

    async def pop(self, timeout: float = 0) -> AsyncJob[T] | None:
        if timeout == 0:
            return await self._pop()
        else:
            return await asyncio.wait_for(self._pop(), timeout=timeout)

    def count(self) -> int:
        ...

    def clear(self):
        ...
