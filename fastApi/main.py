from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    repo_url: str

@app.get("/")
def read_root():
    return {"message": "Service is running. Use POST /scrape endpoint with repo_url parameter."}

@app.post("/scrape")
def scrape_gitingest(request: RepoRequest):
    logger.info(f"Received request to scrape: {request.repo_url}")

    if not request.repo_url or "github.com" not in request.repo_url:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            page = browser.new_page()
            gitingest_url = request.repo_url.replace("github.com", "gitingest.com")
            logger.info(f"Navigating to: {gitingest_url}")

            page.goto(gitingest_url)
            logger.info("Page loaded")

            page_source = page.content()
            # logger.info(f"Full page data scraped: {page_source}")

            # Simulate form submission
            logger.info("Filling and submitting form...")
            page.fill("#input_text", gitingest_url.split("gitingest.com/")[1])  # Extract repo part
            page.click("button[type=submit]")

            # Wait for loader to disappear
            logger.info("Waiting for loading to complete...")
            page.wait_for_selector(".loader", state="detached", timeout=60000)

            logger.info("Waiting for directory structure...")
            dir_structure = page.wait_for_selector("#directory-structure-container", timeout=30000).text_content()
            # logger.info(f"Directory structure found: {dir_structure}")

            logger.info("Waiting for code content...")
            code_content = page.wait_for_selector(".result-text", timeout=30000).text_content()
            # logger.info(f"Code content found: {code_content}")

            browser.close()

            return {
                "directory_structure": dir_structure,
                "code_content": code_content
            }
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
