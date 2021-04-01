# -*- coding: utf-8 -*-
import asyncio


class AsyncForSecond:

    def __init__(self, timeout=0, interval=1, max_times=0):

        if timeout > 0:
            self._expire_time = asyncio.events.get_event_loop().time() + timeout
        else:
            self._expire_time = 0

        self._interval = interval
        self._max_times = max_times

        self._current = 0

    def __aiter__(self):

        return self

    async def __anext__(self):

        if self._current > 0:

            if (self._max_times > 0) and (self._max_times <= self._current):
                raise StopAsyncIteration()

            if (self._expire_time > 0) and (self._expire_time <= asyncio.events.get_event_loop().time()):
                raise StopAsyncIteration()

            await self._sleep()

        self._current += 1

        return self._current

    async def _sleep(self):

        await asyncio.sleep(self._interval)

