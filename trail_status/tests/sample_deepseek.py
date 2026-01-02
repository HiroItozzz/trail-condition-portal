
from openai import OpenAI
import os


deepseek_api_key=os.getenv("DEEPSEEK_API_KEY")
print(deepseek_api_key)
client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

response = client.responses.create(
  model="deepseek-chat",
  input="Write a one-sentence bedtime story about a unicorn."
)
print(response)
print(response.output_text)
