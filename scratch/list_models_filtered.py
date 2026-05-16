import requests

GEMINI_API_KEY = "AIzaSyCBiY-280_0pltlTiRvTDeX-vdDDMzpO0s"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"

response = requests.get(url)
models = response.json().get('models', [])
for m in models:
    if 'generateContent' in m.get('supportedGenerationMethods', []):
        print(m['name'])
