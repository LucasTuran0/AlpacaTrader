import os
from dotenv import load_dotenv
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest

load_dotenv("backend/.env")
client = NewsClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET"))
req = NewsRequest(symbols="TQQQ", limit=5)
news = client.get_news(req)
print(f"Data type: {type(news.data)}")
print(f"Keys: {news.data.keys() if isinstance(news.data, dict) else 'Not a dict'}")
if isinstance(news.data, dict) and news.data:
    first_key = list(news.data.keys())[0]
    print(f"First key content type: {type(news.data[first_key])}")
    print(f"First key content: {news.data[first_key]}")
elif isinstance(news.data, list) and news.data:
    print(f"List element 0 type: {type(news.data[0])}")
    print(f"List element 0: {news.data[0]}")
else:
    print(f"Raw data: {news.data}")
