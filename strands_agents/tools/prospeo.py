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
    "Email Finder" : "email-finder",
    "Mobile Finder": "mobile-finder",
    "Social Url Enrichment": "social-url-enrichment",
    "Domain Search": "domain-search",
    "Email Verifier": "email-verifier"
}


class ProspeoApiTools(Toolkit):
    def __init__(
        self,
        api_key: str,
        api_type: str,
    ):

        super().__init__()

        self.api_key = api_key
        self.api_type = api_type
        if not self.api_key:
            logger.warning("No Prospeo API key provided")

        self.register(self.pros_peo_tool, name="pros_peo_tool")

    def pros_peo_tool(self, **kwargs) -> dict:
        """
            Search using the ProsPeo API. Returns the search results.

            Args:
                email (str): The email to search for (e.g., email address).[optional]
                url (str): The url to search for (e.g., url from which we need to fetch the mobile, https://linkedin.com/in/johndoe).[optional]
                company (str): The company to search for (e.g., company name).[optional]
                first_name (str): The first name of the person whose email format is being searched. [optional]
                middle_name (str): The middle name of the person whose email format is being searched. [optional]
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


            logger.info(f"Pros Peo Api calling")
            base_url = "https://api.prospeo.io/"

            api_end_point = api_call.get(self.api_type)

            api_url = f"{base_url}{api_end_point}"

            required_headers = {
                'Content-Type': 'application/json',
                'X-KEY': self.api_key
            }
            

            params = {}
            for key, value in kwargs.items():
                params[key] = value
            logger.info(f"params: {params}")

            response = requests.request("POST", api_url, headers=required_headers, json=params)

            logger.info(f"Prospeo Api response: {response.text}")

            return json.dumps(response.json())

        except Exception as e:
            logger.error(f"Error while doing prospeo api call for the {self.api_type}: {e}")
            return f"Error while doing prospeo api call for the {self.api_type}: {e}"