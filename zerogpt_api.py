import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
ZEROGPT_API_KEY = os.getenv("ZEROGPT_API_KEY")
ZEROGPT_API_URL = "https://api.zerogpt.com/api/detect/detectText"

def check_ai_content(text):
    headers = {
        "ApiKey": ZEROGPT_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"input_text": text}
    try:
        response = requests.post(ZEROGPT_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if not result.get("success"):
            return {"error": result.get("message", "API error.")}
        return result
    except Exception as e:
        return {"error": str(e)}
