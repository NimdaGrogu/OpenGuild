from langchain_community.document_loaders import WebBaseLoader
from playwright.async_api import async_playwright
from typing import Optional
from rich.logging import RichHandler
import logging, requests
import asyncio


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
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler()])
    logger = logging.getLogger("scraper")

    def clean_text_output(raw_text: str) -> str:
        """Removes excessive blank lines and trailing spaces for clean RAG ingestion."""
        lines = (line.strip() for line in raw_text.splitlines())
        # Drop empty lines, but keep paragraph breaks (single blank lines)
        chunks = (line for line in lines if line)
        return "\n\n".join(chunks)

    async def main_playwright_scraper(url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                logger.info(f"🚀 Loading dynamic page: {url}")
                # 'networkidle' is safer here because we don't know the specific selector to wait for
                await page.goto(url, wait_until="networkidle", timeout=25000)

                logger.info("🧹 Injecting JavaScript to strip boilerplate DOM elements...")

                # 1. Execute JS in the browser to permanently delete non-content nodes
                await page.evaluate("""() => {
                    const selectorsToRemove = [
                        'header', 'footer', 'nav', 'aside', 'noscript', 
                        'script', 'style', 'iframe', 'svg', 'form', 'button',
                        '[role="banner"]', '[role="navigation"]', '[role="contentinfo"]',
                        '.cookie-banner', '#cookie-notice'
                    ];
                    document.querySelectorAll(selectorsToRemove.join(',')).forEach(el => el.remove());
                }""")

                # 2. Try to find semantic 'main' content areas first
                semantic_selectors = ['main', '[role="main"]', '#content', '#main-content','text=Job Description']

                for selector in semantic_selectors:
                    locator = page.locator(selector).first
                    count = await locator.count()
                    logger.info(f"🎯 Checking selector count '{selector}': {count}")

                    if await locator.count() > 0:
                        text = await locator.inner_text()
                        # A typical JD is at least 500 characters. If it's too short, it might be a false positive.
                        trimmed_text = text.strip()
                        if len(trimmed_text) > 400:
                            logger.info(f"🎯 Successfully found content inside semantic tag: {selector}")
                            return clean_text_output(text)
                        else:
                            # Too short. Log the beginning of text for debugging if needed.
                            snippet = trimmed_text[:100].replace('\n', ' ')
                            logger.warning(
                                f"⚠️ Content found via '{selector}' too short ({len(trimmed_text)} chars). Snippet: '{snippet}...'")

                # 3. The Ultimate Fallback: Grab the whole body
                # since the header/footer/nav, was deleted the body should mostly just be the JD.
                logger.warning("⚠️ Semantic tags failed. Falling back to cleaned <body> extraction. (potential noise).")
                text = await page.locator('body').inner_text()
                return clean_text_output(text)

            except Exception as e:
                logger.error(f"❌ Dynamic Extraction Failed: {e}")
                return "None"
            finally:
                await browser.close()

    return asyncio.run(main_playwright_scraper(url))


def get_jd_from_url(url) -> Optional[str]:
    """

    :param url:
    :return:
    """
    try:
        logger.info(f"ℹ️  Loading URL .. {url}")
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

