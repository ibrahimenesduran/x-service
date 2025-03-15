from twikit import Client, errors
from modules.logger import logger
from modules.utils import captcha_solver
from modules.rate_limiter import RateLimiter

class TwitterClient:
    def __init__(self, account):
        self._account = account
        self._client = Client(
            language='en-US',
            proxy=account.get('proxy'),
            captcha_solver=captcha_solver
        )
        self.limiter = RateLimiter()
        self.is_busy = False
        self.is_rate_limited = False

    async def start(self):
        await self._client.login(
            auth_info_1=self._account.get("auth_info_1"),
            auth_info_2=self._account.get("auth_info_2"),
            password=self._account.get("password"),
            cookies_file=self._account.get("cookies_file"),
            totp_secret=self._account.get("totp_secret")
        )
        logger.info(f'[Client] Logged in: {self._account.get("auth_info_1")}')

    def clean_json(self, obj):
        """ Yalnızca JSON uyumlu verileri döndürür. """
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, dict):
            return {k: self.clean_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.clean_json(item) for item in obj] 
        return None 

    async def get_user_tweets(self, username, tweet_type, cursor=None):
        if self.is_busy or self.is_rate_limited:
            return None

        self.is_busy = True
        action_key = f"get_user_tweets[tweet_type={tweet_type}]"
        try:
            await self.limiter.acquire(action_key)  
            user = await self._client.get_user_by_screen_name(username)
            
            author = {
                "user_id": user.id,
                "username": user.screen_name,
                "display_name": user.name,
                "created_at": user.created_at,
                "profile_image": user.profile_image_url,
                "followers_count": user.followers_count,
                "verified": user.verified,
                "description": user.description,
                "website": user.url
            }

            _tweets = await self._client.get_user_tweets(
                user_id=user.id, 
                tweet_type=tweet_type,
                count=40,
                cursor=cursor
            )

            tweets = []
            for tweet in _tweets:
                tweet_data = {
                    "id": tweet.id,
                    "created_at": tweet.created_at,
                    "text": tweet.text,
                    "author": author,
                    "engagement": {
                        "views": getattr(tweet, "views", None),
                        "likes": tweet.favorite_count,
                        "retweets": tweet.retweet_count,
                        "replies": tweet.reply_count,
                        "quotes": tweet.quote_count
                    },
                    "hashtags": tweet.hashtags,
                    "media": [{"id" : media.id, "type": media.type, "url": media.media_url, "display_url" : media.display_url} for media in tweet.media],
                    "is_editable": tweet.edit_control.is_edit_eligible if hasattr(tweet, "edit_control") else False,
                    "edits_remaining": tweet.edit_control.edits_remaining if hasattr(tweet, "edit_control") else 0,
                    "url": f"https://x.com/{user.screen_name}/status/{tweet.id}"
                }
                tweets.append(tweet_data)

            next_id = _tweets.next_cursor
            previous_id = _tweets.previous_cursor

            return {
                "success": True,
                "data": {
                    "previous": previous_id,
                    "tweets": tweets,
                    "next": next_id
                }
            }


        except Exception as e:
            logger.error(f"[Client] Error fetching tweets: {e}")
            return None
        finally:
            self.is_busy = False

