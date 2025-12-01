import os
import requests
from crewai.tools import BaseTool
from typing import Type
import http.client
import json

class SerperTool(BaseTool):
    name: str = "serper_tool"
    description: str = "Search the web using the Serper API and return summarized snippets."

    def _run(self, query: str) -> str:
        """Run the tool with a given query."""
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            return "Error: SERPER_API_KEY not found in environment variables."

        # url = "https://serper.dev/api/search"
        # headers = {"X-API-KEY": api_key}
        # payload = {"q": query}
        # try:
        #     response = requests.post(url, headers=headers, json=payload, timeout=10)
        #     response.raise_for_status()
        # except requests.RequestException as e:
        #     return f"Serper API request failed: {e}"


        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
          "q": query
        })
        headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
        }
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        response = res.read()
        return response.decode("utf-8")
        #data = json.loads(response)
        # data = response.json()
        # snippets = [r.get("snippet", "") for r in data.get("organic", [])]
        # return "\n".join(snippets) if snippets else "No results found."



  #print(data.decode("utf-8"))
  #st.json(data.decode("utf-8"))
# if __name__ == "__main__":
#     SerperTool("Travel Guide to Kolkata")
