import json
import asyncio
import time

class RateLimiter:
    def __init__(self, config_file="./config/ratelimit.config.json"):
        with open(config_file, "r", encoding="utf-8") as file:
            self.limits = json.load(file)

        self.limits = {
            key: {
                "max_calls": value[0],
                "interval": value[1],
                "calls": 0,
                "reset_time": time.time() + value[1]
            }
            for key, value in self.limits.items()
        }
        self.lock = asyncio.Lock()

    async def acquire(self, action):
        async with self.lock:
            limit_info = self.limits.get(action)
            if not limit_info:
                return

            now = time.time()
            if now >= limit_info["reset_time"]:
                limit_info["calls"] = 0
                limit_info["reset_time"] = now + limit_info["interval"]

            if limit_info["calls"] >= limit_info["max_calls"]:
                wait_time = limit_info["reset_time"] - now
                print(f"Rate limit reached for {action}. Waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)

            limit_info["calls"] += 1