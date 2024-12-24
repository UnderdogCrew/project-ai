from dotenv import load_dotenv
from os.path import isfile, join
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import os
from os.path import dirname
import re

from sympy import limit

from app.api.v1.endpoints.chat.db_helper import (get_agent_data as fetch_ai_agent_data, fetch_ai_requests_data,
                                                 get_environment_data, get_agent_history_data,
                                                 get_recent_chat_history_helper,get_chat_history, fetch_user_details, update_user_credit)
from bson import ObjectId  # Importing ObjectId to handle MongoDB document IDs
from app.schemas.agent_chat_schema.chat_schema import GenerateAgentChatSchema
import requests
from langchain_openai import OpenAIEmbeddings
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
from langchain_qdrant import QdrantVectorStore
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
import tiktoken
import os

# Given path
env_path = join(dirname(__file__), '.env')

# Get the path up to 'project-ai'
project_ai_path = os.path.abspath(os.path.join(env_path, '../../../../../../.env'))
print(f"project_ai_path: {project_ai_path}")

load_dotenv(dotenv_path=project_ai_path)

qdrant_url = os.getenv("QDRANT_API_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


def calculate_openai_cost(model: str, input_tokens: int, output_tokens: int, use_batch_api: bool = False,
                          is_cached: bool = False) -> float:
    """
    Calculate the cost of OpenAI API usage based on model and token counts.

    Args:
        model (str): Name of the OpenAI model
        input_tokens (int): Number of input (prompt) tokens
        output_tokens (int): Number of output (completion) tokens
        use_batch_api (bool): Whether to use Batch API pricing
        is_cached (bool): Whether to use cached input token pricing

    Returns:
        float: Total cost in USD
    """
    # Model pricing per 1M tokens
    model_pricing = {
        "gpt-4": {
            "input": 0.03,
            "output": 0.06
        },
        "gpt-4-32k": {
            "input": 0.06,
            "output": 0.12
        },
        "gpt-3.5-turbo": {
            "input": 0.0005,
            "output": 0.0015
        },
        "gpt-3.5-turbo-16k": {
            "input": 0.003,
            "output": 0.004
        },
        "gpt-4o": {
            "input": {
                "regular": 2.50,
                "cached": 1.25,
                "batch": 1.25
            },
            "output": {
                "regular": 10.00,
                "batch": 5.00
            }
        },
        "gpt-4o-mini": {
            "input": {
                "regular": 0.150,
                "cached": 0.075,
                "batch": 0.075
            },
            "output": {
                "regular": 0.600,
                "batch": 0.300
            }
        }
    }

    if model not in model_pricing:
        raise ValueError(f"Unknown model: {model}. Available models: {', '.join(model_pricing.keys())}")

    # Calculate costs based on model type and API usage
    if model in ["gpt-4o", "gpt-4o-mini"]:
        # Handle special pricing for GPT-4o models
        if is_cached:
            input_cost = (input_tokens / 1000) * model_pricing[model]["input"]["cached"]
        elif use_batch_api:
            input_cost = (input_tokens / 1000) * model_pricing[model]["input"]["batch"]
        else:
            input_cost = (input_tokens / 1000) * model_pricing[model]["input"]["regular"]

        if use_batch_api:
            output_cost = (output_tokens / 1000) * model_pricing[model]["output"]["batch"]
        else:
            output_cost = (output_tokens / 1000) * model_pricing[model]["output"]["regular"]
    else:
        # Standard pricing for other models
        input_cost = (input_tokens / 1000) * model_pricing[model]["input"]
        output_cost = (output_tokens / 1000) * model_pricing[model]["output"]

    # Calculate total cost
    total_cost = input_cost + output_cost

    return round(total_cost, 8) #+ 0.0025


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
                sender_email=config.get('sender'),  # Email address of the sender
                sender_name=config.get("username"),  # Display name of the sender
                api_key=config.get('key')  # API key for email service (e.g., Resend, SendGrid)
            )
        elif tool_name in ["perplexity_search"]:
            # Perplexity AI search tool configuration
            return tool_class(
                api_key=config.get('key'),  # Perplexity API authentication key
                model=config.get('model')  # Specific model to use for search operations
            )
        elif tool_name == "crawl4ai_tools":
            # Web crawling tool with character limit configuration
            return tool_class(
                max_length=500  # Maximum length of crawled content
            )
        elif tool_name in ['youtube', 'wikipedia', 'google_search', 'duckduckgo']:
            # Simple tools that don't require additional configuration
            return tool_class()
        elif tool_name in ['serp_api_tools', 'apify', "fire_crawl", "tavily", "pdf_tools"]:
            # Search Engine Results Page (SERP) API tool
            return tool_class(
                api_key=config.get('key')  # SERP API authentication key
            )
        elif tool_name == "resend":
            # Resend email service configuration
            return tool_class(
                api_key=config.get('key'),  # Resend API authentication key
                from_email=config.get('from_email')  # Default sender email address
            )
        elif tool_name == "zendesk":
            # Zendesk customer service platform configuration
            return tool_class(
                username=config.get('username'),  # Zendesk account username
                password=config.get('password'),  # Zendesk account password
                company_name=config.get('company_name')  # Company subdomain in Zendesk
            )
        elif tool_name == "yfinance":
            # Yahoo Finance tool with multiple data retrieval options
            return tool_class(
                stock_price=config.get('stock_price'),  # Enable stock price data
                company_info=config.get('company_info'),  # Enable company information
                stock_fundamentals=config.get('stock_fundamentals'),  # Enable fundamental data
                income_statements=config.get('income_statements'),  # Enable income statement data
                key_financial_ratios=config.get('key_financial_ratios'),  # Enable financial ratios
                analyst_recommendations=config.get('analyst_recommendations'),  # Enable analyst data
                company_news=config.get('company_news'),  # Enable company news
                technical_indicators=config.get('technical_indicators'),  # Enable technical analysis
                historical_prices=config.get('historical_prices'),  # Enable historical price data
                enable_all=config.get("enable_all")  # Enable all available data
            )
        elif tool_name == "apify":
            # Resend email service configuration
            return tool_class(
                api_key=config.get('key'),  # Resend API authentication key
                from_email=config.get('from_email')  # Default sender email address
            )
    else:
        raise ValueError(f"Tool '{tool_name}' not found in tools_list")  # Raise an error if tool not found


def generate_rag_response(request: GenerateAgentChatSchema, response_id: str = None):
    try:
        message = request.message
        device_id = request.device_id

        # Fetch agent data using the agent ID from the request
        gpt_data = fetch_ai_agent_data(agent_id=request.agent_id)

        user_id = gpt_data['user_id']

        agent_environment = get_environment_data(env_id=gpt_data['environment'])

        agent_tools = agent_environment['tools']
        tools = []
        for tool in agent_tools:
            tools.append(
                {
                    "name": tool['apiName'],
                    "config": tool['config']
                }
            )
        name = gpt_data['name']
        llm_config = agent_environment['llm_config']
        prompt = gpt_data['system_prompt']
        additional_instructions = gpt_data['instructions']

        # need to fetch the history from database
        history_query = {
            "user_id": user_id,
            "agent_id": request.agent_id
        }
        history_details = get_agent_history_data(query=history_query, skip=0, limit=5)
        history_details_list = []
        for history in history_details:
            history_details_list.append(
                {
                    "role": "user",
                    "content": history['message'],
                    "created_at": history['created_at']
                }
            )
            history_details_list.append(
                {
                    "role": "assistant",
                    "content": history['message'],
                    "created_at": history['created_at']
                }
            )
        sorted_data = []
        if len(history_details_list) > 0:
            # Sort dictionaries by 'age'
            sorted_dicts = sorted(history_details_list, key=lambda x: x['created_at'])
            for sorted_dict in sorted_dicts:
                sorted_data.append(
                    {
                        "role": sorted_dict['role'],
                        "content": sorted_dict['content']
                    }
                )
            print("Sorted dictionaries by age:", sorted_dicts)

        # Set OpenAI API key from the configuration
        open_ai_api_key = os.getenv("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = open_ai_api_key

        # Initialize variables for RAG (Retrieval-Augmented Generation)
        rag_id = ""
        for feat in agent_environment['features']:
            if feat['type_value'] == 3:
                rag_id = feat['config']['rag_id']

        embedding_id = f"{str(rag_id)}"
        print(f"embedding id {embedding_id}")

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
            # add_messages=sorted_data, # One of system, user, assistant, or tool.
            model=OpenAIChat(id=llm_config['model']),
            knowledge=knowledge_base,
            system_prompt=prompt,
            instructions=[additional_instructions],
            show_tool_calls=False,
            debug_mode=False,
            structured_outputs=True,
            markdown=True
        )

        # Run the agent team and get the response
        agent_response = agent_team.run(formatted_template)
        metrics = agent_response.messages[-1].metrics

        token_uses = {
            "input_tokens": metrics['input_tokens'],
            "output_tokens": metrics['output_tokens'],
            "total_tokens": metrics['total_tokens']
        }

        total_cost = calculate_openai_cost(model=llm_config['model'], input_tokens=metrics['input_tokens'], output_tokens=metrics['output_tokens'], is_cached=False)
        print(f"total cost: {total_cost}")
        response_text = agent_response.content.split(")\n\n")[1:]
        response_text_as_string = "\n\n".join(response_text)

        if response_text_as_string == "":
            response_text = agent_response.content
            response_text_as_string = response_text

        # Define regex patterns to exclude
        exclude_patterns = [
            r'^Running:',  # Lines starting with 'Running:'
            r'^- \w+\(',  # Lines starting with '- ' followed by a word and '(' (e.g., '- generate_text(')
        ]
        # Split the text into individual lines
        lines = response_text_as_string.split('\n')
        # Compile the regex patterns for efficiency
        compiled_patterns = [re.compile(pattern) for pattern in exclude_patterns]

        # Filter out lines matching any of the compiled patterns
        filtered_lines = [line for line in lines if
                          not any(pattern.match(line.strip()) for pattern in compiled_patterns)]

        # Join the filtered lines back into a single string
        main_content = '\n'.join(filtered_lines).strip()

        data = {
            "session_id": request.session_id,
            "agent_id": request.agent_id,
            "response_id": response_id,
            "user_id": user_id,
            "message": request.message,
            "device_id": device_id,
            "response": main_content,
            "token_uses": token_uses,
            "cost": total_cost
        }

        save_ai_request(request_data=data)
        
        # update cost in user table

        # Fetch the user details based on user_id
        user_details_query = {
            "email": user_id
        }
        user_details = fetch_user_details(query=user_details_query)

        if not user_details:
            print(f"User details not found for user_id: {user_id}. Skipping credit update.")
        else:
            # Update the credit in the user table after verifying the user details
            updated_credit = user_details['credit'] - total_cost
            if updated_credit < 0:
                print("Insufficient credit for the user.")
                pass
            else:
                # Construct the update query
                update_user_credit_query = {
                    "_id": ObjectId(user_details['_id'])
                }
                update_user_credit_data = {
                    "credit": updated_credit
                }

                # Perform the update
                update_user_credit(query=update_user_credit_query, update_data=update_user_credit_data)

                print(f"User credit updated successfully. Updated credit: {updated_credit}")

        return {
            "text": main_content
        }
    except Exception as e:
        data = {
            "session_id": request.session_id,
            "agent_id": request.agent_id,
            "response_id": response_id,
            "device_id": request.device_id,
            "user_id": request.user_id,
            "message": request.message,
            "response": str(e)
        }
        save_ai_request(request_data=data)
        return {
            "text": str(e)
        }


def get_response_by_id(response_id):
    query = {
        "response_id": response_id
    }
    document = fetch_ai_requests_data(query=query)
    if document is None:
        return None
    else:
        return {
            "text": document['response']
        }

def get_user_recent_session_by_user_email(device_id,skip,limit):
    document = get_recent_chat_history_helper(device_id=device_id,skip=skip,limit=limit)
    if not document:
        return {"total": 0, "sessions": []}
    
    total = document[0]["total"][0]["count"] if document[0]["total"] else 0
    sessions = document[0]["sessions"]
    
    # Add ellipsis to chat names that were truncated
    for session in sessions:
        if len(session["chat_name"]) == 30:
            session["chat_name"] += "..."

    return {
        "total": total,
        "sessions": sessions
    }

def get_chat_by_session_id(session_id,skip,limit):
    query = {"session_id": session_id}
    document,total = get_chat_history(query=query,skip=skip,limit=limit)
    messages = []
    for message in document:
        message["id"] = str(message.pop("_id"))
        messages.append(message)            
    return {
        "total": total,
        "messages": messages,        
    }