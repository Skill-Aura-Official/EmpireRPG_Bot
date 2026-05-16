import requests
import json

GEMINI_API_KEY = "AIzaSyCBiY-280_0pltlTiRvTDeX-vdDDMzpO0s"
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
headers = {'Content-Type': 'application/json'}
data = {
    "contents": [{"parts":[{"text": "Hello, how are you?"}]}]
}

response = requests.post(url, headers=headers, json=data)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
