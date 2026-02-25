import requests
from langchain_community.document_loaders import WebBaseLoader

import logging
import asyncio
from typing import Optional
from langchain_community.document_loaders import PlaywrightURLLoader
from rich.logging import RichHandler
from bs4 import BeautifulSoup

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
Pending wrapper Function to validate and sanitize the input 
"""


def get_jd_with_playwright(url: str) -> Optional[str]:
    """
    Uses a headless browser to load JS-heavy job boards.
    """
    try:
        logger.info(f"🚀 Launching browser for: [bold cyan]{url}[/bold cyan]", extra={"markup": True})

        # remove_selectors helps strip out nav, footers, and scripts automatically
        loader = PlaywrightURLLoader(
            urls=[url],
            remove_selectors=["header", "footer", "nav", ".cookie-banner", "script", "style"],
        )

        # PlaywrightURLLoader.load() is synchronous, but uses asyncio under the hood
        docs = loader.load()

        if not docs or len(docs[0].page_content) < 200:
            logger.warning("⚠️ Content seems too short. The page might still be loading or blocked.")
            return None

        # Clean up the whitespace and formatting
        raw_text = docs[0].page_content
        lines = (line.strip() for line in raw_text.splitlines())
        clean_text = "\n".join(chunk for chunk in lines if chunk)

        logger.info(f"✅ Successfully extracted {len(clean_text)} characters.")
        if clean_text:
            logger.info("\n--- EXTRACTED CONTENT PREVIEW ---")
            logger.info(clean_text[:1000])  # Print first 1000 characters
        return clean_text

    except Exception as e:
        logger.error(f"❌ Playwright Error: {e}")
        return None


def get_jd_from_url(url) -> Optional[str]:
    """

    :param url:
    :return:
    """
    from urllib.parse import urlparse


    try:
        url_validation = urlparse(url)
        # Check if it has both a scheme (http/https) and a network location (domain)
        all([url_validation.scheme, url_validation.netloc])
        logger.info(f"ℹ️  Loading URL .. {url}")
        loader = WebBaseLoader(url,
                               raise_for_status=True,
                               requests_kwargs={
                                   "headers": {
                                       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                                   },
                               },
                               show_progress=True
                               )
        docs = loader.load()
        # Combine content from all pages found (maybe just one)
        return " ".join([d.page_content for d in docs])
    except Exception as e:
        logger.error(f"❌ Error Format URL: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Error fetching URL: {e}")
        return None


# Function 2: Extract Text from Uploaded PDF
def get_pdf_text_pypdf(uploaded_file, verbose=False) -> Optional[tuple]:
    import pypdf
    try:
        # Read the PDF file directly from the stream
        logger.info(f"ℹ️  Reading PDF. {uploaded_file.name}")
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        if verbose:
            logger.info(f"ℹ️  Extracted Text\n\n {text}")
        return text
    except Exception as e:
        logger.error(f"☠️ Error reading PDF: {e}")
        return None


def get_pdf_text_pdfplumber(uploaded_file, verbose=False)-> Optional[tuple]:
    import pdfplumber
    try:
        #logger.info(f"ℹ️  Reading PDF: {uploaded_file.name}")
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
            if verbose:
                logger.info(f"Extracted Text\n\n {text}")
            return text
    except Exception as e:
        logger.error(f"☠️ Error reading PDF: {e}")



def get_pdf_text_pymupdf(uploaded_file, split_ratio=0.35, verbose=False)-> str | None:
    import fitz
    logger.info(f"ℹ️  Reading PDF: {uploaded_file.name}")
    try:
        # Uploaded_file is a Streamlit UploadedFile object
        uploaded_file.seek(0)  # Reset pointer to start just in case
        # Read bytes from the stream and tell fitz it's a PDF
        uploaded_file_bytes = uploaded_file.read()
        with fitz.open(stream=uploaded_file_bytes, filetype="pdf") as pdf:
            full_text = []
            for page in pdf:
                w, h = page.rect.width, page.rect.height

                # split page into 2 columns
                split_x = w * split_ratio

                left_rect = fitz.Rect(0, 0, split_x, h)
                right_rect = fitz.Rect(split_x, 0, w, h)

                # extract blocks per column
                left_blocks = page.get_text("blocks", clip=left_rect)
                right_blocks = page.get_text("blocks", clip=right_rect)

                # sort blocks top → bottom
                left_blocks = sorted(left_blocks, key=lambda b: (b[1], b[0]))
                right_blocks = sorted(right_blocks, key=lambda b: (b[1], b[0]))

                # add text in reading order
                for b in left_blocks:
                    full_text.append(b[4].strip())

                for b in right_blocks:
                    full_text.append(b[4].strip())

        return "\n".join(full_text)
    except Exception as e:
        logger.error(f"☠️  Error reading PDF: {e}")
        return None


