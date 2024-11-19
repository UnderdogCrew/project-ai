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



def scrap_website(account_id, knowledge_source, user_id):
    final_links = []

    # Create a session object
    session = requests.Session()
    # Set the maximum number of redirects allowed for this session
    session.max_redirects = 50
    print("inside scrap data")
    embedding_id = f"{str(account_id)}"

    all_urls = []
    scrap_data_id = account_id

    # Define chunk size and overlap based on recommendations
    chunk_size = 5000
    # separators = ["\n", "\n\n", "\r", "\r\n", "\n\r", "\t", " ", "  "]
    chunk_overlap = 0  # 100-150 tokens overlap

    # Define the text splitter
    text_splitter = CharacterTextSplitter(separator="\n\n", chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len)

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

    
    for _source in knowledge_source:
        try:
            url = _source['source']  # Replace with the actual URL

            # need to get all url using crawlies
            final_links = find_all_urls(url) # we need to call this function to get the urls from sitemaps
            print("=================final_links==================", len(final_links))
            if len(final_links) == 0:
                final_links = [url]

            for _logs in final_links:
                generate_logs = {
                    "rag_id": account_id,
                    "created_at": datetime.now(),
                    "link": _logs,
                    "page_content": "",
                    "status": "INPROGRESS"
                }
                save_website_scrapper_logs(data=generate_logs)

            total_count = len(final_links)
            success_links = len(final_links)
            for _link in final_links:
                try:
                    print("Loader completed", total_count)
                    content_data = None
                    markdown_content = ""
                    metadata = None
                    if content_data is None:
                        content_data = ""
                        text_data, metadata, markdown_content = clean_and_extract_content(url=_link)
                        for _text in text_data:
                            text = _text['page_title'] + "\n\n" + _text['title'] + "\n\n"
                            if "content" in _text:
                                for inner_content in _text['content']:
                                    text = text + "\n" + inner_content['text']
                            else:
                                pass

                            if content_data == "":
                                content_data = text
                            else:
                                content_data = content_data + "\n" + text
                    # Remove extra spaces
                    cleaned_string = ' '.join(content_data.split())
                    total_count -= 1
                    p_uuid = str(uuid.uuid4())
                    if cleaned_string != "":
                        # Clean the text content
                        cleaned_doc = Document(page_content=cleaned_string, metadata=metadata)
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
                            "link": _link,
                            "page_content": cleaned_string,
                            "status": "SUCCESS"
                        }
                        update_website_scrapper_logs(data=update_logs)

                except Exception as e:
                    print("reason", e)
                    success_links -= 1
        except Exception as e:
            print("e", e)

    print(f'File Scrapped Successfully')
    return True