
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import openai
import os
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Initialize 
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    print("Warning: OPENAI_API_KEY environment variable not set")

class Request(BaseModel):
    payload: Dict[str, Any]
    state: Dict[str, Any]

def get_openai_client():
    """Get OpenAI client with error handling"""
    if not openai.api_key:
        print("Warning: OpenAI API key not configured, using fallback responses")
        return None
    return openai

# Original common MCP abilities
@app.post("/abilities/accept_payload")
def accept_payload(req: Request):
    return {"accepted": True}

@app.post("/abilities/parse_request_text")
def parse_request_text(req: Request):
    query = req.state.get("query", "").lower()
    parsed = {
        "intent": "issue_report" if "damaged" in query else "general_query",
        "mentioned_order_ids": [tok for tok in req.state.get("query", "").split() if tok.startswith("#")],
    }
    return {"parsed": parsed}

@app.post("/abilities/normalize_fields")
def normalize_fields(req: Request):
    return {
        "normalized": {
            "email": req.state.get("email", "").lower().strip(),
            "priority": req.state.get("priority", "medium").lower()
        }
    }

@app.post("/abilities/add_flags_calculations")
def add_flags(req: Request):
    priority = req.state.get("priority", "medium").lower()
    return {"flags": {"sla_risk": 2 if priority == "high" else 1}}

@app.post("/abilities/solution_evaluation")
def solution_eval(req: Request):
    score = 80
    if req.state.get("kb_results"):
        score += 10
    if req.state.get("clarification_answer"):
        score += 5
    return {"solution_score": min(score, 100)}

@app.post("/abilities/update_payload")
def update_payload(req: Request):
    return {
        "decision_notes": f"Score={req.state.get('solution_score', 0)}; escalated={req.state.get('escalated', False)}"
    }

@app.post("/abilities/store_answer")
def store_answer(req: Request):
    return {"clarification_answer": req.state.get("clarification_answer")}

@app.post("/abilities/store_data")
def store_data(req: Request):
    return {"kb_results": req.state.get("kb_results", [])}

@app.post("/abilities/response_generation")
def response_generation(req: Request):
    name = req.state.get("customer_name", "Customer")
    if req.state.get("escalated"):
        msg = f"Hi {name}, we've escalated your issue to a specialist."
    else:
        msg = f"Hi {name}, your request is being processed."
    return {"draft_response": msg}

@app.post("/abilities/output_payload")
def output_payload(req: Request):
    return {"output": req.state}

# abilities
@app.post("/abilities/extract_intent")
def extract_intent(req: Request):
    """Extract intent from customer query using OpenAI"""
    client = get_openai_client()
    
    if not client:
        # Fallback logic
        query = req.state.get("query", "").lower()
        if "refund" in query:
            return {"intent": "refund_request", "confidence": 0.8}
        elif "replacement" in query or "replace" in query:
            return {"intent": "replacement_request", "confidence": 0.8}
        elif "order" in query and ("status" in query or "track" in query):
            return {"intent": "order_status", "confidence": 0.8}
        else:
            return {"intent": "general_inquiry", "confidence": 0.5}
    
    try:
        query = req.state.get("query", "")
        if not query:
            return {"intent": "unknown", "confidence": 0.0}
        
        messages = [
            {
                "role": "system", 
                "content": """Analyze the customer query and extract the primary intent. Choose from:
                - refund_request
                - replacement_request  
                - order_status
                - technical_support
                - account_issue
                - general_inquiry
                - complaint
                - compliment
                
                Respond with only the intent name and confidence score (0-1) separated by a space."""
            },
            {"role": "user", "content": query}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=50,
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip().lower()
        parts = result.split()
        intent = parts[0] if parts else "general_inquiry"
        confidence = float(parts[1]) if len(parts) > 1 and parts[1].replace('.', '').isdigit() else 0.5
        
        return {
            "intent": intent,
            "confidence": confidence,
            "raw_response": result
        }
        
    except Exception as e:
        return {"intent": "general_inquiry", "confidence": 0.0, "error": str(e)}

@app.post("/abilities/sentiment_analysis")
def sentiment_analysis(req: Request):
    """Analyze sentiment of customer query"""
    client = get_openai_client()
    
    if not client:
        # fallback sentiment analysis
        query = req.state.get("query", "").lower()
        negative_words = ["angry", "frustrated", "terrible", "awful", "hate", "worst", "useless"]
        positive_words = ["great", "excellent", "love", "amazing", "perfect", "thank", "wonderful"]
        
        negative_count = sum(1 for word in negative_words if word in query)
        positive_count = sum(1 for word in positive_words if word in query)
        
        if negative_count > positive_count:
            return {"sentiment": "negative", "confidence": 0.7}
        elif positive_count > negative_count:
            return {"sentiment": "positive", "confidence": 0.7}
        else:
            return {"sentiment": "neutral", "confidence": 0.6}
    
    try:
        query = req.state.get("query", "")
        if not query:
            return {"sentiment": "neutral", "confidence": 0.0}
        
        messages = [
            {
                "role": "system", 
                "content": "Analyze the sentiment of the following customer support query. Respond with only: positive, negative, or neutral, followed by a confidence score from 0-1."
            },
            {"role": "user", "content": query}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=50,
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip().lower()
        parts = result.split()
        sentiment = parts[0] if parts else "neutral"
        confidence = float(parts[1]) if len(parts) > 1 and parts[1].replace('.', '').isdigit() else 0.5
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "raw_response": result
        }
        
    except Exception as e:
        return {"sentiment": "neutral", "confidence": 0.0, "error": str(e)}

@app.post("/abilities/generate_response")
def generate_response(req: Request):
    """Generate customer response using OpenAI"""
    client = get_openai_client()
    
    customer_name = req.state.get("customer_name", "Customer")
    
    if not client:
        # Fallback response generation
        if req.state.get("escalated"):
            return {"draft_response": f"Hi {customer_name}, we've escalated your issue to a specialist who will contact you shortly."}
        else:
            return {"draft_response": f"Hi {customer_name}, thank you for contacting us. We're processing your request and will get back to you soon."}
    
    try:
        query = req.state.get("query", "")
        entities = req.state.get("entities", {})
        kb_results = req.state.get("kb_results", [])
        
        # Build context for response generation
        context = f"""
        Customer: {customer_name}
        Query: {query}
        Entities: {json.dumps(entities)}
        Knowledge Base Results: {json.dumps(kb_results)}
        """
        
        system_message = req.payload.get("system_message", 
            "You are a professional customer support agent. Generate a helpful, empathetic response to the customer query based on the provided context. Be concise but warm.")
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Context: {context}\n\nGenerate a response:"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        
        return {
            "draft_response": response.choices[0].message.content,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"draft_response": f"Hi {customer_name}, we're processing your request.", "error": str(e)}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_configured": bool(openai.api_key)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)