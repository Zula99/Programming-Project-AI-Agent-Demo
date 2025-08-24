import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI

load_dotenv()  # Load environment variables from .env file

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

llm_openAI = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=2,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)