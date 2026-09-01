import asyncio
import time
from collections import defaultdict, deque
from typing import Dict

from . import config

# waiters: user_id -> Future awaiting next message text
waiters: Dict[int, asyncio.Future] = {}
# per-user lock to prevent overlapping wizards
locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
# rate limiter: user_id -> deque[timestamps]
attempts: Dict[int, deque] = defaultdict(deque)

def get_lock(user_id: int) -> asyncio.Lock:
    return locks[user_id]

def is_rate_limited(user_id: int) -> tuple[bool, int]:
    now = time.time()
    dq = attempts[user_id]
    # purge old
    while dq and now - dq[0] > config.RATE_LIMIT_WINDOW:
        dq.popleft()
    if len(dq) >= config.RATE_LIMIT_COUNT:
        retry_after = int(config.RATE_LIMIT_WINDOW - (now - dq[0]))
        return True, retry_after
    return False, 0

def record_attempt(user_id: int):
    attempts[user_id].append(time.time())

def set_waiter(user_id: int, fut: asyncio.Future):
    # cancel old if exists
    old = waiters.get(user_id)
    if old and not old.done():
        old.cancel()
    waiters[user_id] = fut

def pop_waiter(user_id: int):
    waiters.pop(user_id, None)

async def wait_for_text(user_id: int, timeout: int) -> str | None:
    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    set_waiter(user_id, fut)
    try:
        text = await asyncio.wait_for(fut, timeout=timeout)
        return text
    except asyncio.TimeoutError:
        return None
    except asyncio.CancelledError:
        return None
    finally:
        # caller pops on success; keep if timeout we clean
        if waiters.get(user_id) is fut:
            pop_waiter(user_id)

def fulfill_waiter(user_id: int, text: str) -> bool:
    fut = waiters.get(user_id)
    if fut and not fut.done():
        fut.set_result(text)
        # don't pop here; waiter will pop
        return True
    return False

def cancel_waiter(user_id: int):
    fut = waiters.get(user_id)
    if fut and not fut.done():
        fut.cancel()
    pop_waiter(user_id)
