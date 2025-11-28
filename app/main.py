import os
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from app.quiz_solver import solve_quiz_task
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/run")
async def run_quiz(request: QuizRequest, background_tasks: BackgroundTasks):
    # Verify secret
    # In a real scenario, we might check against a stored secret.
    # Here we assume the user sets STUDENT_SECRET env var to match what they submitted.
    # If not set, we might skip or warn.
    expected_secret = os.environ.get("STUDENT_SECRET")
    if expected_secret and request.secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    # Start background task
    background_tasks.add_task(solve_quiz_task, request.email, request.secret, request.url)
    
    return {"message": "Quiz processing started", "status": "processing"}

@app.get("/")
async def root():
    return {"message": "LLM Analysis Quiz Agent is running"}
