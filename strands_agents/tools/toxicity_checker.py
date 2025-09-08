from strands import Agent
from strands.models.openai import OpenAIModel
from dotenv import load_dotenv

import os

from pydantic import BaseModel, Field

class Toxicity(BaseModel):
    is_toxic: bool = Field(..., description="Indicates if the query is toxic")

async def check_toxicity(query: str):
    """Scans the query for toxicity"""
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
    
    agent = Agent(
        model=OpenAIModel(model_id='gpt-5-nano', client_args={'api_key': OPENAI_API_KEY}),
        name="toxicity_checker",
        description="Checks the toxicity of a given query using OpenAI's API.",
        system_prompt=(
            "You are a strict content safety and policy compliance classifier. "
            "Your task is to determine if a user query should be marked as toxic under the `is_toxic` boolean. "
            "Mark `is_toxic` as true if the query contains, promotes, or requests racism/sexism/pornographic or sexual content"
        )
    )
    response = await agent.structured_output_async(Toxicity, query)
    return response.is_toxic


if __name__ == "__main__":
    import asyncio
    query = "Fuck you."
    result = asyncio.run(check_toxicity(query))
    print(result)