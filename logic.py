import random
import re

# --- 1. DEAL GENERATION ---
def generate_deal_parameters(seed=None):
    """Generates the hidden math numbers."""
    if seed is not None:
        try:
            if isinstance(seed, str): seed = hash(seed) % (2**32)
            random.seed(seed)
        except: pass
    
    # Price
    opening_price = round(random.uniform(30, 50) * 10, 2)
    target_percent = random.uniform(0.05, 0.08) 
    target_price = round(opening_price * (1 - target_percent), 2)
    reservation_percent = random.uniform(0.12, 0.15)
    reservation_price = round(opening_price * (1 - reservation_percent), 2)

    # Delivery
    opening_delivery = int(random.randint(25, 45))
    target_delivery = int(opening_delivery * 0.85) 
    reservation_delivery = int(opening_delivery * 0.70)

    # Volume
    standard_volume = 1000 

    return {
        "price": { "opening": opening_price, "target": target_price, "reservation": reservation_price },
        "delivery": { "opening": opening_delivery, "target": target_delivery, "reservation": reservation_delivery },
        "volume": { "standard": standard_volume }
    }

# --- 2. FORMATTING ---
def format_deal_parameters(params):
    """Returns PURE DATA."""
    return f"""
--- NEGOTIATION DATA ---
1. Opening Price: ${params['price']['opening']}
2. Target Price: ${params['price']['target']}
3. Walk-away Price: ${params['price']['reservation']}
4. Standard Volume: {params['volume']['standard']} units
5. Opening Delivery: {params['delivery']['opening']} days
"""

# --- 3. STRICT DEAL DETECTION (Updated) ---
def detect_deal_readiness(history, current_extracted_terms=None):
    """
    Checks if the deal is ACTUALLY done using terms extracted by the AI.
    
    Args:
        history: list of messages (conversation context)
        current_extracted_terms: dict (optional) - The specific terms found in the CURRENT message 
                                 by Claude Haiku in ai_service.py.
                                 Format: {'price': 40, 'delivery': 30, 'volume': 1000}
    """
    if len(history) < 2: return False, None
    
    last_msg = history[-1]
    content = last_msg['content'].lower()
    
    # 1. Check for Agreement Signal
    strong_signals = [
        "i accept", "we accept", "accepted", "i agree", "we agree", "agreed",
        "deal confirmed", "confirm deal", "confirm the deal",
        "sounds good", "works for me", "perfect", "it's a deal", "its a deal", 
        "let's do it", "lets do it", "i can do that", "that works",
        "done", "fine", "ok deal", "okay deal", "deal"
    ]
    
    has_signal = any(phrase in content for phrase in strong_signals)
    
    # Negation Check (e.g. "I do NOT accept")
    negations = ["don't", "dont", "cannot", "can't", "won't", "not", "unable"]
    if has_signal:
        for neg in negations:
            # Simple check: if a negation word is present, we are cautious.
            # Exception: "Why not? Agreed." -> contains 'not' but is an agreement.
            # This is a heuristic; the AI extraction is the primary source of truth, 
            # but this signal check prevents false positives on simple chatter.
            if neg in content and ("confirmed" not in content and "agreed" not in content):
                has_signal = False
    
    # 2. Consolidate Terms
    # We combine the terms found in the LATEST message (by Haiku) 
    # with terms found in previous messages (to handle "I accept your price of $400")
    
    final_terms = {"price": None, "delivery": None, "volume": None}

    # If we have accurate AI extraction for the current turn, use it
    if current_extracted_terms:
        final_terms.update(current_extracted_terms)

    # 3. Backfill missing terms from history (Context Window)
    # If the user says "Deal", they are implicitly accepting the AI's last offer.
    # We need to find what the AI last proposed to fill in the blanks.
    if has_signal:
        for msg in reversed(history):
            # If we are still missing terms, check the AI's previous messages
            if msg['role'] == 'assistant':
                txt = msg['content']
                
                # FALLBACK REGEX (Only for AI text, which is predictable)
                # We search AI text to see what offer is currently on the table
                if final_terms['price'] is None: 
                    m = re.search(r'\$\s*([0-9][0-9,]*(?:\.\d+)?)', txt)
                    if m: final_terms['price'] = float(m.group(1).replace(',', ''))
                
                if final_terms['delivery'] is None:
                    m = re.search(r'(\d+)\s*days?', txt.lower())
                    if m: final_terms['delivery'] = int(m.group(1))
                    
                # If we have both now, stop searching back
                if final_terms['price'] and final_terms['delivery']:
                    break
    
    # 4. Final Verification
    has_price = final_terms["price"] is not None
    has_delivery = final_terms["delivery"] is not None
    
    # Only return True if we have the Signal AND both critical terms
    if has_signal and has_price and has_delivery:
        return True, final_terms
        
    return False, None
