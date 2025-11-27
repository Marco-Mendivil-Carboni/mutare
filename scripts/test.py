from dotenv import load_dotenv
import os
import requests

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

requests.get(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    params={
        "chat_id": CHAT_ID,
        "text": "Simulation finished!",
    },
)
