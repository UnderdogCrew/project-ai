import json
from os import getenv
from typing import Optional, Literal, Dict, Any

from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger

try:
    from tavily import TavilyClient
except ImportError:
    raise ImportError("`tavily-python` not installed. Please install using `pip install tavily-python`")


class TavilyTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        search: bool = True,
        max_tokens: int = 6000,
        include_answer: bool = True,
        search_depth: Literal["basic", "advanced"] = "advanced",
        format: Literal["json", "markdown"] = "markdown",
        use_search_context: bool = False,
    ):

        super().__init__()

        self.api_key = api_key or getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.error("TAVILY_API_KEY not provided")

        self.client: TavilyClient = TavilyClient(api_key=self.api_key)
        self.search_depth: Literal["basic", "advanced"] = search_depth
        self.max_tokens: int = max_tokens
        self.include_answer: bool = include_answer
        self.format: Literal["json", "markdown"] = format
        
        # Store configuration
        self.search = search
        self.use_search_context = use_search_context
        
        # Initialize tools based on configuration
        if self.search:
            if self.use_search_context:
                self.register(self.web_search_with_tavily, name="tavily_web_search")
            else:
                self.register(self.web_search_using_tavily, name="tavily_web_search")

    def web_search_using_tavily(self, query: str, max_results: int = 5) -> str:
        """Use this function to search the web for a given query.
        This function uses the Tavily API to provide realtime online information about the query.

        Args:
            query (str): Query to search for.
            max_results (int): Maximum number of results to return. Defaults to 5.

        Returns:
            str: JSON string of results related to the query.
        """
        try:
            logger.info(f"Starting Tavily search for query: {query}")
            
            if not self.api_key:
                logger.error("Tavily API key not provided")
                return "Error: Tavily API key not provided"

            response = self.client.search(
                query=query, search_depth=self.search_depth, include_answer=self.include_answer, max_results=max_results
            )

            if not response:
                logger.warning(f"No response from Tavily for query: {query}")
                return "No results found."

            clean_response: Dict[str, Any] = {"query": query}
            if "answer" in response:
                clean_response["answer"] = response["answer"]

            clean_results = []
            current_token_count = len(json.dumps(clean_response))
            for result in response.get("results", []):
                _result = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                }
                current_token_count += len(json.dumps(_result))
                if current_token_count > self.max_tokens:
                    break
                clean_results.append(_result)
            clean_response["results"] = clean_results

            logger.info(f"Successfully processed {len(clean_results)} results for query: {query}")

            if self.format == "json":
                return json.dumps(clean_response) if clean_response else "No results found."
            elif self.format == "markdown":
                _markdown = ""
                _markdown += f"# {query}\n\n"
                if "answer" in clean_response:
                    _markdown += "### Summary\n"
                    _markdown += f"{clean_response.get('answer')}\n\n"
                for result in clean_response["results"]:
                    _markdown += f"### [{result['title']}]({result['url']})\n"
                    _markdown += f"{result['content']}\n\n"
                return _markdown
                
        except Exception as e:
            logger.error(f"Error in Tavily search for query '{query}': {str(e)}")
            return f"Error searching Tavily: {str(e)}"

    def web_search_with_tavily(self, query: str) -> str:
        """Use this function to search the web for a given query.
        This function uses the Tavily API to provide realtime online information about the query.

        Args:
            query (str): Query to search for.

        Returns:
            str: JSON string of results related to the query.
        """
        try:
            logger.info(f"Starting Tavily search context for query: {query}")
            
            if not self.api_key:
                logger.error("Tavily API key not provided")
                return "Error: Tavily API key not provided"

            result = self.client.get_search_context(
                query=query, search_depth=self.search_depth, max_tokens=self.max_tokens, include_answer=self.include_answer
            )
            
            if not result:
                logger.warning(f"No search context from Tavily for query: {query}")
                return "No search context found."
            
            logger.info(f"Successfully retrieved search context for query: {query}")
            return result
            
        except Exception as e:
            logger.error(f"Error in Tavily search context for query '{query}': {str(e)}")
            return f"Error getting Tavily search context: {str(e)}"
