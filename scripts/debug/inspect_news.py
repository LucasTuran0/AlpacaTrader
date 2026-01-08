import os
from dotenv import load_dotenv
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest

load_dotenv("backend/.env")
client = NewsClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET"))
req = NewsRequest(symbols="TQQQ", limit=1)
news = client.get_news(req)
print(f"Type: {type(news)}")
print(f"Attributes: {dir(news)}")
try:
    print(f"News Sample: {news.news[0]}")
except Exception as e:
    print(f"Error accessing .news: {e}")
