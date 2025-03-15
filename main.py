import asyncio
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from modules.client_manager import ClientManager
from modules.logger import logger

app = FastAPI()

with open("./config/accounts.config.json", "r", encoding="utf-8") as file:
    accounts = json.load(file)

client_manager = ClientManager(accounts)

@app.on_event("startup")
async def startup_event():
    await client_manager.start_all_clients()

@app.get("/tweets/{username}/{tweet_type}")
async def get_tweets(username: str, tweet_type: str, cursor: str = Query(None)):
    try:
        result = await client_manager.get_user_tweets(username=username, tweet_type=tweet_type, cursor=cursor)
        return jsonable_encoder(result) 
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

