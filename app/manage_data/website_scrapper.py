import requests
import os
from langchain_community.embeddings import OpenAIEmbeddings
from datetime import datetime
from langchain_qdrant import QdrantVectorStore
from langchain.text_splitter import CharacterTextSplitter
from app.manage_data.scrap_sitemaps import find_all_urls, clean_and_extract_content
from langchain.text_splitter import CharacterTextSplitter
import re
from qdrant_client.http.models import PointStruct, VectorParams
from qdrant_client import QdrantClient
from openai import OpenAI
from langchain_core.documents import Document
from app.api.v1.endpoints.chat.db_helper import save_website_scrapper_logs, update_website_scrapper_logs
from firecrawl import FirecrawlApp, ScrapeOptions

FIRECRAWL_API_KEY=settings.FIRECRAWL_API_KEY

firecrawl_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

client = OpenAI()
import uuid
from app.core.config import settings

embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
os.environ["OPENAI_API_TYPE"] = "openai"
qdrant_api_url = settings.QDRANT_API_URL
qdrant_api_key = settings.QDRANT_API_KEY

embeddings_dimension = 1536

qdrant_client = QdrantClient(
    url=qdrant_api_url,
    api_key=qdrant_api_key,
    timeout=300
)

TAGS_TO_MARKDOWN = {
    'h1': '#',
    'h2': '##',
    'h3': '###',
    'h4': '####',
    'h5': '#####',
    'h6': '######',
    'p': ''
}


def _create_embeddings(input: str):
    results = client.embeddings.create(
        input=[input],
        model="text-embedding-ada-002"
    )
    # dimensions=embeddings_dimension)
    content = results.data[0]
    return content


# Function to clean text by removing extra spaces, newlines, tabs, etc.
def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()


def remove_extra_spaces(input_string):
    return ' '.join(input_string.split())


def clean_strings(string_list):
    return [remove_extra_spaces(s) for s in string_list]


def process_element(element):
    """Recursively convert an element and its children to Markdown."""
    markdown = ""
    if element.name in TAGS_TO_MARKDOWN:
        # Prepend the Markdown equivalent of the current tag
        prefix = TAGS_TO_MARKDOWN[element.name] + ' ' if element.name != 'ul' else ''
        if element.name == 'li':
            markdown += prefix + element.get_text(strip=True) + '\n'
        else:
            markdown += prefix + element.get_text(strip=True) + '\n\n'

    # Recursively process each child that is a tag and not just string
    for child in element.children:
        if child.name:
            markdown += process_element(child)

    return markdown


def scrap_website(account_id, knowledge_source, user_id, max_crawl_depth: int = 1, max_crawl_page: int = 1, dynamic_wait: int = 5):
    print("inside scrap data")
    embedding_id = f"{str(account_id)}"

    # Define chunk size and overlap based on recommendations
    chunk_size = 5000
    # separators = ["\n", "\n\n", "\r", "\r\n", "\n\r", "\t", " ", "  "]
    chunk_overlap = 0  # 100-150 tokens overlap

    # Define the text splitter
    text_splitter = CharacterTextSplitter(separator="\n\n", chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                                          length_function=len)

    scrap_data_id = account_id
    print(f"scrap_data_id {scrap_data_id}")

    if qdrant_client.collection_exists(embedding_id):
        qdrant_client.delete_collection(embedding_id)
        print(f"Collection deleted in Qdrant.........!!!!!!!!! {embedding_id}")

    if not qdrant_client.collection_exists(embedding_id):
        qdrant_client.create_collection(
            collection_name=embedding_id,
            vectors_config=VectorParams(size=embeddings_dimension, distance='Cosine')
        )
        print(f"Collection created in Qdrant.........!!!!!!!!! {embedding_id}")

    try:
        url = knowledge_source  # Replace with the actual URL
        crawl_result = firecrawl_app.crawl_url(
            url, 
            limit=max_crawl_page,
            max_depth=max_crawl_depth,
            scrape_options=ScrapeOptions(
                formats=['markdown'],
                maxAge=3600000  # Use cached data if less than 1 hour old
            )
        )
        for page in crawl_result.data:
            url = page.metadata['url']
            metadata = page.metadata
            content_data = page.markdown
            generate_logs = {
                "rag_id": account_id,
                "created_at": datetime.now(),
                "link": url,
                "page_content": "",
                "status": "INPROGRESS"
            }
            save_website_scrapper_logs(data=generate_logs)
            print("Loader completed")
            p_uuid = str(uuid.uuid4())
            cleaned_doc = Document(page_content=content_data, metadata=metadata)
            # Split the cleaned text into chunks
            text_chunks = text_splitter.split_documents([cleaned_doc])
            QdrantVectorStore.from_documents(
                text_chunks,
                embeddings,
                ids=[p_uuid],
                url=qdrant_api_url,
                api_key=qdrant_api_key,
                prefer_grpc=True,
                collection_name=embedding_id,
                force_recreate=False,
            )
            print(f"data stored in qdrant {embedding_id}")
            update_logs = {
                "rag_id": account_id,
                "link": url,
                "page_content": url,
                "status": "SUCCESS"
            }
            update_website_scrapper_logs(data=update_logs)
    except Exception as e:
        print("e", e)

    print(f'File Scrapped Successfully')
    return True
