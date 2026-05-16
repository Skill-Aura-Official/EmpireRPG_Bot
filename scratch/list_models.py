import google.generativeai as genai
import os
import sys

# Add project root to path to import TSBSSB
sys.path.append(os.getcwd())

from TSBSSB.config import Config

api_key = "8743383751:AAFxNkHNlV0AflFIBDNQTRBijdVEmSWGSO4" 
# Wait, that's the telegram token. The GEMINI_API_KEY is:
api_key = "AIzaSyCBiY-280_0pltlTiRvTDeX-vdDDMzpO0s"

genai.configure(api_key=api_key)

print("Listing models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model: {m.name}")
except Exception as e:
    print(f"Error: {e}")
