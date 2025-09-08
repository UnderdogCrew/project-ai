import asyncio
import logging
from typing import Optional

from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger

try:
    from crawl4ai import AsyncWebCrawler, CacheMode
except ImportError:
    raise ImportError("`crawl4ai` not installed. Please install using `pip install crawl4ai`")


class Crawl4aiTools(Toolkit):
    def __init__(
        self,
        existing_tools: Optional[list] = None,
        max_length: Optional[int] = 100000,
        timeout: int = 60
    ):
        """
        Initialize the web crawler tool with minimal improvements.

        Args:
            max_length: Maximum length of returned content
            timeout: Timeout in seconds for page loading
        """
        super().__init__(existing_tools or [])

        self.max_length = max_length
        self.timeout = timeout

        self.register(self.web_crawler, name="crawl4ai_tools")

    def web_crawler(self, url: str, max_length: Optional[int] = None) -> str:
        """
        Crawls a website using crawl4ai's WebCrawler with improved error handling.

        :param url: The URL to crawl.
        :param max_length: The maximum length of the result.

        :return: The results of the crawling.
        """
        if url is None:
            return "No URL provided"

        # Run the async crawler function synchronously
        return asyncio.run(self._async_web_crawler(url, max_length))

    async def _async_web_crawler(self, url: str, max_length: Optional[int] = None) -> str:
        """
        Asynchronous method to crawl a website using AsyncWebCrawler with retry logic.

        :param url: The URL to crawl.
        :param max_length: The maximum length of the result.

        :return: The results of the crawling as a markdown string.
        """
        length = max_length or self.max_length

        try:
            async with AsyncWebCrawler(thread_safe=True) as crawler:
                logger.info(f"Starting crawl for URL: {url}")
                
                result = await crawler.arun(
                    url=url, 
                    cache_mode=CacheMode.BYPASS,
                    page_timeout=self.timeout * 1000,  # Convert to milliseconds
                    wait_until="domcontentloaded",
                )

                if not result or not result.markdown:
                    return "No content found on the page"

                content = result.markdown.strip()
                if length and len(content) > length:
                    content = content[:length] + "..."
                    
                content = self._clean_content(content)

                logger.info(f"Successfully crawled {url}")
                return content

        except Exception as e:
                logger.error(f"Error crawling {url}: {str(e)}")
                return f"Error crawling the page: {str(e)}"

    def _clean_content(self, content: str) -> str:
        """Clean and optimize the crawled content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = " ".join(content.split())
        
        return content.strip()

if __name__ == '__main__':
    # Example usage
    crawler = Crawl4aiTools()
    print(crawler._tools)