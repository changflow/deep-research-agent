import requests
import os
import json

# Configuration from .env
API_KEY = "sk-806d2e03d2524be2bc162e58afa969b4"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def test_chat_completion():
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "qwen3-vl-plus",
        "messages": [
            {"role": "user", "content": "Hello, simply reply with 'API is working'."}
        ]
    }
    
    print(f"Testing API connection to: {url}")
    print(f"Using Model: {data['model']}")
    print(f"Key prefix: {API_KEY[:5]}...")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        try:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print("Response Text:")
            print(response.text)
            
        if response.status_code == 200:
            print("SUCCESS: API call worked!")
        else:
            print("FAILURE: API call returned non-200 status.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_chat_completion()
