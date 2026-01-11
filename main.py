from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import uuid
from datetime import datetime

# IMPORT YOUR MODULES
# Ensure these files (ai_service.py, logic.py) are in the same folder
from ai_service import get_bedrock_response, create_negotiation_prompt, get_evaluation
from logic import generate_deal_parameters, format_deal_parameters, detect_deal_readiness

app = FastAPI(title="AI Negotiator", version="1.0.0")

# CORS Setup (Allows your frontend to talk to this backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class NewSessionRequest(BaseModel):
    student_id: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: str
    user_input: str

# NEW: Model for the evaluation request
class EvaluateRequest(BaseModel):
    session_id: str
    final_terms: Dict  # Expects data like: {price: 50, delivery: 30, volume: 10000}

# --- IN-MEMORY STORAGE ---
# (Note: This resets if the Lambda goes cold. For production, use DynamoDB)
sessions = {}

# --- ENDPOINTS ---

@app.get("/")
def root():
    return {"message": "AI Negotiator API", "status": "running"}

@app.post("/api/sessions/new")
def create_session(request: NewSessionRequest):
    session_id = str(uuid.uuid4())
    
    # 1. Generate Smart Parameters (using logic.py)
    deal_params = generate_deal_parameters(request.student_id)
    
    # 2. Format them for the AI (using logic.py)
    deal_params_str = format_deal_parameters(deal_params)
    
    greeting = f"Hello! I'm Alex from ChipSource Inc. We are looking to sell our CS-1000 chips. Our standard opening is ${deal_params['price']['opening']} per unit with {deal_params['delivery']['opening']}-day delivery. What works for you?"
    
    # 3. Save Session
    sessions[session_id] = {
        "session_id": session_id,
        "deal_params": deal_params,
        "deal_params_str": deal_params_str,
        "conversation": [{"role": "assistant", "content": greeting}],
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "session_id": session_id,
        "deal_params": deal_params,
        "greeting": greeting
    }

@app.post("/api/chat")
def chat(request: ChatRequest):
    if request.session_id not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[request.session_id]
    
    # 1. Add User Input
    session["conversation"].append({"role": "user", "content": request.user_input})
    
    # 2. Get AI Response
    prompt = create_negotiation_prompt(
        request.user_input,
        session["deal_params_str"],
        session["conversation"]
    )
    
    ai_response = get_bedrock_response(prompt)
    session["conversation"].append({"role": "assistant", "content": ai_response})
    
    # 3. CHECK FOR DEAL (Logic from logic.py)
    is_deal_ready, proposed_terms = detect_deal_readiness(session["conversation"])
    
    return {
        "ai_response": ai_response,
        "status": "success",
        "deal_ready": is_deal_ready,       # <--- Frontend listens for this
        "proposed_terms": proposed_terms   # <--- Frontend displays these
    }

# --- THE NEW ENDPOINT ---
@app.post("/api/evaluate")
def evaluate_session(request: EvaluateRequest):
    if request.session_id not in sessions:
        raise HTTPException(404, "Session not found")
        
    session = sessions[request.session_id]
    
    # Generate Report Card (using ai_service.py)
    report = get_evaluation(
        session["conversation"],
        session["deal_params"],
        request.final_terms
    )
    
    return {
        "evaluation_report": report,
        "status": "completed"
    }
