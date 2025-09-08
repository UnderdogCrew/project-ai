import json
from os import getenv
from typing import Optional
import requests
import json

from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger

class PerplexityTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        temperature: Optional[float] = 0.2,
        top_p: Optional[float] = 0.9,
        search_domain_filter: Optional[list] = None,
        top_k: Optional[int] = 0,
        presence_penalty: Optional[float] = 0,
        frequency_penalty: Optional[float] = 1,
    ):
        super().__init__()
        self.api_key = api_key or getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("No Perplexity API key provided")
        self.model = model
        self.prompt = prompt
        self.temperature = float(temperature)
        self.top_p = float(top_p)
        self.search_domain_filter = search_domain_filter.split(",") if search_domain_filter is not None else None
        self.top_k = int(top_k)
        self.presence_penalty = float(presence_penalty)
        self.frequency_penalty = float(frequency_penalty)
        
        # Initialize tools
        self.register(self.search_perplexity, name="perplexity_tools")

    def search_perplexity(self, query: str) -> str:
        try:
            if not self.api_key:
                return "Please provide an API key"
            if not self.model:
                return "Please provide a Model name"
            if not query:
                return "Please provide a query to search for"

            logger.info(f"Searching Perplexity for: {query}")

            url = "https://api.perplexity.ai/chat/completions"

            system = """
                You are a helpful assistant with a focus on providing well-sourced information. When responding to questions:

                1. Analyze the query to identify key topics requiring evidence or sources
                2. Include relevant URLs to authoritative sources when providing factual information
                3. Format citations properly using a consistent style (APA, MLA, or Chicago)
                4. For academic topics, prioritize peer-reviewed journals and educational institutions
                5. For current events, reference reputable news organizations
                6. When sharing statistics or data, always cite the specific source and date
                7. If uncertainty exists about a fact, acknowledge limitations and provide multiple perspectives with their respective sources
                8. Organize complex information with clear headings and structured formatting
                9. When appropriate, include both primary sources (original research) and secondary sources (analyses)
                10. End responses with a "Further Reading" section for additional exploration when appropriate

                Remember to balance comprehensive sourcing with readability, ensuring citations support rather than overwhelm your response.
            """
            human = f"{query}"
            messages = []
            messages.append(
                {
                    "role": "system",
                    "content": system
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": human
                }
            )
            payload = json.dumps({
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "search_domain_filter": self.search_domain_filter,
                "top_k": self.top_k,
                "stream": False,
                "presence_penalty": self.presence_penalty,
                "frequency_penalty": self.frequency_penalty,
                "response_format": None
            })
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            logger.info("*************************api called************************************************")
            logger.info(f"************************************************************************* {headers}")
            logger.info(f"*************************************payload************************************ {payload}")
            response = requests.request("POST", url, headers=headers, data=payload)
            logger.info(f"************************************status_code************************************* {response.status_code}")
            if response.status_code != 200:
                logger.info(f"perpexlity ai search: {response.text}")
            if response.status_code == 200:
                response_data = response.json()
                citations = response_data['citations']
                content = response_data['choices'][0]['message']['content']
                usage = response_data['usage'] if "usage" in response_data else None
                json_data = {
                    "citations": citations,
                    "content": content,
                    "usage": usage
                }
                return json.dumps(json_data)
            else:
                logger.info(f"perpexlity ai search: {response.text}")
                return f"Error searching for the query"

        except Exception as e:
            logger.error(f"Error searching for the query {query}: {e}")
            return f"Error searching for the query {query}: {e}"
