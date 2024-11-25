from dotenv import load_dotenv
from os.path import isfile, join
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import os
from os.path import dirname
import re
from app.api.v1.endpoints.chat.db_helper import get_agent_data as fetch_ai_agent_data
from bson import ObjectId  # Importing ObjectId to handle MongoDB document IDs
from app.schemas.agent_chat_schema.chat_schema import GenerateAgentChatSchema
import requests

from phi.agent import Agent
from phi.tools.email import EmailTools
from phi.tools.googlesearch import GoogleSearch
from phi.tools.crawl4ai_tools import Crawl4aiTools
from phi.tools.serpapi_tools import SerpApiTools
from phi.tools.resend_tools import ResendTools
from phi.tools.zendesk import ZendeskTools
from phi.tools.youtube_tools import YouTubeTools
from phi.tools.wikipedia import WikipediaTools
from phi.tools.yfinance import YFinanceTools
from phi.model.openai import OpenAIChat
from phi.tools.perplexity_tool import PerplexityTools
from phi.vectordb.qdrant import Qdrant
from phi.tools.apify import ApifyTools
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.firecrawl import FirecrawlTools
from phi.tools.tavily import TavilyTools
# from phi.tools.pdf_extractor import PdfTools
from phi.knowledge.website import WebsiteKnowledgeBase
from app.api.v1.endpoints.chat.db_helper import fetch_manage_data, save_ai_request


tools_list = {
    "send_email": EmailTools,
    "perplexity_search": PerplexityTools,
    "google_search": GoogleSearch,
    "crawl4ai_tools": Crawl4aiTools,
    "serp_api_tools": SerpApiTools,
    "resend": ResendTools,
    "zendesk": ZendeskTools,
    "youtube": YouTubeTools,
    "wikipedia": WikipediaTools,
    "yfinance": YFinanceTools,
    "apify": ApifyTools,
    "duckduckgo": DuckDuckGo,
    "fire_crawl": FirecrawlTools,
    "tavily": TavilyTools,
    # "pdf_tools": PdfTools
}

import os

# Given path
env_path = join(dirname(__file__), '.env')

# Get the path up to 'project-ai'
project_ai_path = os.path.abspath(os.path.join(env_path, '../../../../../../.env'))
print(f"project_ai_path: {project_ai_path}")

load_dotenv(dotenv_path=project_ai_path)


qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")



class ChainStreamHandler(StreamingStdOutCallbackHandler):
    def __init__(self, gen):
        super().__init__()
        self.gen = gen
        self.final_token = ""

    def on_llm_new_token(self, token: str, **kwargs):
        self.final_token += token
        self.gen.send(token)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)



# Function to dynamically create tools based on the tool configuration
def create_tool(tool_config):
    """
    Creates a tool instance based on the provided configuration.

    Args:
        tool_config (dict): Configuration dictionary for the tool.
        prompt (str): The prompt to be used with the tool.

    Returns:
        Tool instance based on the tool configuration.

    Raises:
        ValueError: If the tool is not found in the tools_list.
    """
    tool_name = tool_config['name']
    tool_class = tools_list.get(tool_name)  # Retrieve the tool class from the tools list

    if tool_class:
        config = tool_config['config']  # Get the configuration for the tool
        # Create an instance of the tool based on its type
        if tool_name == "send_email":
            # Email tool configuration for sending emails
            return tool_class(
                sender_email=config.get('sender'),     # Email address of the sender
                sender_name=config.get("username"),    # Display name of the sender
                api_key=config.get('key')             # API key for email service (e.g., Resend, SendGrid)
            )
        elif tool_name in ["perplexity_search"]:
            # Perplexity AI search tool configuration
            return tool_class(
                api_key=config.get('key'),            # Perplexity API authentication key
                model=config.get('model')             # Specific model to use for search operations
            )
        elif tool_name == "crawl4ai_tools":
            # Web crawling tool with character limit configuration
            return tool_class(
                max_length=500                        # Maximum length of crawled content
            )
        elif tool_name in ['youtube', 'wikipedia', 'google_search', 'duckduckgo']:
            # Simple tools that don't require additional configuration
            return tool_class()
        elif tool_name in ['serp_api_tools', 'apify', "fire_crawl", "tavily", "pdf_tools"]:
            # Search Engine Results Page (SERP) API tool
            return tool_class(
                api_key=config.get('key')             # SERP API authentication key
            )
        elif tool_name == "resend":
            # Resend email service configuration
            return tool_class(
                api_key=config.get('key'),            # Resend API authentication key
                from_email=config.get('from_email')   # Default sender email address
            )
        elif tool_name == "zendesk":
            # Zendesk customer service platform configuration
            return tool_class(
                username=config.get('username'),       # Zendesk account username
                password=config.get('password'),       # Zendesk account password
                company_name=config.get('company_name')# Company subdomain in Zendesk
            )
        elif tool_name == "yfinance":
            # Yahoo Finance tool with multiple data retrieval options
            return tool_class(
                stock_price=config.get('stock_price'),                # Enable stock price data
                company_info=config.get('company_info'),              # Enable company information
                stock_fundamentals=config.get('stock_fundamentals'),  # Enable fundamental data
                income_statements=config.get('income_statements'),    # Enable income statement data
                key_financial_ratios=config.get('key_financial_ratios'),  # Enable financial ratios
                analyst_recommendations=config.get('analyst_recommendations'),  # Enable analyst data
                company_news=config.get('company_news'),              # Enable company news
                technical_indicators=config.get('technical_indicators'),  # Enable technical analysis
                historical_prices=config.get('historical_prices'),    # Enable historical price data
                enable_all=config.get("enable_all")                   # Enable all available data
            )
        elif tool_name == "apify":
            # Resend email service configuration
            return tool_class(
                api_key=config.get('key'),            # Resend API authentication key
                from_email=config.get('from_email')   # Default sender email address
            )
    else:
        raise ValueError(f"Tool '{tool_name}' not found in tools_list")  # Raise an error if tool not found




def generate_rag_response(request: GenerateAgentChatSchema):
    print("generate rag response called")
    file = request.file
    
    # Handle file content from AWS if file is provided
    if file:
        try:
            # Download file content from S3
            response = requests.get(file)
            
            # Get file extension from URL
            file_extension = file.split('.')[-1].lower()
            
            # Create a temporary file to store the content
            temp_file_path = f"temp_file.{file_extension}"
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)
            
            # Use appropriate loader based on file extension
            if file_extension == 'pdf':
                from langchain.document_loaders import PyPDFLoader
                loader = PyPDFLoader(temp_file_path)
                pages = loader.load()
                file_content = "\n".join([page.page_content for page in pages])
            elif file_extension == 'json':
                from langchain.document_loaders import JSONLoader
                loader = JSONLoader(temp_file_path)
                documents = loader.load()
                file_content = "\n".join([doc.page_content for doc in documents])
            elif file_extension == 'docx':
                from langchain.document_loaders import Docx2txtLoader
                loader = Docx2txtLoader(temp_file_path)
                documents = loader.load()
                file_content = "\n".join([doc.page_content for doc in documents])
            else:
                # For text files and other formats, use the original method
                file_content = response.text
            
            print(file_content)
            
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            # Append file content to message or use as message if no message provided
            message = f"{request.message}\n\nFile Content:\n{file_content}" if request.message else file_content
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            message = request.message  # Fallback to original message if file processing fails
    else:
        message = request.message

    # Fetch agent data using the agent ID from the request
    search_agents = {
        "_id": ObjectId(request.agent_id)
    }
    gpt_data = fetch_ai_agent_data(search_query=search_agents, skip=0, limit=1)
    
    tools = gpt_data[0]['tools']
    name = gpt_data[0]['name']
    llm_config = gpt_data[0]['llm_config']
    prompt = gpt_data[0]['system_prompt']
    additional_instructions = gpt_data[0]['instructions']
    
    # Set OpenAI API key from the configuration
    open_ai_api_key = llm_config['api-key']
    os.environ["OPENAI_API_KEY"] = open_ai_api_key
    
    # Initialize variables for RAG (Retrieval-Augmented Generation)
    rag_id = ""
    for feat in gpt_data[0]['features']:
        if feat['type_value'] == 3:
            rag_id = feat['config']['lyzr_rag']['rag_id']
    
    # Fetch manage data if rag_id is found
    if rag_id:
        query = {
            "rag_id": rag_id
        }
        manage_data = fetch_manage_data(search_query=query, skip=0, limit=1)
        rag_id = str(manage_data[0]['_id'])

    print(f"rag_id {rag_id}")
    embedding_id = f"embedding_{str(rag_id)}"

    # Initialize knowledge base if rag_id is available
    knowledge_base = None
    if rag_id:
        vector_db = Qdrant(
            collection=embedding_id,
            url=qdrant_url,
            api_key=qdrant_api_key,
        )
        
        # Perform a search in the vector database
        search_data = vector_db.search(query=message, limit=1)
        urls = [search.name for search in search_data]
        
        knowledge_base = WebsiteKnowledgeBase(
            urls=urls,
            vector_db=vector_db,
        )

    # Format the system prompt based on the schema or message
    formatted_template = message
    
    # Create tools based on the configuration
    config_tools = [create_tool(config) for config in tools if config['name'] in tools_list]

    # Create team agent
    agent_team = Agent(
        name=f"{name}",
        tools=config_tools,
        model=OpenAIChat(id=llm_config['model']),
        knowledge=knowledge_base,
        system_prompt=prompt,
        instructions=additional_instructions,
        show_tool_calls=True,
        debug_mode=True,
        structured_outputs=True,
        markdown=True
    )
    
    
    # Run the agent team and get the response
    agent_response = agent_team.run(formatted_template)
    response_text = agent_response.content.split(")\n\n")[1:]
    response_text_as_string = "\n\n".join(response_text)

    
    if response_text_as_string == "":
        response_text = agent_response.content
        response_text_as_string = response_text
    
    data = {
        "session_id": request.session_id,
        "agent_id": request.agent_id,
        "user_id": request.user_id,
        "message": request.message,
        "response": response_text_as_string
    }

    save_ai_request(request_data=data)

    return {
        "text": response_text_as_string
    }