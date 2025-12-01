from safe_llm import safe_llm_call

class CrewSafeLLM:
    def __init__(self, model="gpt-4.1", temperature=0.7):
        self.model = model
        self.temperature = temperature

    def __call__(self, prompt):
        prompt = clamp_prompt(prompt)   # 👈 APPLY CLAMP

        response = client.responses.create(
            model=self.model,
            input=prompt,
            temperature=self.temperature,
        )
        return response.output_text
