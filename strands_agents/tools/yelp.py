"""
This module provides tools for searching business information using the Google Maps API.

Prerequisites:
- Set the environment variable `GOOGLE_MAPS_API_KEY` with your Google Maps API key.
  You can obtain the API key from the Google Cloud Console:
  https://console.cloud.google.com/projectselector2/google/maps-apis/credentials

- You also need to activate the Address Validation API for your .
  https://console.developers.google.com/apis/api/addressvalidation.googleapis.com

"""

import json
from datetime import datetime
from os import getenv
from typing import List, Optional

from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger

try:
    import requests
except ImportError:
    print("Error while importing requests.")


class YelpTools(Toolkit):
    def __init__(
        self,
        key: Optional[str] = None,
        search_businesses: bool = True,
        search_businesses_phone: bool = True,
        food_bussinesses_search: bool = True,
    ):

        super().__init__()

        self.api_key = key
        if not self.api_key:
            raise ValueError("YELP API KEY is not set in the environment variables.")

        if search_businesses:
            self.register(self.search_businesses, name="yelp_search_businesses")
        if search_businesses_phone:
            self.register(self.search_businesses_phone, name="yelp_search_businesses_phone")
        if food_bussinesses_search:
            self.register(self.food_bussinesses_search, name="yelp_food_bussinesses_search")

    def search_businesses(self, **kwargs) -> str:
        """
        Search for businesses using Yelp API.
        This tool takes a search query and returns detailed businesses information.

        Args:
            location (str): The query string to search for using Yelp API. (e.g., "dental clinics in Noida")
            term (str): Search term, e.g. "food" or "restaurants". The term may also be the business's name, such as "Starbucks". If term is not included the endpoint will default to searching across businesses from a small number of popular categories.

        Returns:
            Stringified list of dictionaries containing business information like name, address, phone, website, image_url, and review_count etc.
        """
        try:
            params = []
            url = "https://api.yelp.com/v3/businesses/search?"

            for key, value in kwargs.items():
                params.append(f"{key}={value}")
            print(f"params: {params}")

            url = f"{url}" + "&".join(params)

            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {self.api_key}"
            }

            response = requests.get(url, headers=headers)

            logger.info(f"Yelp Api response code: {response.status_code}")

            return json.dumps(response.json())

        except Exception as e:
            logger.error(f"Error searching Google Maps: {str(e)}")
            return str([])
    
    def search_businesses_phone(self, **kwargs) -> str:
        """
        Search for businesses using Yelp API and phone number.
        This tool takes a search query and returns detailed businesses information.

        Args:
            phone (str): Phone number of the business you want to search for. It must start with + and include the country code, like +14159083801.

        Returns:
            Stringified list of dictionaries containing business information like name, address, phone, website, image_url, and review_count etc.
        """
        try:
            params = []
            url = "https://api.yelp.com/v3/businesses/search/phone?"

            for key, value in kwargs.items():
                params.append(f"{key}={value}")

            url = f"{url}" + "&".join(params)

            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {self.api_key}"
            }

            response = requests.get(url, headers=headers)

            logger.info(f"Yelp Api response code: {response.status_code}")

            return json.dumps(response.json())

        except Exception as e:
            logger.error(f"Error searching Google Maps: {str(e)}")
            return str([])

    def food_bussinesses_search(self, **kwargs) -> str:
        """
            returns a list of businesses which support requested transaction type.
            This tool takes a search query and returns detailed businesses information.

            Args:
                location (str): The query string to search for using Yelp API. (e.g., "dental clinics in Noida")
                term (str): Search term, e.g. "food" or "restaurants". The term may also be the business's name, such as "Starbucks". If term is not included the endpoint will default to searching across businesses from a small number of popular categories.

            Returns:
                Stringified list of dictionaries containing business information like name, address, phone, website, image_url, and review_count etc.
        """
        try:
            params = []
            url = "https://api.yelp.com/v3/transactions/delivery/search?"

            for key, value in kwargs.items():
                params.append(f"{key}={value}")
            print(f"params: {params}")

            url = f"{url}" + "&".join(params)

            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {self.api_key}"
            }

            response = requests.get(url, headers=headers)

            logger.info(f"Yelp Api response code: {response.status_code}")

            return json.dumps(response.json())

        except Exception as e:
            logger.error(f"Error searching Google Maps: {str(e)}")
            return str([])
