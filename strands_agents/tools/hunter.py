import json
from os import getenv
from typing import Optional

from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed.")


api_call = {
    "Domain Search": "domain-search",
    "Email Finder": "email-finder",
    "Email Verifier": "email-verifier",
    "People Find": "people/find"
}

class HunterApiTools(Toolkit):
    def __init__(
        self,
        api_key: str,
        api_type: int,
    ):

        super().__init__()

        self.api_key = api_key
        self.api_type = api_type
        if not self.api_key:
            logger.warning("No Hunter API key provided")

        self.register(self.search_hunter, name="hunter_search")

    def search_hunter(self, 
                domain: Optional[str] = None,
                first_name: Optional[str] = None,
                last_name: Optional[str] = None,
                email: Optional[str] = None
            ) -> dict:
        """
            Search using the Hunter API. Returns the search results.

            Args:
                domain (str): The domain to search for (e.g., a domain or company name).
                email (str): The email to search for (e.g., email address).[optional]
                first_name (str): The first name of the person whose email format is being searched. [optional]
                last_name (str): The last name of the person whose email format is being searched. [optional]

            Returns:
                dict: The search results from Hunter.
                    Keys:
                        - 'data': Contains the response data returned by Hunter API.
        """
        try:
            if not self.api_key:
                return "Please provide an API key"
            if not self.api_type:
                return "Please provide an API Type"


            logger.info(f"Hunter Api calling")
            base_url = "https://api.hunter.io/v2/"

            api_end_point = api_call.get(self.api_type)

            api_url = f"{base_url}{api_end_point}?"
            

            params = [f"api_key={self.api_key}"]
            if domain is not None:
                params.append(f"domain={domain}")
            if first_name is not None:
                params.append(f"first_name={first_name}")
            if last_name is not None:
                params.append(f"last_name={last_name}")
            if email is not None:
                params.append(f"email={email}")
            # for key, value in kwargs.items():
            #     params.append(f"{key}={value}")
            logger.info(f"params: {params}")
            logger.info(f"api_url: {api_url}")
            final_url = api_url + "&".join(params)
            logger.info(f"url: {final_url}")
            payload = {}
            headers = {}

            response = requests.request("GET", final_url, headers=headers, data=payload)

            logger.info(f"Hunter Api response: {response.text}")

            return json.dumps(response.json())

        except Exception as e:
            logger.error(f"Error while doing hunter api call for the {self.api_type}: {e}")
            return f"Error while doing hunter api call for the {self.api_type}: {e}"