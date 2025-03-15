import asyncio
from modules.client import TwitterClient
from modules.logger import logger

class ClientManager:
    def __init__(self, accounts):
        self.clients = [TwitterClient(account) for account in accounts]
        self.lock = asyncio.Lock()

    async def start_all_clients(self):
        tasks = [client.start() for client in self.clients]
        await asyncio.gather(*tasks)
        logger.info("All Twitter clients started successfully.")

    async def get_user_tweets(self, username, tweet_type, cursor=None):
        async with self.lock:
            for client in self.clients:
                if not client.is_busy and not client.is_rate_limited:
                    return await client.get_user_tweets(username, tweet_type, cursor)

            logger.warning("All clients are busy or rate-limited. Waiting for an available client...")
            await asyncio.sleep(5)  # Bekleme süresi (isteğe bağlı artırılabilir)
            return await self.get_user_tweets(tweet_type)  # Yeniden deneme
