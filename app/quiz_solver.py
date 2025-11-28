import asyncio
import json
import logging
import re
import os
import base64
from playwright.async_api import async_playwright
from app.llm_utils import chat_with_llm
import httpx

logger = logging.getLogger(__name__)

async def solve_quiz_task(email: str, secret: str, start_url: str):
    logger.info(f"Starting quiz task for {email} at {start_url}")
    print(f"\n🚀 Starting quiz task for {email}")
    print(f"🔗 Initial URL: {start_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        current_url = start_url
        
        while current_url:
            logger.info(f"Navigating to {current_url}")
            print(f"\n🌐 Navigating to: {current_url}")
            try:
                await page.goto(current_url)
                # Wait for content to load. The sample shows JS decoding.
                # We'll wait for network idle or a specific element if known.
                # For now, wait for networkidle and maybe a small sleep or check for text.
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2) # Extra buffer for JS execution
                
                # Extract content
                # We'll get the full body text or specific container if we can identify it.
                # The sample had id="result". Let's try to find that or fallback to body.
                content = ""
                if await page.locator("#result").count() > 0:
                    content = await page.locator("#result").inner_text()
                else:
                    content = await page.inner_text("body")
                
                logger.info(f"Extracted content: {content[:100]}...")
                print(f"📄 Extracted page content ({len(content)} chars)")
                
                # Take screenshot for vision tasks
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                image_data_url = f"data:image/png;base64,{screenshot_b64}"
                print("📸 Captured page screenshot")
                
                # Solve the problem
                answer = await solve_problem(content, current_url, image_data_url)
                logger.info(f"Computed answer: {answer}")
                print(f"💡 Computed Answer: {answer}")
                
                # Submit answer
                # The submission URL is usually on the page, but the prompt says:
                # "Post your answer to https://example.com/submit with this JSON payload"
                # The text on the page says "Post your answer to ...".
                # We need to extract the submit URL from the text or the page.
                # The prompt says "The quiz page always includes the submit URL to use."
                
                submit_url = extract_submit_url(content)
                if not submit_url:
                    # Fallback: maybe it's the same domain?
                    # Or maybe we ask LLM to extract it.
                    submit_url = await extract_submit_url_with_llm(content)
                
                if not submit_url:
                    logger.error("Could not find submit URL")
                    break
                
                payload = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": answer
                }
                
                logger.info(f"Submitting to {submit_url} with payload {payload}")
                print(f"📤 Submitting answer to {submit_url}...")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(submit_url, json=payload, timeout=30.0)
                    
                if response.status_code != 200:
                    logger.error(f"Submission failed: {response.status_code} {response.text}")
                    # Logic to retry or stop?
                    # Prompt says: "If your answer is wrong... you are allowed to re-submit"
                    # "The endpoint will respond with a HTTP 200 and a JSON payload indicating whether your answer is correct"
                    # So 400/403/500 is a system error, 200 with correct=false is a wrong answer.
                    break
                
                result = response.json()
                logger.info(f"Submission result: {result}")
                print(f"✅ Submission Result: {result}")
                
                if result.get("correct"):
                    next_url = result.get("url")
                    if next_url:
                        current_url = next_url
                    else:
                        logger.info("Quiz completed!")
                        current_url = None
                else:
                    logger.warning(f"Incorrect answer: {result.get('reason')}")
                    print(f"❌ Incorrect Answer: {result.get('reason')}")
                    # Retry logic?
                    # For now, we'll stop to avoid infinite loops, or maybe retry once?
                    # The prompt implies we can retry.
                    # If we want to retry, we need to re-solve.
                    # Maybe we pass the error reason to the LLM?
                    # For this V1, let's just stop or maybe try one more time?
                    # I'll implement a simple retry loop inside solve_problem later if needed.
                    break
                    
            except Exception as e:
                logger.error(f"Error processing {current_url}: {e}")
                break
        
        await browser.close()

async def solve_problem(content: str, page_url: str, image_url: str = None):
    # Use LLM to understand the task and generate code
    prompt = f"""
You are an intelligent agent solving a data analysis quiz.
The current page URL is: {page_url}
The page content is:
---
{content}
---

You also have access to a screenshot of the page (provided as an image).

Your task is to:
1. Identify the question.
2. Identify any data sources (URLs to CSVs, PDFs, APIs, etc.).
3. Write and execute a Python script to solve the question.
4. Print the final answer to stdout.

IMPORTANT:
- DO NOT submit the answer to any URL.
- DO NOT use `requests.post` to submit data.
- JUST PRINT the answer.
- The answer format should be the raw value (number, string, etc.) or a JSON object if requested.

If you need to download files, use `requests`.
If you need to parse PDFs, you might need `pypdf` or similar (assume standard libs or common ones installed).
If you need to calculate something, do it in Python.

For this interaction, please output the PYTHON CODE to solve the problem.
I will execute it and return the result.
Wrap the code in ```python ... ```.
"""
    # Step 1: Get code from LLM
    llm_response = chat_with_llm(prompt, image_url=image_url)
    if not llm_response:
        return None
    
    # Extract code
    code_match = re.search(r"```python\n(.*?)```", llm_response, re.DOTALL)
    if not code_match:
        # Maybe the LLM just gave the answer?
        return llm_response.strip()
    
    code = code_match.group(1)
    
    # Execute code
    # We need to capture stdout or the return value.
    # We'll wrap the code to print the result.
    logger.info(f"Generated code:\n{code}")
    print(f"\n--- LLM Generated Code ---\n{code}\n--------------------------\n")
    
    try:
        # Create a safe-ish local scope
        local_scope = {}
        # We might need to handle imports.
        # The code should import what it needs.
        
        # Capture stdout
        import io
        import sys
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        
        exec(code, {}, local_scope)
        
        sys.stdout = old_stdout
        output = redirected_output.getvalue().strip()
        
        print(f"--- Code Output ---\n{output}\n-------------------\n")
        
        # If the code printed something, use that.
        # If not, check if 'answer' variable exists?
        if output:
            return parse_answer(output)
        elif 'answer' in local_scope:
            return local_scope['answer']
        else:
            return None
            
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return None

def parse_answer(output):
    # Try to parse as JSON, float, int, or string
    try:
        return json.loads(output)
    except:
        try:
            return float(output)
        except:
            return output

def extract_submit_url(content):
    # Simple regex to find "Post your answer to (url)"
    # or look for the JSON payload example which usually contains the url.
    # "url": "https://example.com/quiz-834" -> this is the quiz url, not submit url.
    # The text says "Post your answer to https://example.com/submit"
    match = re.search(r"Post your answer to (https?://[^\s]+)", content)
    if match:
        return match.group(1).rstrip('.,;')
    return None

async def extract_submit_url_with_llm(content):
    prompt = f"Extract the submission URL from this text. Return ONLY the URL.\n\n{content}"
    return chat_with_llm(prompt).strip()
