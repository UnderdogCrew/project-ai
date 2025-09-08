import json
import traceback
from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed.")


api_call = {
    "Validate": "validate",
    "Guess Format": "guessformat"
}


class ZeroBounceApiTools(Toolkit):
    def __init__(
        self,
        api_key: str,
        api_type: str,
    ):
        super().__init__()
        self.api_key = api_key
        self.api_type = api_type
        if not self.api_key:
            logger.warning("No Zero Bounce key provided")

        self.register(self.zero_bounce_tool, name="zero_bounce_tool")

    def zero_bounce_tool(self, **kwargs) -> dict:
        """
            Search using the Zero Bounce API. Returns the search results.

            Args:
                email (str): The email to search for (e.g., email address).[optional]
                domain (str): The domain to search for (e.g., domain).[optional]
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


            logger.info(f"Zero Bounce Api calling")
            base_url = "https://api.zerobounce.net/v2/"

            api_end_point = api_call.get(self.api_type)

            api_url = f"{base_url}{api_end_point}?"
            
            params = [f"api_key={self.api_key}"]
            for key, value in kwargs.items():
                params.append(f"{key}={value}")

            url = f"{api_url}" + "&".join(params)
            payload = {}
            headers = {}

            response = requests.request("GET", url, headers=headers, data=payload)

            logger.info(f"Zero Bounce Api response code: {response.status_code}")

            return json.dumps(response.json())

        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            line_number = tb[-1].lineno
            filename = tb[-1].filename
            logger.error(f"Error while doing zero bounce api call for the {self.api_type}: {e} at line {line_number} in {filename}")
            return f"Error while doing zero bounce api call for the {self.api_type}: {e}"
