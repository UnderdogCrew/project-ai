from pyexpat import features

from dotenv import load_dotenv

from os.path import dirname
from os.path import join
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import os

from datetime import datetime
from app.api.v1.endpoints.chat.db_helper import (get_agent_data as fetch_ai_agent_data, fetch_ai_requests_data, get_environment_data)

from bson import ObjectId
import requests

from strands_agents.tools import EmailTools, PerplexityTools, GoogleSearch, Crawl4aiTools, SerpApiTools, ResendTools, ZendeskTools, YouTubeTools, WikipediaTools, YFinanceTools, ApifyTools, DuckDuckGo, FirecrawlTools, TavilyTools, HunterApiTools, ZeroBounceApiTools, ProspeoApiTools, ScrapIoApiTools, GoogleMapTools, YelpTools, PostgresSqlTools
from strands_agents.utils.struct_op import create_dynamic_model

from app.api.v1.endpoints.chat.db_helper import fetch_manage_data, save_ai_request, fetch_rag_data

import json
import time
import openai
from together import Together as Together_client
from qdrant_client import QdrantClient
import traceback
from openai import OpenAI
from zep_cloud.client import Zep
import time
import json
import os
import requests
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.core.config import settings

from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.models.anthropic import AnthropicModel
from strands.models.bedrock import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.agent.state import AgentState
from qdrant_client import QdrantClient
from app.schemas.strands_agents import GenerateAgentChatSchema

import cohere

import asyncio

together_client = Together_client()


api_platform = os.getenv("API_PLATFORM")
ZEP_PROJECT_KEY = os.environ.get('ZEP_PROJECT_KEY')

zep_client = Zep(
    api_key=ZEP_PROJECT_KEY,
)


cohere_client = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

openai.api_type = "openai"
open_ai_client = OpenAI()

def get_openai_embedding(text: str, model = "text-embedding-ada-002") -> list[float]:
    user_embedding = open_ai_client.embeddings.create(
        input=text,
        model=model
    )
    return user_embedding.data[0].embedding


os.environ['OPENAI_API_TYPE'] = "openai"
openai.api_type = "openai"

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
    # "pdf_tools": PdfTools,
    "hunter_tool": HunterApiTools,
    "zero_bounce_tool": ZeroBounceApiTools,
    "pros_peo_tool": ProspeoApiTools,
    "scrap_io_tool": ScrapIoApiTools,
    "google_maps": GoogleMapTools,
    "yelp": YelpTools,
    "postgres_sql": PostgresSqlTools
}

env_path = join(dirname(__file__), 'env')
dir_path = os.path.dirname(os.path.realpath(__file__))
load_dotenv()

qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
os.environ['AUTOGEN_USE_DOCKER'] = "no"
os.environ['TOKENIZERS_PARALLELISM'] = "false"
CONNECTION_STRING = os.getenv("SQLALCHEMY_DATABASE_URL")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_URL = os.getenv("AWS_S3_URL")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_S3_REGION = os.getenv("AWS_S3_REGION")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ['AUTOGEN_USE_DOCKER'] = "no"
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
mistral_api_key = os.getenv("mistral_api_key")

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

def create_tool(tool_config, user_id, url=None, method=None):
    """
    Creates a tool instance based on the provided configuration.

    Args:
        tool_config (dict): Configuration dictionary for the tool.

    Returns:
        Tool instance based on the tool configuration.

    Raises:
        ValueError: If the tool is not found in the tools_list.
    """
    tool_name = tool_config['name']
    tool_class = tools_list.get(tool_name)

    if tool_class:
        config = tool_config['config']
        if tool_name == "send_email":
            return tool_class(
                sender_email=config.get('sender'),
                sender_name=config.get("username"),
                api_key=config.get('key')
            )
        elif tool_name in ["perplexity_search"]:
            return tool_class(
                api_key=config.get('key'),
                model=config.get('model'),
                temperature=config.get('temperature', 0.2),
                top_p=config.get('top_p', 0.9),
                search_domain_filter=config.get('search_domain_filter', None),
                top_k=config.get('top_k', 0),
                presence_penalty=config.get('presence_penalty', 0),
                frequency_penalty=config.get('frequency_penalty', 1)
            )
        elif tool_name == "crawl4ai_tools":
            return tool_class(
                max_length=500
            )
        elif tool_name in ['youtube', 'wikipedia', 'google_search', 'duckduckgo', 'generative_text', 'image_tools', "generate_image", "image_to_image"]:
            return tool_class()
        elif tool_name in ['serp_api_tools', 'apify', "fire_crawl", "tavily"]:
            return tool_class(
                api_key=config.get('key')
            )
        elif tool_name == "pdf_tools":
            return tool_class(
                api_key=config.get('key'),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_bucket_name=os.getenv("ISOMETRIK_AWS_S3BUCKET"),
                aws_url=os.getenv("ISOMETRIK_AWS_S3URL")
            )
        elif tool_name == "resend":
            return tool_class(
                api_key=config.get('key'),
                from_email=config.get('from_email')
            )
        elif tool_name == "zendesk":
            return tool_class(
                username=config.get('username'),
                password=config.get('password'),
                company_name=config.get('company_name')
            )
        elif tool_name == "yfinance":
            return tool_class(
                stock_price=config.get('stock_price'),
                company_info=config.get('company_info'),
                stock_fundamentals=config.get('stock_fundamentals'),
                income_statements=config.get('income_statements'),
                key_financial_ratios=config.get('key_financial_ratios'),
                analyst_recommendations=config.get('analyst_recommendations'),
                company_news=config.get('company_news'),
                technical_indicators=config.get('technical_indicators'),
                historical_prices=config.get('historical_prices'),
                enable_all=config.get("enable_all")
            )
        elif tool_name == "google_maps":
            return tool_class(
                search_places=config.get('search_places'),               
                get_directions=config.get('get_directions'),             
                validate_address=config.get('validate_address'),  
                geocode_address=config.get('geocode_address'),    
                reverse_geocode=config.get('reverse_geocode'),  
                get_distance_matrix=config.get('get_distance_matrix'),
                get_elevation=config.get('get_elevation'),        
                get_timezone=config.get('get_timezone'), 
                key=config.get('key')
            )
        elif tool_name == "yelp":
            return tool_class(
                search_businesses=config.get('search_businesses'),               
                search_businesses_phone=config.get('search_businesses_phone'),             
                food_bussinesses_search=config.get('food_bussinesses_search'),
                key=config.get('key')
            )
        elif tool_name == "apify":
            return tool_class(
                api_key=config.get('key'),
                from_email=config.get('from_email')
            )
        elif tool_name == "image_search":
            return tool_class(
                api_key=config.get('google_custom_search_api_key'),
                search_engine_id=config.get('search_engine_id'),
                image_folder_name=config.get('image_folder_name'),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_bucket_name=os.getenv("ISOMETRIK_AWS_S3BUCKET"),
                aws_url=os.getenv("ISOMETRIK_AWS_S3URL")
            )
        elif tool_name == "custom_tool":
            return tool_class(
                api_headers=config.get('api_headers'),
                token=user_id,
                tfm_user_id=user_id,
                url=url, 
                method=method,
                GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY
            )
        elif tool_name == "hunter_tool" or tool_name == "zero_bounce_tool" or tool_name == "pros_peo_tool" or tool_name == "scrap_io_tool":
            return tool_class(
                api_key=config.get('api_key'),
                api_type=config.get('api_type')  
            )
        elif tool_name == "postgres_sql":
            return tool_class(
                db_url=config.get('db_url')
            )
    else:
        raise ValueError(f"Tool '{tool_name}' not found in tools_list")


def create_strands_tools(tool_configs: List[Dict], user_id: str = None) -> List:
    """
    Convert tool configurations to Strands-compatible tools using strands_agents.tools.
    """
    strands_tools = []
    for config in tool_configs:
        tool_name = config.get('name', '')
        try:
            tool_instance = create_tool(config, user_id)
            if tool_instance:
                strands_tools.append(tool_instance)
        except Exception as e:
            print(f"[ERROR] Could not create tool '{tool_name}': {e}")
    return strands_tools


def get_strands_model(model_vendor_client_id: int, llm_config: Dict) -> Any:
    """
    Get the appropriate Strands model based on vendor client ID.
    """
    model_id = llm_config.get('model', 'gpt-4.1-nano')
    
    if model_vendor_client_id == 1:
        return OpenAIModel(model_id=model_id, client_args={'api_key': llm_config.get('api-key', OPENAI_API_KEY)})
    elif model_vendor_client_id == 12:
        return AnthropicModel(model_id=model_id)
    elif model_vendor_client_id in [3]:
        return BedrockModel(model_id=model_id)
    elif model_vendor_client_id == 14:
        return OpenAIModel(model_id=model_id, client_args={'api_key': DEEPSEEK_API_KEY, "base_url": "https://api.deepseek.com/v1"})
    elif model_vendor_client_id == 13:
        return OpenAIModel(model_id=model_id, client_args={'api_key': GOOGLE_API_KEY, "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"})
    elif model_vendor_client_id == 16:
        return OpenAIModel(model_id=model_id, client_args={'api_key': GROQ_API_KEY, "base_url": "https://api.groq.com/openai/v1"})
    elif model_vendor_client_id == 15:
        return OpenAIModel(model_id=model_id, client_args={'api_key': XAI_API_KEY, "base_url": "https://api.x.ai/v1"})
    
    else:
        return OpenAIModel(model_id='gpt-5-nano', client_args={'api_key': OPENAI_API_KEY})

async def generate_rag_response_strands(
    request: GenerateAgentChatSchema, 
    db, 
    response_id: str = None,
    g=None,
    user_id=None
) -> Dict[str, Any]:
    function_start_time = time.time()
    print("[DEBUG] Entered generate_rag_response_strands")
    print(f"[DEBUG] Request: {request}")
    print(f"[DEBUG] Response ID: {response_id}")
    print(f"[DEBUG] DB: {db}")
    print(f"[DEBUG] Generator: {g}")

    try:
        stream = request.stream

        if not isinstance(request.session_id, str):
            print("[ERROR] Invalid session ID format")
            return {
                "message": "Invalid session ID format. It should be a UUID or timestamp in string format.",
                "status_code": 400
            }

        print("[DEBUG] Fetching agent data...")
        gpt_data = fetch_ai_agent_data(agent_id=request.agent_id)
        print(f"[DEBUG] gpt_data: {gpt_data}")

        if not gpt_data:
            print("[ERROR] No agent data found")
            return {"message": "No agent data found", "status_code": 404}

        gpt_details = gpt_data

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
        llm_config = agent_environment['llm_config']

        name = gpt_details['name']
        print(f"[DEBUG] Agent name: {name}")

        agent_features = agent_environment['features'] if "features" in agent_environment else []
        additional_instruction = gpt_details['instructions']
        system_prompt = gpt_details['system_prompt']
        schema = agent_environment.get('schema', None)
        is_structured_output = llm_config.get('is_structured_output', False)
        print(f'[DEBUG]structured_ot: {gpt_details.get("is_structured_output", False)}')
        print(f"[DEBUG] is_structured_output: {is_structured_output}")
        if is_structured_output:
            structured_output = gpt_details.get('structured_output', [])
            response_model = create_dynamic_model(structured_output)


        print(f"[DEBUG] tools: {tools}, agent_features: {agent_features}, llm_config: {llm_config}, additional_instruction: {additional_instruction}, system_prompt: {system_prompt}")

        is_humanizer_present = any(obj.get("type") == "HUMANIZER" for obj in agent_features)
        is_reflective_present = any(obj.get("type") == "REFLECTION" for obj in agent_features)
        is_memory_enable = any(obj.get('type') == 'MEMORY' for obj in agent_features)

        print("[DEBUG] Creating Strands tools...")
        config_tools = create_strands_tools(tools)
        print(f"[DEBUG] config_tools: {config_tools}")

        message = request.message
        
        # Initialize variables for RAG (Retrieval-Augmented Generation)
        rag_id = ""
        rag_context = ""
        for feat in agent_environment['features']:
            if feat['type_value'] == 3:
                rag_id = feat['config']['rag_id']
                print(f"[DEBUG] Found RAG feature, rag_id: {rag_id}")
                break
        
        if rag_id:
            try:
                print("[DEBUG] Fetching manage data for RAG...")
                query = {"rag_id": rag_id}
                manage_data = fetch_manage_data(search_query=query, skip=0, limit=1)
                rag_data = fetch_rag_data({"_id": ObjectId(rag_id)}, 0, 1)
                rag_id = str(manage_data['_id'])
                rag_data = list(rag_data)[0]
                top_k = rag_data.get('top_k_similarity', 3)
                print(rag_data)
                rag_model = rag_data.get('embedding_model', 'text-embedding-ada-002')

                print(f"[DEBUG] manage_data: {list(manage_data)}, rag_id: {rag_id}, rag_model: {rag_model}")

                print(f"[DEBUG] Generating embedding for user query: {message[:100]}...")
                query_embedding = get_openai_embedding(message, model = rag_model)
                print(f"[DEBUG] Generated query embedding, dimension: {len(query_embedding)}")
                
                embedding_id = f"embedding_{rag_id}"
                print(f"[DEBUG] Searching Qdrant collection: {embedding_id}")
                
                client = QdrantClient(
                    api_key=settings.QDRANT_API_KEY,
                    url=settings.QDRANT_API_URL
                )
                
                search_results = client.search(
                    collection_name=embedding_id,
                    query_vector=query_embedding,
                    limit=15,
                    score_threshold=0.4,
                    with_payload=True,
                    with_vectors=False
                )

                print(f"[DEBUG] Found {len(search_results)} relevant chunks")

                relevant_contexts = []
                for result in search_results:
                    score = result.score
                    content = result.payload.get('page_content', '')
                    
                    print(f"[DEBUG] Chunk score: {score:.3f}, preview: {content[:100]}...")
                    print(len(content))
                    if content.strip():
                        relevant_contexts.append(content)

                reranked_data = cohere_client.v2.rerank(
                    model="rerank-english-v3.0",
                    documents=relevant_contexts,
                    query=message,
                    top_n=top_k
                )

                final_chunks = []

                for doc in reranked_data.results:
                    idx = doc.index
                    if doc.relevance_score > 0.1:
                        final_chunks.append(relevant_contexts[idx])
                        print(f"[DEBUG] Reranked chunk score: {doc.relevance_score:.3f}, preview: {relevant_contexts[idx]}...")

                if final_chunks:
                    rag_context += "\n\n---\n\n".join(final_chunks)
                    print(f"[DEBUG] Final RAG context length: {len(rag_context)} characters")
                else:
                    print("[DEBUG] No relevant context found above threshold")
                    
            except Exception as e:
                print(f"[ERROR] RAG context retrieval error: {e}")
                # Optional: Add fallback to keyword search here if needed

        print("[DEBUG] Building system prompt...")
        if rag_context:
            system_prompt = f"{system_prompt}\n\nContext: {rag_context}"
        if schema:
            system_prompt = f"{system_prompt}\n\n{schema}"
        if additional_instruction:
            system_prompt = f"{system_prompt}\n\n{additional_instruction}"
        if is_humanizer_present:
            system_prompt += '''
            Before providing your final answer:
                - Engages in natural, flowing conversation
                - Shows emotional intelligence and empathy
                - Maintains consistent personality
                - References relevant details from previous conversations when appropriate
                - Uses varied, natural language
                - Expresses appropriate uncertainty
            '''
        if is_reflective_present:
            system_prompt += '''
            Before providing your final answer:
                - Think through the problem step by step
                - Consider multiple perspectives and approaches
                - Verify your reasoning and check for mistakes
                - Explain your thought process
                - Highlight any uncertainties or assumptions
            '''
        system_prompt += f"\nCurrent date: {datetime.now()}"
        print(f"[DEBUG] Final system_prompt: {system_prompt[:200]}...")
        formatted_message = message
        print(f"[DEBUG] formatted_message: {formatted_message[:200]}...")

        print("[DEBUG] Getting Strands model...")
        model = get_strands_model(model_vendor_client_id=1, llm_config=llm_config)
        print(f"[DEBUG] model: {model}")

        initial_messages = []
        if is_memory_enable:
            print("[DEBUG] Loading memory for agent...")
            try:
                memory_query = {"session_id": request.session_id}
                memory_details = fetch_ai_requests_data(query=memory_query)
                print(f"[DEBUG] memory_details: {memory_details}")
                for memory in memory_details:
                    initial_messages.extend([
                        {"role": "assistant", "content": [{'text': memory["response"]}]},
                        {"role": "user", "content": [{"text": memory["message"]}]}

                    ])
                print(f"[DEBUG] initial_messages: {initial_messages[::-1]}")
            except Exception as e:
                print(f"[ERROR] Memory loading error: {e}")

        print("[DEBUG] Creating Agent...")
        agent = Agent(
            name=name,
            model=model,
            tools=config_tools,
            system_prompt=system_prompt,
            messages=initial_messages[::-1],
            conversation_manager=SlidingWindowConversationManager(window_size=40),
            agent_id=request.session_id,
            state=AgentState({"session_id": request.session_id}),
        )

        print("[DEBUG] Agent created")

        agent_start_time = time.time()
        print("[DEBUG] Starting agent response...")
        if is_structured_output:
            formatted_message = f"{formatted_message}\n\nCapture the following points in detail from the content/tool_call:\n"
            formatted_message += '\n'.join([i["key"] for i in structured_output])
        if stream:
            print("[DEBUG] WRONG FUNCTION CALLED, STREAMING NOT SUPPORTED")
        else:
            print("[DEBUG] Getting agent response...")
            result = await agent.invoke_async(formatted_message)
            response_text = str(result)

            if is_reflective_present:
                print(f'Before : {response_text}')
                response_text = await agent.invoke_async(f"Reflect on your response, and provide a more in depth, focused, and verbose response. RETURN ONLY THE NEW TEXT, NO CONFIRMATION TEXT LIKE SURE THING FOR THIS REPROMPT:\n {response_text}")
                print(f'After : {response_text}')

            if is_humanizer_present:
                print(f'Before : {response_text}')
                response_text = await agent.invoke_async(f"Convert this text to a more human-written-like format, using beginner friendly english terms and slags, explaining everything that you can, again, all in human like language, asking questions along the way like, following along? or does that make sense? RETURN ONLY THE NEW TEXT, NO CONFIRMATION TEXT LIKE SURE THING FOR THIS REPROMPT:\n{response_text}")            
                print(f'After : {response_text}')

            response_text = str(result)

            print("[DEBUG] Agent response received")


        agent_duration = time.time() - agent_start_time
        print(f"[DEBUG] Agent processing completed in {agent_duration:.2f} seconds for {name}")

        response_text = response_text.replace('json', "").replace('```', "")
        print(f"[DEBUG] Cleaned response_text: {response_text[:200]}...")

        if is_structured_output:
            try:
                response_md = await agent.structured_output_async(response_model, response_text)
                response_text = response_md.model_dump_json()

            except Exception as e:
                print(f"[ERROR] Structured output error: {e}")
                response_text = f"Structured output error: {str(e)}"


        data = {
            "message": request.message,
            "project_type": 1,
            "request_id": 1,
            "response": response_text,
            "session_id": request.session_id,
            "fingure_print_id": request.agent_id,
            "bot_id": request.agent_id,
            "image_data": None,
            "sources": None,
            "supported_ai_model_name": llm_config['model'],
            "response_id": response_id,
            "created_at": datetime.now(),
            "input_token_count": len(request.message)
        }

        print(f"[DEBUG] Saving AI request data: {data}")
        save_ai_request(request_data=data)

        total_duration = time.time() - function_start_time
        print(f"[DEBUG] Total execution time: {total_duration:.2f} seconds")
        print("[DEBUG] Returning response")
        return {"text": response_text}

    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        line_number = tb[-1].lineno
        filename = tb[-1].filename
        print(f"[ERROR] Error occurred: {e} at line {line_number} in {filename}")

        error_message = str(e).lower()

        if "insufficient_quota" in error_message or "quota exceeded" in error_message:
            print("[ERROR] API credit limit exceeded")
            return {"error": "API credit limit exceeded. Please check your account balance.", "status_code": 402}
        elif "rate limit" in error_message:
            print("[ERROR] Rate limit exceeded")
            return {"error": "Rate limit exceeded. Please try again later.", "status_code": 429}
        elif "invalid api key" in error_message:
            print("[ERROR] Invalid API key")
            return {"error": "Invalid API key. Please check your API credentials.", "status_code": 401}
        else:
            print("[ERROR] Unexpected error, saving to DB if possible")
            if gpt_data:
                data = {
                    "message": request.message,
                    "project_type": 1,
                    "request_id": 1,
                    "response": f"An unexpected error occurred: {str(e)}",
                    "session_id": request.session_id,
                    "fingure_print_id": request.agent_id,
                    "bot_id": request.agent_id,
                    "image_data": None,
                    "sources": None,
                    "supported_ai_model_name": llm_config.get('model', 'unknown'),
                    "response_id": response_id,
                    "created_at": datetime.now(),
                    "input_token_count": len(request.message)
                }
                print(f"[DEBUG] Saving error data: {data}")
                save_ai_request(request_data=data)

            return {"text": f"An unexpected error occurred: {str(e)}"}

    finally:
        print("[DEBUG] Strands RAG function completed")
        if db:
            print("[DEBUG] Closing DB connection")
            db.close()
        if g:
            print("[DEBUG] Closing generator")
            g.close()


async def generate_rag_response_strands_streaming_v2(
    request: GenerateAgentChatSchema, 
    db, 
    response_id: str = None,
    g=None,
    user_id=None
):
    """
    Streaming version of generate_rag_response_strands
    Yields chunks of response data as they are generated
    """
    function_start_time = time.time()
    print("[DEBUG] Entered generate_rag_response_strands_streaming_v2")
    print(f"[DEBUG] Request: {request}")
    print(f"[DEBUG] Response ID: {response_id}")
    print(f"[DEBUG] Generator: {g}")

    try:
        if not isinstance(request.session_id, str):
            print("[ERROR] Invalid session ID format")
            yield "data:Invalid session ID format. It should be a UUID or timestamp in string format.\n\n"
            return

        print("[DEBUG] Fetching agent data...")
        gpt_data = fetch_ai_agent_data(agent_id=request.agent_id)
        print(f"[DEBUG] gpt_data: {gpt_data}")

        if not gpt_data:
            print("[ERROR] No agent data found")
            yield {
                "error": "No agent data found", 
                "status_code": 404,
                "finished": True
            }
            return

        gpt_details = gpt_data

        agent_environment = get_environment_data(env_id=gpt_data['environment'])
        name = gpt_details['name']
        print(f"[DEBUG] Agent name: {name}")

        agent_tools = agent_environment['tools']
        tools = []
        for tool in agent_tools:
            tools.append(
                {
                    "name": tool['apiName'],
                    "config": tool['config']
                }
            )
        agent_features = agent_environment['features'] if "features" in agent_environment else []
        functions = agent_environment.get('functions', [])
        llm_config = agent_environment['llm_config']
        schema = agent_environment.get('schema', None)
        additional_instruction = gpt_details['instructions']
        system_prompt = gpt_details['system_prompt']
        model_vendor_client_id = 1
        is_structured_output = llm_config.get('is_structured_output', False)
        print(f'[DEBUG]structured_ot: {gpt_details.get("is_structured_output", False)}')
        print(f"[DEBUG] is_structured_output: {is_structured_output}")
        
        if is_structured_output:
            structured_output = gpt_details.get('structured_output', [])
            response_model = create_dynamic_model(structured_output)

        print(f"[DEBUG] tools: {tools}, agent_features: {agent_features}, llm_config: {llm_config}, additional_instruction: {additional_instruction}, system_prompt: {system_prompt}, model_vendor_client_id: {model_vendor_client_id}")

        is_humanizer_present = any(obj.get("type") == "HUMANIZER" for obj in agent_features)
        is_reflective_present = any(obj.get("type") == "REFLECTION" for obj in agent_features)
        is_memory_enable = any(obj.get('type') == 'MEMORY' for obj in agent_features)

        print("[DEBUG] Creating Strands tools...")
        config_tools = create_strands_tools(tools, user_id)
        print(f"[DEBUG] config_tools: {config_tools}")

        message = request.message

        rag_context = ""
        rag_id = ""
        print("[DEBUG] Checking for RAG feature...")
        for feat in agent_environment['features']:
            if feat.get('type_value') == 3:
                rag_id = feat['config']['rag_id']
                print(f"[DEBUG] Found RAG feature, rag_id: {rag_id}")
                break

        if rag_id:
            try:
                print("[DEBUG] Fetching manage data for RAG...")
                query = {"rag_id": rag_id}
                manage_data = fetch_manage_data(search_query=query, skip=0, limit=1)
                rag_data = fetch_rag_data({"_id": ObjectId(rag_id)}, 0, 1)
                rag_id = str(manage_data['_id'])
                rag_data = list(rag_data)[0]
                top_k = rag_data.get('top_k_similarity', 3)
                rag_model = rag_data.get('embedding_model', 'text-embedding-ada-002')

                print(f"[DEBUG] manage_data: {list(manage_data)}, rag_id: {rag_id}, rag_model: {rag_model}")

                print(f"[DEBUG] Generating embedding for user query: {message[:100]}...")
                query_embedding = get_openai_embedding(message, model = rag_model)
                print(f"[DEBUG] Generated query embedding, dimension: {len(query_embedding)}")
                
                embedding_id = f"embedding_{rag_id}"
                print(f"[DEBUG] Searching Qdrant collection: {embedding_id}")
                
                client = QdrantClient(
                    api_key=settings.QDRANT_API_KEY,
                    url=settings.QDRANT_API_URL
                )
                
                search_results = client.search(
                    collection_name=embedding_id,
                    query_vector=query_embedding,
                    limit=15,
                    score_threshold=0.4,
                    with_payload=True,
                    with_vectors=False
                )

                print(f"[DEBUG] Found {len(search_results)} relevant chunks")

                relevant_contexts = []
                for result in search_results:
                    score = result.score
                    content = result.payload.get('page_content', '')
                    
                    print(f"[DEBUG] Chunk score: {score:.3f}, preview: {content[:100]}...")
                    print(len(content))
                    if content.strip():
                        relevant_contexts.append(content)

                reranked_data = cohere_client.v2.rerank(
                    model="rerank-english-v3.0",
                    documents=relevant_contexts,
                    query=message,
                    top_n=top_k
                )

                final_chunks = []

                for doc in reranked_data.results:
                    idx = doc.index
                    if doc.relevance_score > 0.1:
                        final_chunks.append(relevant_contexts[idx])
                        print(f"[DEBUG] Reranked chunk score: {doc.relevance_score:.3f}, preview: {relevant_contexts[idx]}...")

                if final_chunks:
                    rag_context += "\n\n---\n\n".join(final_chunks)
                    print(f"[DEBUG] Final RAG context length: {len(rag_context)} characters")
                else:
                    print("[DEBUG] No relevant context found above threshold")
                    
            except Exception as e:
                print(f"[ERROR] RAG context retrieval error: {e}")

        print("[DEBUG] Building system prompt...")
        if schema and rag_id:
            system_prompt = f"{system_prompt}\n\n{schema}"
        if rag_context:
            system_prompt = f"{system_prompt}\n\nContext: {rag_context}"
        if additional_instruction:
            system_prompt = f"{system_prompt}\n\n{additional_instruction}"
        if is_humanizer_present:
            system_prompt += '''
            Before providing your final answer:
                - Engages in natural, flowing conversation
                - Shows emotional intelligence and empathy
                - Maintains consistent personality
                - References relevant details from previous conversations when appropriate
                - Uses varied, natural language
                - Expresses appropriate uncertainty
            '''
        if is_reflective_present:
            system_prompt += '''
            Before providing your final answer:
                - Think through the problem step by step
                - Consider multiple perspectives and approaches
                - Verify your reasoning and check for mistakes
                - Explain your thought process
                - Highlight any uncertainties or assumptions
            '''
        system_prompt += f"\nCurrent date: {datetime.now()}"
        print(f"[DEBUG] Final system_prompt: {system_prompt[:200]}...")
        formatted_message = message
        print(f"[DEBUG] formatted_message: {formatted_message[:200]}...")

        print("[DEBUG] Getting Strands model...")
        model = get_strands_model(model_vendor_client_id=1, llm_config=llm_config)
        print(f"[DEBUG] model: {model}")

        initial_messages = []
        if is_memory_enable:            
            print("[DEBUG] Loading memory for agent...")
            try:
                memory_query = {"session_id": request.session_id}
                memory_details = fetch_ai_requests_data(query=memory_query)
                print(f"[DEBUG] memory_details: {memory_details}")
                for memory in memory_details:
                    initial_messages.extend([
                        {"role": "assistant", "content": [{'text': memory["response"]}]},
                        {"role": "user", "content": [{"text": memory["message"]}]}
                    ])
            except Exception as e:
                print(f"[ERROR] Memory loading error: {e}")

        print("[DEBUG] Creating Agent...")
        agent = Agent(
            name=name,
            model=model,
            tools=config_tools,
            system_prompt=system_prompt,
            messages=initial_messages[::-1],
            conversation_manager=SlidingWindowConversationManager(window_size=40),
            agent_id=request.session_id,
            state=AgentState({"session_id": request.session_id}),
        )

        print("[DEBUG] Agent created")


        agent_start_time = time.time()
        print("[DEBUG] Starting agent response...")
        
        async for event in agent.stream_async(formatted_message, callbacks=[ChainStreamHandler(g)]):
            if "data" in event and event["data"]:
                yield f"{event['data']}\n\n"
                await asyncio.sleep(0)
            if "result" in event and event["result"]:
                response_text = event["result"].message.get("content", "")[0].get("text", "")


        if is_reflective_present:
            yield "data:##Reflecting on response for depth and clarity...\n\n"
            
            print(f'Before reflection: {response_text[:100]}...')
            reflection_prompt = f"Reflect on your response, and provide a more in depth, focused, and verbose response. RETURN ONLY THE NEW TEXT, NO CONFIRMATION TEXT LIKE SURE THING FOR THIS REPROMPT:\n {response_text}"
            
            async for event in agent.stream_async(reflection_prompt, callbacks=[ChainStreamHandler(g)]):
                if "data" in event and event["data"]:
                    yield f"data:{event['data']}\n\n"
                    await asyncio.sleep(0)
                if "result" in event and event["result"]:
                    response_text = event["result"].message.get("content", "")[0].get("text", "")

            print(f'After reflection: {response_text[:100]}...')

        # Handle humanization if enabled
        if is_humanizer_present:
            yield "data:##Converting to human-like response...\n\n"
            
            print(f'Before humanizing: {response_text[:100]}...')
            humanized_response = ""
            humanize_prompt = f"Convert this text to a more human-written-like format, using beginner friendly english terms and slags, explaining everything that you can, again, all in human like language, asking questions along the way like, following along? or does that make sense? RETURN ONLY THE NEW TEXT, NO CONFIRMATION TEXT LIKE SURE THING FOR THIS REPROMPT:\n{response_text}"
            
            async for event in agent.stream_async(humanize_prompt, callbacks=[ChainStreamHandler(g)]):
                if "data" in event and event["data"]:
                    yield f"data:{event['data']}\n\n"
                    await asyncio.sleep(0)
                if "result" in event and event["result"]:
                    humanized_response = event["result"].message.get("content", "")[0].get("text", "")

            
            response_text = humanized_response
            print(f'After humanizing: {response_text[:100]}...')

        agent_duration = time.time() - agent_start_time
        print(f"[DEBUG] Agent processing completed in {agent_duration:.2f} seconds for {name}")

        response_text = response_text.replace('json', "").replace('```', "")
        print(f"[DEBUG] Cleaned response_text: {response_text[:200]}...")

        data = {
            "message": request.message,
            "project_type": 1,
            "request_id": 1,
            "response": response_text,
            "session_id": request.session_id,
            "fingure_print_id": request.agent_id,
            "bot_id": request.agent_id,
            "image_data": None,
            "sources": None,
            "supported_ai_model_name": llm_config['model'],
            "response_id": response_id,
            "created_at": datetime.now(),
            "input_token_count": len(request.message)
        }

        print(f"[DEBUG] Saving AI request data: {data}")
        save_ai_request(request_data=data)

        total_duration = time.time() - function_start_time
        print(f"[DEBUG] Total execution time: {total_duration:.2f} seconds")
        print("[DEBUG] Returning final response")
        
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        line_number = tb[-1].lineno
        filename = tb[-1].filename
        print(f"[ERROR] Error occurred: {e} at line {line_number} in {filename}")

        error_message = str(e).lower()

        if "insufficient_quota" in error_message or "quota exceeded" in error_message:
            print("[ERROR] API credit limit exceeded")
        else:
            print("[ERROR] Unexpected error, saving to DB if possible")
            data = {
                "message": request.message,
                "project_type": 1,
                "request_id": 1,
                "response": f"An unexpected error occurred: {str(e)}",
                "session_id": request.session_id,
                "fingure_print_id": request.agent_id,
                "bot_id": request.agent_id,
                "image_data": None,
                "sources": None,
                "supported_ai_model_name": llm_config.get('model', 'unknown') if 'llm_config' in locals() else 'unknown',
                "response_id": response_id,
                "created_at": datetime.now(),
                "input_token_count": len(request.message)
            }
            print(f"[DEBUG] Saving error data: {data}")
            save_ai_request(request_data=data)

            yield f"data:An unexpected error occurred: {str(e)}\n\n"

    finally:
        print("[DEBUG] Strands RAG streaming function completed")
        if db:
            print("[DEBUG] Closing DB connection")
            db.close()
        if g:
            print("[DEBUG] Closing generator")
            g.close()


async def generate_rag_response_strands_streaming(
    request: GenerateAgentChatSchema, 
    db, 
    response_id: str = None,
    g= None,
    user_id=None
):
    try:
        request.stream = False
        print(request)
        response_text = await generate_rag_response_strands(request,db,response_id, g)
        for i in response_text:
            yield f"data:{i}\n\n"
            asyncio.sleep(0)
    except Exception as e:
        print(f"[ERROR] ERROR WHILE STREAMING : {e}")

def main():
    from unittest.mock import MagicMock
    import sys
    import asyncio

    mock_db = MagicMock()
    mock_session_data = MagicMock()
    mock_session_data.token = "dummy_token"
    mock_session_data.user_id = "dummy_user"
    mock_db.query().filter().order_by().first.return_value = mock_session_data

    this_module = sys.modules[__name__]
    this_module.fetch_ai_agent_data = MagicMock(
        return_value=[
            {
                'account_id': 'acc',
                'project_id': 'proj',
                'name': 'TestAgent',
                'tools': [
                    {
                        'name': 'crawl4ai_tools',
                        'config': {}
                    }
                ],
                'features': [],
                'functions': [],
                'llm_config': {'model': 'gpt-4.1-nano'},
                'additional_instruction': '',
                'system_prompt': 'You are a helpful assistant.',
                'modelVendorClientId': 1,
                'webhooks': []
                
            }
        ]
    )

    this_module.save_ai_requests_data = MagicMock()
    request = GenerateAgentChatSchema(
        message="Crawl this website: https://appscrip.com, and let me know the summary of the content",
        session_id="user-123",
        agent_id="64e4e9f2b7e6c8a1b2c3d4e5", 
        stream=True
    )

    async def handle_stream():
        async for response in generate_rag_response_strands_streaming(request, mock_db):
            print(response, flush=True, end ="")

    asyncio.run(handle_stream())

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

def send_webhook_notification(webhook_id: str, response_text: str, response_id: str) -> None:
    """
    Sends a webhook notification with the response text and ID.
    
    Args:
        webhook_id (str): The ID of the webhook configuration
        response_text (str): The text response to send
        response_id (str): The ID of the response
    """
    webhook_query = {
        "_id": ObjectId(webhook_id)
    }
    webhooksettings = fetch_webhook_data(query=webhook_query)
    
    if webhooksettings is not None:
        try:
            if webhooksettings['auth_type'] == 1:
                headers = {
                    "Content-Type": "application/json"
                }
            elif webhooksettings['auth_type'] == 2:
                headers = {
                    "username": webhooksettings["config"]["username"],
                    "password": webhooksettings["config"]["password"],
                    "Content-Type": "application/json"
                }
            elif webhooksettings['auth_type'] == 3:
                headers = {
                    "Authorization": webhooksettings["config"]["token"],
                    "Content-Type": "application/json"
                }
            else:
                headers = {
                    "Content-Type": "application/json"
                }
                
            print(f"Webhook URL: {webhooksettings['url']}")
            print(f"response_id: {response_id}")
            response = requests.post(
                url=webhooksettings['url'],
                headers=headers,
                json={
                    "text": response_text,
                    "response_id": response_id
                }
            )
            print(f"Webhook response: {response.status_code}")
        except Exception as e:
            print(f"Error sending webhook: {str(e)}")


if __name__ == "__main__":
    main()