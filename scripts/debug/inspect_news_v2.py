import os
from dotenv import load_dotenv
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest

load_dotenv("backend/.env")
client = NewsClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET"))
req = NewsRequest(symbols="TQQQ", limit=1)
news = client.get_news(req)
print(f"Data type: {type(news.data)}")
if len(news.data) > 0:
    first_item = news.data[0]
    print(f"Item type: {type(first_item)}")
    print(f"Item content: {first_item}")
    if hasattr(first_item, 'headline'):
        print(f"Headline: {first_item.headline}")
    elif isinstance(first_item, dict):
        print(f"Dict Headline: {first_item.get('headline')}")
else:
    print("No news found.")
