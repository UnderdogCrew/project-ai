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
    "GoogleMap Types": "gmap/types",
    "GoogleMap Locations": "gmap/locations",
    "GoogleMap Place": "gmap/place",
    "GoogleMap Search": "gmap/search",
    "GoogleMap Enrich": "gmap/enrich"
}


class ScrapIoApiTools(Toolkit):
    def __init__(
        self,
        api_key: str,
        api_type: str,
    ):

        super().__init__()

        self.api_key = api_key
        self.api_type = api_type
        if not self.api_key:
            logger.warning("No Scrap IO API key provided")

        self.register(self.scrap_io_tool, name="scrap_io_tool")

    def scrap_io_tool(self, **kwargs) -> dict:
        """
            Search using the Scrap IO API. Returns the search results.

            Args:
                country_code (str): 2 letters (ISO 3166-1 alpha-2) country code (FR, US, etc.)
                type (str): Type of entity to search for (admin1, admin2, city)
                city(str): Name of the city
                search_term (str): The search_term to search for (e.g., Place name).
                google_id (str): Google id (ex: 0xabc:0xdef) 
                place_id (str): Place id (ex: ChIabcDeFGhIJkLMnoPqR)

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


            logger.info(f"Scrap IO Api calling")
            base_url = "https://scrap.io/api/v1/"

            api_end_point = api_call.get(self.api_type)

            api_url = f"{base_url}{api_end_point}"

            required_headers = {
                'Authorization': f"Bearer {self.api_key}",
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            

            params = []
            for key, value in kwargs.items():
                params.append(f"{key}={value}")

            if api_url.__contains__("?"):
                    url = f"{api_url}" + "&".join(params)
            else:
                url = f"{api_url}?" + "&".join(params)

            logger.info(f"params: {params}")
            payload = ""
            for _payload in params:
                if payload == "":
                    payload += _payload
                else:
                    payload += "&"+_payload
            # payload = "".join(params)
            logger.info(f"payload: {payload}")
            logger.info(f"url: {url}")
            response = requests.request("GET", url, headers=required_headers, data=payload)

            logger.info(f"Scrap IO Api response: {response.text}")

            return json.dumps(response.json())

        except Exception as e:
            return f"Error while doing zero bounce api call for the {self.api_type}: {e}"
