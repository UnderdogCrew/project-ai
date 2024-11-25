import requests
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import hashlib


def generate_embedding(text):
    """Generate a simple hash-based embedding for demonstration purposes."""
    return int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16) % (10 ** 8)


def is_xml(response):
    return 'xml' in response.headers.get('Content-Type', '')


def fetch_url(url, headers):
    try:
        response = requests.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response
    except requests.RequestException as e:
        print(f"Error accessing {url}: {e}")
    return None


def parse_sitemap(url, headers):
    response = fetch_url(url, headers)
    if response and is_xml(response):
        try:
            root = ET.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            sitemap_urls = []
            actual_urls = []
            # Find all <sitemap> entries
            for sitemap in root.findall('ns:sitemap', namespace):
                loc = sitemap.find('ns:loc', namespace)
                if loc is not None:
                    sitemap_urls.append(loc.text)
            # Find all <url> entries
            for url in root.findall('ns:url', namespace):
                loc = url.find('ns:loc', namespace)
                if loc is not None:
                    actual_urls.append(loc.text)
            return sitemap_urls, actual_urls
        except ET.ParseError as e:
            print(f"Error parsing XML from {url}: {e}")
    return [], []


def find_all_urls(domain):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    sitemap_urls = [
        f"{domain}/sitemap.xml",
        f"{domain}/sitemap_index.xml",
        f"{domain}/robots.txt"
    ]

    discovered_sitemaps = set()
    actual_urls = set()

    def discover_sitemaps(url):
        if url in discovered_sitemaps:
            return
        discovered_sitemaps.add(url)
        print("url", url)
        sitemap_urls, urls = parse_sitemap(url, headers)
        actual_urls.update(urls)
        for sitemap in sitemap_urls:
            discover_sitemaps(sitemap)

    # Check standard sitemap URLs
    for url in sitemap_urls[:2]:
        response = fetch_url(url, headers)
        if response and is_xml(response):
            discover_sitemaps(url)
            break

    # Check robots.txt for sitemap URL
    robots_response = fetch_url(sitemap_urls[2], headers)
    if robots_response:
        for line in robots_response.text.splitlines():
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                full_sitemap_url = urljoin(domain, sitemap_url)
                discover_sitemaps(full_sitemap_url)

    return list(actual_urls)


def clean_and_extract_content(url):
    # Fetch webpage content
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Remove non-content elements
    for tag in soup(
            ["input", "script", "style", "header", "nav", "aside", "form", "iframe", "noscript", "button", "link",
             "meta"]):
        tag.decompose()

    # Remove non-content elements by class name
    for tag in soup.find_all(class_=["liteboxFormat3Circle"]):
        tag.decompose()

    # Remove non-content elements by ID
    for tag in soup.find_all(id=["liteboxFormat3Circle"]):
        tag.decompose()

    # Remove elements with the attribute data-elementor-type="header"
    for tag in soup.find_all(attrs={"data-elementor-type": "header"}):
        tag.decompose()

    # # Remove elements with the attribute data-elementor-type="footer"
    # for tag in soup.find_all(attrs={"data-elementor-type": "footer"}):
    #     tag.decompose()

    # Initialize structure to hold the organized content
    structured_content = []
    current_section = None
    section_start_tags = ['h2', 'h3', 'h1']  # Tags that denote the start of a new section
    seen_vectors = set()  # Set to track vectors already added

    # Define tags of interest for content extraction
    content_tags = ['p', 'span', 'li', 'article', 'section', 'div']  # Exclude 'div' from the list
    title = soup.title.string.strip() if soup.title else ''

    # Iterate over elements to organize them under section start tags
    for element in soup.find_all(['h1', 'h2', 'p', 'span', 'li', 'article', 'section', 'div', 'h3', 'h4', 'h5']):
        if element.name in section_start_tags:
            # Start a new section if a primary section tag is encountered
            text = element.get_text(strip=True)
            vector = generate_embedding(text)
            if vector not in seen_vectors:
                seen_vectors.add(vector)
                current_section = {
                    "heading": element.name,
                    "title": text,
                    "vector": vector,
                    "content": [],
                    "url": url,
                    "page_title": title
                }
                structured_content.append(current_section)
        elif current_section and element.name in content_tags:
            # Collect content under the current section
            text = element.get_text(" ", strip=True)
            if text:
                vector = generate_embedding(text)
                if vector not in seen_vectors:
                    seen_vectors.add(vector)
                    content_data = {
                        "tag": element.name,
                        "text": text,
                        "vector": vector
                    }
                    current_section['content'].append(content_data)

    # Extract metadata
    description = soup.find('meta', attrs={'name': 'description'})['content'].strip() if soup.find('meta', attrs={
        'name': 'description'}) else ''
    language = soup.find('html')['lang'] if soup.find('html') and 'lang' in soup.find('html').attrs else ''

    # Construct metadata object
    metadata = {
        "source": url,
        "title": title,
        "description": description,
        "language": language
    }

    # Convert structured content to Markdown format
    markdown_content = ""
    tags_to_markdown = {
        'h1': '#',
        'h2': '##',
        'h3': '###',
        'h4': '####',
        'h5': '#####',
        'h6': '######',
        'p': ''
    }
    for section in structured_content:
        markdown_content += f"{tags_to_markdown.get(section['heading'], '##')} {section['title']}\n"
        for content in section['content']:
            markdown_content += f"{tags_to_markdown.get(content['tag'], '')}{content['text']}\n\n"

    return structured_content, metadata, markdown_content
