import requests
from langchain_community.document_loaders import WebBaseLoader
from typing import Optional

import logging
from rich.logging import RichHandler

# Configure basic config with RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s", # Rich handles the timestamp and level separately
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("ingestion")

# Function 1: Extract Text from Job Description URL
"""
Pending wrapper Funtion to validate and sanitize the input 
"""


def get_jd_from_url(url) -> Optional[str]:
    """

    :param url:
    :return:
    """
    try:
        logger.info(f"ℹ️ Loading URL .. {url}")
        loader = WebBaseLoader(url,
                               raise_for_status=True,
                               requests_kwargs={
                                   "headers": {
                                       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                                   },
                               }
                               )
        docs = loader.load()
        # Conbine content from all pages found (maybe just one)
        return " ".join([d.page_content for d in docs])
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error fetching URL: {e}")
        return None
0

# Function 2: Extract Text from Uploaded PDF
def get_pdf_text_pypdf(uploaded_file, verbose=False) -> Optional[tuple]:
    import pypdf
    try:
        # Read the PDF file directly from the stream
        logger.info(f"ℹ️ Reading PDF. {uploaded_file.name}")
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        if verbose:
            logger.info(f"Extracted Text\n\n {text}")
        return text
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return None


def get_pdf_text_pdfplumber(uploaded_file, verbose=False)-> Optional[tuple]:
    import pdfplumber
    try:
        logger.info(f"ℹ️ Reading PDF. {uploaded_file.name}")
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
            if verbose:
                logger.info(f"Extracted Text\n\n {text}")
            return text
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return None
