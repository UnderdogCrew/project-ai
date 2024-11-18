from langchain_core.prompts import ChatPromptTemplate
import json
from os import getenv
from typing import Optional

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from langchain_community.chat_models import ChatPerplexity
except ImportError:
    raise ImportError("`chat-perplexity` not installed.")


class PerplexityTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None
    ):
        super().__init__(name="perplexity_tools")

        self.api_key = api_key or getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("No Perplexity API key provided")
        self.model = model
        self.prompt = prompt
        self.register(self.search_perplexity)
        
    
    def search_perplexity(self, query: str) -> str:
        try:
            if not self.api_key:
                return "Please provide an API key"
            if not self.model:
                return "Please provide a Model name"
            if not query:
                return "Please provide a query to search for"

            logger.info(f"Searching Perplexity for: {query}")

            llm = ChatPerplexity(
                temperature=0,
                pplx_api_key=self.api_key,
                streaming=False,
                model=self.model
            )

            system = "You are a helpful assistant."
            human = "{input}"
            prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])

            chain = prompt | llm
            response = chain.invoke({"input": query})
            return response.content

        except Exception as e:
            return f"Error searching for the query {query}: {e}"