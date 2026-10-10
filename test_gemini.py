from google import genai
import os

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
response = client.models.generate_content(model="gemini-3.5-flash", contents="Hello, are you working?")
print(response.text)