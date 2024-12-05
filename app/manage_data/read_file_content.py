import requests
from PyPDF2 import PdfReader
from io import BytesIO
import json
import os
from os.path import join, dirname
from llama_parse import LlamaParse
import pymupdf4llm
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from app.core.config import settings
from langchain.schema import Document
from datetime import datetime
from app.api.v1.endpoints.chat.db_helper import save_website_scrapper_logs, update_website_scrapper_logs

qdrant_api_url = settings.QDRANT_API_URL
qdrant_api_key = settings.QDRANT_API_KEY
llama_cloud_api_key = settings.LLAMA_CLOUD_API_KEY

parser = LlamaParse(
    api_key=llama_cloud_api_key,  # can also be set in your env as LLAMA_CLOUD_API_KEY
    result_type="markdown",  # "markdown" and "text" are available
    num_workers=4,  # if multiple files passed, split in `num_workers` API calls
    verbose=True,
    language="en",  # Optionally you can define a language, default=en
)


def read_file_from_url(url):
    # Send a GET request to download the file
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        return f"Failed to download the file. Status code: {response.status_code}"

    # Get the content type from the headers
    content_type = response.headers.get('Content-Type')
    print("content_type", content_type)

    # Handle PDF files
    try:
        return read_pdf(response.content)
    except:
        try:
            return read_json(response.content)
        except:
            try:
                return response.text  # Directly return the text content
            except:
                return "Unsupported file type"


def read_pdf(content):
    # Use BytesIO to load the content as a file-like object
    pdf_content = BytesIO(content)

    # Read the PDF content
    reader = PdfReader(pdf_content)
    text = ''

    # Extract text from all the pages
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text()

    return text


def read_json(content):
    # Decode the JSON content
    try:
        json_content = json.loads(content.decode('utf-8'))
        return json.dumps(json_content, indent=4)  # Pretty-print JSON
    except json.JSONDecodeError:
        return "Invalid JSON content"


# Example usage
def file_data(url, rag_manage_id):
    # Make a GET request to the URL
    response = requests.get(url)

    # Local path where you want to save the file (including the file name)
    local_filename = join(dirname(__file__)) + "/" + str(rag_manage_id) + ".pdf"

    # Open the local file in write-binary mode and save the content
    with open(local_filename, 'wb') as file:
        file.write(response.content)

    page_content = ""
    try:
        documents = parser.load_data(local_filename)
        for _i in documents:
            if page_content == "":
                page_content = _i.text
            else:
                page_content = page_content + "\n" + _i.text
    except:
        page_content = pymupdf4llm.to_markdown(local_filename)

    generate_logs = {
        "rag_id": rag_manage_id,
        "created_at": datetime.now(),
        "link": url,
        "page_content": "",
        "status": "INPROGRESS"
    }
    save_website_scrapper_logs(data=generate_logs)

    text_splitter = CharacterTextSplitter(separator="\n\n", chunk_size=5000, chunk_overlap=0, length_function=len)
    docs = [Document(page_content=page_content)]
    text_chunks = text_splitter.split_documents(docs)

    QdrantVectorStore.from_documents(
        text_chunks,
        embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
        url=qdrant_api_url,
        api_key=qdrant_api_key,
        prefer_grpc=True,
        collection_name=f"{str(rag_manage_id)}",
        force_recreate=True,
    )
    print(f'File downloaded and saved as {local_filename}')
    update_logs = {
        "rag_id": rag_manage_id,
        "link": url,
        "page_content": page_content,
        "status": "SUCCESS"
    }
    update_website_scrapper_logs(data=update_logs)
    os.remove(local_filename)
    return page_content, page_content
