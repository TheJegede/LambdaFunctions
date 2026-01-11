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

# --- 3. HELPERS ---
def extract_price(text):
    if not text: return None
    match = re.search(r'\$\s*([0-9][0-9,]*(?:\.\d+)?)', text)
    if match:
        try: return float(match.group(1).replace(',', ''))
        except: return None
    return None

def extract_delivery(text):
    if not text: return None
    match = re.search(r'(\d+)\s*days?', text.lower())
    if match: return int(match.group(1))
    return None

def extract_volume(text):
    if not text: return None
    txt = text.lower()
    m_k = re.search(r'(\d+(?:\.\d+)?)\s*k\b', txt)
    if m_k: return int(float(m_k.group(1)) * 1000)
    m_u = re.search(r'(\d+(?:,\d{3})*)\s*units?', txt)
    if m_u: return int(m_u.group(1).replace(',', ''))
    return None

# --- 4. STRICT DEAL DETECTION ---
def detect_deal_readiness(history):
    """
    Checks if the deal is ACTUALLY done.
    REQUIREMENT: Must have a Signal AND (Price + Delivery).
    """
    if len(history) < 3: return False, None
    
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
    
    # Negation Check
    negations = ["don't", "dont", "cannot", "can't", "won't", "not", "unable"]
    if has_signal:
        for neg in negations:
            if neg in content and ("confirmed" not in content and "agreed" not in content):
                has_signal = False
    
    # 2. Extract Terms from recent context
    current_terms = {"price": None, "delivery": None, "volume": None}
    
    # Scan last 3 messages to gather terms
    for msg in reversed(history[-3:]):
        txt = msg['content']
        if current_terms["price"] is None: current_terms["price"] = extract_price(txt)
        if current_terms["delivery"] is None: current_terms["delivery"] = extract_delivery(txt)
        if current_terms["volume"] is None: current_terms["volume"] = extract_volume(txt)
    
    # 3. THE FIX: Explicitly check for Price AND Delivery
    has_price = current_terms["price"] is not None
    has_delivery = current_terms["delivery"] is not None
    
    # Only return True if we have the Signal AND both critical terms
    if has_signal and has_price and has_delivery:
        return True, current_terms
        
    return False, None
