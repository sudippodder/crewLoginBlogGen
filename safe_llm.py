import time
import openai

def safe_llm_call(
    messages,
    model="gpt-4.1",
    temperature=0.8,
    max_retries=8
):
    retries = 0

    while True:
        try:
            return openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            ).choices[0].message.content

        except openai.RateLimitError as e:
            wait = min(2 ** retries, 20)
            print(f"[SAFE LLM] 429 detected. Waiting {wait} seconds…")
            time.sleep(wait)
            retries += 1

            if retries > max_retries:
                raise Exception("❌ Max retries exceeded for LLM call")

        except Exception:
            raise
