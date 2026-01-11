import boto3
import json
from decimal import Decimal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import uuid
from datetime import datetime
from mangum import Mangum

# IMPORT YOUR MODULES
# Ensure these files (ai_service.py, logic.py) are in the same folder
from ai_service import get_bedrock_response, create_negotiation_prompt, get_evaluation
from logic import generate_deal_parameters, format_deal_parameters, detect_deal_readiness

app = FastAPI(title="AI Negotiator", version="1.0.0")

# CORS Setup
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

class EvaluateRequest(BaseModel):
    session_id: str
    final_terms: Dict  # Expects data like: {price: 50, delivery: 30, volume: 10000}

# Initializing DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('NegotiationSessions')

# Helper function to handle decimal type (for JSON serialization)
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

@app.post("/api/sessions/new")
def create_session(request: NewSessionRequest):
    session_id = str(uuid.uuid4())
    
    # 1. Generate Smart Parameters
    deal_params = generate_deal_parameters(request.student_id)
    
    # 2. Format them for the AI 
    deal_params_str = format_deal_parameters(deal_params)
    
    # 3. Create Greeting
    greeting = (
        f"Hello! I'm Alex from ChipSource Inc. We are looking to sell our CS-1000 chips. "
        f"Our standard opening is ${deal_params['price']['opening']} per unit "
        f"with {deal_params['delivery']['opening']}-day delivery. What works for you?"
    )

    # 4. Save to DynamoDB
    # We use json.loads(json.dumps(...)) to convert floats to Decimals if needed, 
    # or ensure your generate_deal_parameters returns Decimals compatible with DynamoDB.
    item = {
        'session_id': session_id,
        'deal_params': json.loads(json.dumps(deal_params, default=decimal_default), parse_float=Decimal),
        'deal_params_str': deal_params_str,
        'conversation': [{"role": "assistant", "content": greeting}],
        'created_at': datetime.utcnow().isoformat()
    }
    
    table.put_item(Item=item)

    return {
        "session_id": session_id,
        "deal_params": deal_params,
        "greeting": greeting
    }

@app.post("/api/chat")
def chat(request: ChatRequest):
    # 1. Fetch from DynamoDB
    response = table.get_item(Key={'session_id': request.session_id})
    if 'Item' not in response:
        raise HTTPException(status_code=404, detail="Session not found")

    session = response['Item']

    # 2. Add User Input
    session["conversation"].append({"role": "user", "content": request.user_input})
    
    # 3. Get AI Response
    prompt = create_negotiation_prompt(
        request.user_input,
        session.get("deal_params_str", ""), # Use .get() for safety
        session["conversation"]
    )
    
    ai_response = get_bedrock_response(prompt)
    session["conversation"].append({"role": "assistant", "content": ai_response})
    
    # 4. Save Update to DynamoDB (CRITICAL: Must happen BEFORE return)
    table.put_item(Item=session)

    # 5. CHECK FOR DEAL
    is_deal_ready, proposed_terms = detect_deal_readiness(session["conversation"])
    
    return {
        "ai_response": ai_response,
        "status": "success",
        "deal_ready": is_deal_ready,       
        "proposed_terms": proposed_terms   
    }

@app.post("/api/evaluate")
def evaluate_session(request: EvaluateRequest):
    # 1. Fetch from DynamoDB
    response = table.get_item(Key={'session_id': request.session_id})
    if 'Item' not in response:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = response['Item']
    
    # 2. Generate Report Card
    # Ensure deal_params is converted back from Decimal if your logic.py expects floats
    # DynamoDB returns Decimals.
    report = get_evaluation(
        session["conversation"],
        session["deal_params"],
        request.final_terms
    )
    
    return {
        "evaluation_report": report,
        "status": "completed"
    }

handler = Mangum(app)
