import json
import time
from typing import Optional, List, Dict, Any

from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger

try:
    from firecrawl import FirecrawlApp
except ImportError:
    raise ImportError("`firecrawl-py` not installed. Please install using `pip install firecrawl-py`")


class FirecrawlTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        formats: Optional[List[str]] = None,
        limit: int = 10,
        scrape: bool = True,
        crawl: bool = False,
    ):

        super().__init__()

        self.api_key: Optional[str] = api_key
        self.formats: Optional[List[str]] = formats
        self.limit: int = limit
        self.app: FirecrawlApp = FirecrawlApp(api_key=self.api_key)

        if crawl:
            scrape = False
        elif not scrape:
            crawl = True

        self.register(self.scrape_website, name="firecrawl_scrape_website")
        self.register(self.crawl_website, name="firecrawl_crawl_website")

    def scrape_website(self, url: str) -> str:
        """Use this function to Scrapes a website using Firecrawl.

        Args:
            url (str): The URL to scrape.

        Returns:
            The results of the scraping.
        """
        if url is None:
            return "No URL provided"

        try:
            logger.info(f"Starting scrape for URL: {url}")
            
            params = {}
            if self.formats:
                params["formats"] = self.formats

            scrape_result = self.app.scrape_url(url, params=params)
            
            if not scrape_result:
                return "No content found on the page"
            
            logger.info(f"Successfully scraped {url}")
            return json.dumps(scrape_result)
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return f"Error scraping the page: {str(e)}"

    def crawl_website(self, url: str, limit: Optional[int] = None) -> str:
        """Use this function to Crawls a website using Firecrawl.

        Args:
            url (str): The URL to crawl.
            limit (int): The maximum number of pages to crawl

        Returns:
            The results of the crawling.
        """
        if url is None:
            return "No URL provided"

        try:
            logger.info(f"Starting crawl for URL: {url}")
            
            params: Dict[str, Any] = {}
            if self.limit or limit:
                params["limit"] = self.limit or limit
                if self.formats:
                    params["scrapeOptions"] = {"formats": self.formats}

            crawl_result = self.app.crawl_url(url, params=params, poll_interval=30)
            
            if not crawl_result:
                return "No content found on the page"
            
            logger.info(f"Successfully crawled {url}")
            return json.dumps(crawl_result)
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return f"Error crawling the page: {str(e)}"
