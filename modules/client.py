from twikit import Client, errors
from datetime import datetime, timezone

from modules.logger import logger
from modules.utils import captcha_solver
from modules.rate_limiter import RateLimiter


class TwitterClient:
    """
    Twitter client for interacting with Twitter's API via Twikit.

    Handles authentication, fetching tweets, and manages rate limits.
    """

    def __init__(self, account):
        """
        Initializes the Twitter client.

        @param {dict} account - The account details for authentication.
        """
        self._account = account
        self._client = Client(
            language='en-US',
            proxy=account.get('proxy'),
            captcha_solver=captcha_solver
        )
        self.limiter = RateLimiter()
        self.is_busy = False
        self.is_rate_limited = False
        self.is_logged_in = False

    async def start(self):
        """
        Logs into Twitter using the provided account credentials.

        @returns {None}
        """
        try:
            await self._client.login(
                auth_info_1=self._account.get("auth_info_1"),
                auth_info_2=self._account.get("auth_info_2"),
                password=self._account.get("password"),
                cookies_file=self._account.get("cookies_file"),
                totp_secret=self._account.get("totp_secret")
            )
            self.is_logged_in = True
            logger.info(f'[Client] Logged in: {self._account.get("auth_info_1")}')
        except Exception as e:
            self.is_logged_in = False
            self.handle_exception(e, "login")

    def clean_json(self, obj):
        """
        Recursively cleans an object to ensure it is JSON-compatible.

        @param {any} obj - The object to clean.
        @returns {any} - A JSON-safe version of the object.
        """
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, dict):
            return {k: self.clean_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.clean_json(item) for item in obj] 
        return None 
    
    def userCreator(self, user):
        return {
            "user_id": user.id,
            "username": user.screen_name,
            "display_name": user.name,
            "created_at": int(datetime.strptime(user.created_at, "%a %b %d %H:%M:%S %z %Y").timestamp() * 1000),
            "profile_image": user.profile_image_url,
            "followers_count": user.followers_count,
            "verified": user.verified,
            "description": user.description,
            "website": user.url
        }
        
    def tweetCreator(self, tweet):
        return {
            "id": tweet.id,
            "created_at": int(datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y").timestamp() * 1000),
            "text": tweet.text,
            "author": self.userCreator(tweet.user),
            "engagement": {
                "views": getattr(tweet, "views", None),
                "likes": tweet.favorite_count,
                "retweets": tweet.retweet_count,
                "replies": tweet.reply_count,
                "quotes": tweet.quote_count
            },
            "hashtags": tweet.hashtags,
            "media": [
                {"id": media.id, "type": media.type, "url": media.media_url, "display_url": media.display_url}
                for media in tweet.media
            ],
            "is_editable": getattr(tweet, "edit_control", None) and tweet.edit_control.is_edit_eligible,
            "edits_remaining": getattr(tweet, "edit_control", None) and tweet.edit_control.edits_remaining,
            "url": f"https://x.com/{tweet.user.screen_name}/status/{tweet.id}"
        }

    async def get_user_tweets(self, username, tweet_type, cursor=None):
        """
        Fetches tweets of a given user.

        @param {string} username - The Twitter username.
        @param {string} tweet_type - The type of tweets to retrieve (e.g., "tweets", "replies").
        @param {string} [cursor] - Cursor for pagination.

        @returns {dict} - A dictionary containing tweets, pagination info, and a success status.
        """
        if self.is_busy or self.is_rate_limited:
            return {"success": False, "error": "Client is busy or rate limited"}

        self.is_busy = True
        action_key = f"get_user_tweets[tweet_type={tweet_type}]"

        try:
            await self.limiter.acquire(action_key)
            user = await self._client.get_user_by_screen_name(username)

            

            _tweets = await self._client.get_user_tweets(
                user_id=user.id, 
                tweet_type=tweet_type,
                count=40,
                cursor=cursor
            )
            
            tweets = [
                self.tweetCreator(tweet)
                for tweet in _tweets
            ]

            return {
                "success": True,
                "data": {
                    "previous": _tweets.previous_cursor,
                    "tweets": tweets,
                    "next": _tweets.next_cursor
                }
            }

        except Exception as e:
            return self.handle_exception(e, "fetching tweets")
        finally:
            self.is_busy = False

    def handle_exception(self, e, context=""):
        """
        Handles exceptions and maps them to meaningful error messages.

        @param {Exception} e - The exception to handle.
        @param {string} [context=""] - The context in which the error occurred.

        @returns {dict} - A dictionary containing a success flag and an error message.
        """
        error_mapping = {
            errors.Unauthorized: ("Unauthorized: Invalid credentials", "error"),
            errors.AccountSuspended: ("Account suspended. Login not possible.", "error"),
            errors.AccountLocked: ("Account locked. Requires manual action.", "error"),
            errors.BadRequest: ("Bad Request: Invalid parameters.", "error"),
            errors.TooManyRequests: ("Rate limit exceeded. Try again later.", "warning"),
            errors.ServerError: ("Twitter server error. Try again later.", "error"),
            errors.UserNotFound: ("User not found.", "warning"),
            errors.UserUnavailable: ("User unavailable.", "warning"),
            errors.TweetNotAvailable: ("Tweet not available.", "warning"),
            errors.Forbidden: ("Access denied. You may not have permission.", "error"),
        }

        for error_type, (message, level) in error_mapping.items():
            if isinstance(e, error_type):
                log_func = getattr(logger, level)
                log_func(f"[Client] {message} Context: {context}")
                return {"success": False, "error": message}

        # If the exception is not mapped, log as an unexpected error.
        logger.error(f"[Client] Unexpected error in {context}: {e}")
        return {"success": False, "error": "Unexpected error occurred"}
