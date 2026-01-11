import boto3
import json
import logging
import re  # <--- CRITICAL IMPORT
from typing import Dict, Any
from prompts import MASTER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# --- HELPERS ---

def extract_price(text):
    if not text: return None
    # Find all prices, take the LAST one mentioned
    matches = re.findall(r'\$\s*([0-9][0-9,]*(?:\.\d+)?)', text)
    if matches:
        try: return float(matches[-1].replace(',', ''))
        except: return None
    return None

def extract_delivery(text):
    if not text: return None
    matches = re.findall(r'(\d+)\s*days?', text.lower())
    if matches: return int(matches[-1])
    return None

def extract_volume(text):
    if not text: return None
    txt = text.lower()
    m_k = re.search(r'(\d+(?:\.\d+)?)\s*k\b', txt)
    if m_k: return int(float(m_k.group(1)) * 1000)
    m_u = re.search(r'(\d+(?:,\d{3})*)\s*(?:units|pcs|chips)', txt)
    if m_u: return int(m_u.group(1).replace(',', ''))
    return None

def clean_ai_response(text):
    if not isinstance(text, str): return text
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL).strip()
    prefixes = ["NEGOTIATING", "Negotiating", "negotiating", "Response:", "Alex:", "State:"]
    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].lstrip(" :")
    paragraphs = text.split('\n\n')
    if len(paragraphs) > 1 and len(paragraphs) % 2 == 0:
        mid = len(paragraphs) // 2
        if paragraphs[:mid] == paragraphs[mid:]:
            return '\n\n'.join(paragraphs[:mid])
    return text.strip()

# --- THE PUPPETEER LOGIC ---

def generate_turn_guidance(user_input, history, deal_params_str):
    """
    Calculates the EXACT move, including Missing Term Detection.
    """
    # 1. Parse Baseline
    standard_vol = 1000
    if deal_params_str and "Standard Order = 1000" in deal_params_str: 
        standard_vol = 1000
    
    # 2. Get Last AI Terms
    last_ai_price = None
    last_ai_delivery = None
    
    # Safety check for history
    if not history: history = []

    for msg in reversed(history):
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            p = extract_price(content)
            d = extract_delivery(content)
            if p: last_ai_price = p
            if d: last_ai_delivery = d
            if p and d: break 
            
    # Fallback
    if not last_ai_price:
        if deal_params_str:
            match = re.search(r'Opening Price: \$([0-9.]+)', deal_params_str)
            if match: last_ai_price = float(match.group(1))
            else: last_ai_price = 400.0
        else:
            last_ai_price = 400.0

    # 3. Analyze User Input
    user_price = extract_price(user_input)
    user_volume = extract_volume(user_input)
    user_delivery = extract_delivery(user_input)
    
    # --- RULE A: AGREEMENT CHECK ---
    agreement_words = ["deal", "agree", "accept", "done", "sounds good", "okay"]
    is_agreement = any(w in user_input.lower() for w in agreement_words)
    
    if is_agreement:
        has_final_price = user_price or last_ai_price
        has_final_delivery = user_delivery or last_ai_delivery
        
        if not has_final_delivery:
            return f"User agreed, but DELIVERY DATE is missing. Do NOT confirm. Say: 'We have a price, but we need to agree on delivery time.'"
        if not has_final_price:
            return f"User agreed, but PRICE is unclear. Do NOT confirm. Ask to confirm price."

    # --- RULE B: VOLUME PENALTY ---
    if user_volume and user_volume < standard_vol:
        return f"User asked for {user_volume} units. Small orders cost MORE. Refuse discount. Hold firm at ${last_ai_price}."

    # --- RULE C: TYPO CHECK ---
    if user_price and user_price > last_ai_price:
        return f"User offered ${user_price}, which is HIGHER than your price (${last_ai_price}). Ask if that is a typo."

    # --- RULE D: STALEMATE ---
    if len(history) >= 2 and history[-2].get('role') == 'user':
        last_user_input = history[-2].get('content', '')
        last_user_price = extract_price(last_user_input)
        
        if (user_price and last_user_price and abs(user_price - last_user_price) < 0.1) or (user_input.strip().lower() == last_user_input.strip().lower()):
             return f"User repeated their offer. You MUST hold firm at exactly ${last_ai_price}. Say: 'As I stated, I cannot accept that.'"

    # --- RULE E: CALCULATION LOGIC ---
    if user_price:
        gap_percent = (last_ai_price - user_price) / last_ai_price
        
        if gap_percent > 0.20:
            next_price = round(last_ai_price * 0.995, 2)
            return f"User is lowballing (${user_price}). You MUST offer exactly ${next_price}. Say: 'That is far too low.'"
            
        elif gap_percent < 0.10: 
             next_price = round(last_ai_price * 0.975, 2) 
             return f"We are getting close. Offer exactly ${next_price}. Say: 'I can make a significant move.'"
             
        else: 
             next_price = round(last_ai_price * 0.985, 2)
             return f"Standard negotiation. Offer exactly ${next_price}."
            
    return f"Hold at ${last_ai_price}. Discuss delivery time."

# --- CORE FUNCTIONS ---

def get_bedrock_response(prompt: str, region: str = "us-east-2") -> str:
    """Get response from Amazon Bedrock"""
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=region)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "temperature": 0.1, 
            "messages": [{"role": "user", "content": prompt}]
        }
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps(body),
            contentType='application/json'
        )
        result = json.loads(response['body'].read())
        return clean_ai_response(result['content'][0]['text'].strip())
    except Exception as e:
        logger.error(f"Bedrock error: {e}")
        return f"Error: {str(e)[:50]}"

def create_negotiation_prompt(user_input: str, deal_params_str: str, history: list) -> str:
    """Create the prompt with injected Python logic"""
    # Run logic safely
    try:
        guidance = generate_turn_guidance(user_input, history, deal_params_str)
    except Exception as e:
        logger.error(f"Guidance Error: {e}")
        guidance = "Negotiate professionally."

    # Format history safely
    history_str = ""
    if history:
        history_str = "\n".join([f"{msg.get('role', 'unknown').title()}: {msg.get('content', '')}" for msg in history[-6:]])
    
    prompt = MASTER_PROMPT_TEMPLATE.format(
        deal_parameters=deal_params_str,
        conversation_history=history_str,
        user_input=user_input,
        turn_guidance=guidance, 
        standard_volume=1000
    )
    return prompt

def get_evaluation(history: list, deal_params: Dict, final_terms: Dict) -> str:
    """Generates the final grading report"""
    # Safe getters
    final_price = final_terms.get('price', 'N/A')
    final_delivery = final_terms.get('delivery', 'N/A')
    final_volume = final_terms.get('volume', 'N/A')
    
    conversation_log = ""
    if history:
        conversation_log = "\n".join([f"{m.get('role','').upper()}: {m.get('content','')}" for m in history])
  
    # 2. The FULL Original Rubric Prompt
    eval_prompt = f"""
You are an expert negotiation coach and evaluator. Analyze the following B2B negotiation and provide a comprehensive evaluation.

--- SELLER'S (AI's) SECRET PARAMETERS ---
(The AI uses 0-5% reductions between price/delivery levels to enable dynamic negotiation with meaningful concessions)
Price Opening: ${deal_params['price']['opening']}
Price Target (AI's Ideal): ${deal_params['price']['target']}
Price Reservation (AI's Walk-away): ${deal_params['price']['reservation']}

Delivery Opening: {deal_params['delivery']['opening']} days
Delivery Target (AI's Ideal): {deal_params['delivery']['target']} days
Delivery Reservation (AI's Fastest): {deal_params['delivery']['reservation']} days

--- NEGOTIATION CONVERSATION ---
{conversation_log}

--- ACADEMIC EVALUATION RUBRIC (Evaluate the USER) ---
Please evaluate the USER'S performance on the following criteria. Note that the AI was instructed to use strict 0-5% reductions.

1. Deal Quality & Outcome (Weight: 33%)
Excellent (A: 90-100): Achieved a deal at or very close to the AI's reservation points for both price and delivery.
Proficient (B: 80-89): Achieved a strong deal, significantly better than the AI's opening offers but not quite at reservation limits.
Developing (C: 70-79): Reached an agreement, but the deal is only slightly better than the AI's opening offers.
Needs Improvement (D/F: 0-69): Failed to reach an agreement, or accepted a deal at or worse than the AI's opening offers.

2. Trade-off Strategy & Analytical Reasoning (Weight: 28%)
Excellent (A: 90-100): User demonstrates strong analytical reasoning and actively proposes logical, win-win trade-offs.
Proficient (B: 80-89): User identifies at least one meaningful trade-off with sound reasoning.
Developing (C: 70-79): User shows limited recognition of trade-offs; tends to focus on single variables.
Needs Improvement (D/F: 0-69): User made no attempt to use trade-offs; offers were inconsistent or illogical.

3. Professionalism & Communication (Weight: 17%)
Excellent (A: 90-100): User maintains professional tone, justifies positions with business logic, shows strong persuasion skills.
Proficient (B: 80-89): User is mostly professional and clear with minor lapses.
Developing (C: 70-79): User has some professional tone but lacks clarity in justifications.
Needs Improvement (D/F: 0-69): User used unprofessional, argumentative, or overly casual tone.

4. Negotiation Process Management (Weight: 11%)
Excellent (A: 90-100): User efficiently manages negotiation flow, summarizes progress, confirms offers clearly.
Proficient (B: 80-89): User is mostly structured with minor flow issues.
Developing (C: 70-79): User's conversation flow is disorganized or purely reactive.
Needs Improvement (D/F: 0-69): User's process is chaotic or incomplete.

5. Creativity & Adaptability (Weight: 11%)
Excellent (A: 90-100): User employs innovative solutions and adapts effectively to counteroffers.
Proficient (B: 80-89): User shows some creativity or adaptation.
Developing (C: 70-79): User shows limited adaptation, mostly repeats offers.
Needs Improvement (D/F: 0-69): User made no attempt to adjust strategy or be creative.

--- OUTPUT FORMAT ---
FINAL EVALUATION REPORT

Final Deal Achieved:
Price: ${final_price}
Delivery: {final_delivery} days
Volume: {final_volume} units

Metrics Scores:
Deal Quality: [score]/100 (Weight: 33%)
Trade-off Strategy: [score]/100 (Weight: 28%)
Professionalism: [score]/100 (Weight: 17%)
Process Management: [score]/100 (Weight: 11%)
Creativity & Adaptability: [score]/100 (Weight: 11%)

Overall Weighted Score: [calculated_score]/100

Key Strengths:
[Specific strength based on high-scoring categories]
[Additional strength]

Areas for Improvement:
[Specific area based on low-scoring categories]
[Additional area]

Feedback & Recommendations:
[2-3 paragraphs of constructive, specific feedback about how the user engaged with the AI's dynamic concession patterns and negotiation flexibility.]
"""
    
    # 3. Call Bedrock
    try:
        bedrock = boto3.client('bedrock-runtime', region_name="us-east-2")
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "temperature": 0.5,
            "messages": [{"role": "user", "content": eval_prompt}]
        }
        
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps(body),
            contentType='application/json'
        )
        
        result = json.loads(response['body'].read())
        raw_text = result['content'][0]['text'].strip()
        return raw_text
        
    except Exception as e:
        logger.error(f"Bedrock evaluation error: {e}")
        return f"Error generating evaluation: {str(e)}"
