# enhanced_atlas_mcp.py - Enhanced debug version with all required abilities
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# MongoDB configuration
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "support_system")

# Initialize MongoDB client
mongo_client = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mongo_client, db
    print("🚀 Starting up Atlas MCP server...")
    
    try:
        print(f"Attempting to connect to MongoDB: {MONGO_URI}")
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = mongo_client[DATABASE_NAME]
        
        # Test connection
        mongo_client.admin.command('ping')
        print(f"✅ Connected to MongoDB database: {DATABASE_NAME}")
        
        # Create indexes
        try:
            db.tickets.create_index("ticket_id", unique=True)
            db.customers.create_index("email", unique=True)
            db.knowledge_base.create_index([("title", "text"), ("content", "text")])
            print("✅ Indexes created successfully")
        except Exception as e:
            print(f"⚠️ Warning: Could not create indexes: {e}")
            
    except ConnectionFailure as e:
        print(f"⚠️ Could not connect to MongoDB: {e}")
        print("Will continue with mock responses...")
        mongo_client = None
        db = None
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        print("Will continue with mock responses...")
        mongo_client = None
        db = None
    
    print("✅ Startup completed")
    yield
    
    # Shutdown
    print("🔌 Shutting down application...")
    if mongo_client is not None:
        mongo_client.close()
        print("🔌 MongoDB connection closed")

# FastAPI app with lifespan
app = FastAPI(
    title="Atlas MongoDB MCP Server - Enhanced Debug",
    description="Enhanced version with all required abilities and better error handling",
    version="2.0.0",
    lifespan=lifespan
)

class Request(BaseModel):
    payload: Dict[str, Any] = {}
    state: Dict[str, Any] = {}

def get_mock_response(ability_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Return mock responses when MongoDB is not available"""
    mock_responses = {
        "extract_entities": {
            "entities": {
                "order_id": "#A123" if "#A123" in state.get("query", "") else None,
                "product_type": "order",
                "urgency": "high" if "asap" in state.get("query", "").lower() else "medium"
            }
        },
        "enrich_records": {
            "enriched": {
                "customer_tier": "premium",
                "account_age_days": 365,
                "total_orders": 15
            }
        },
        "get_customer_history": {
            "customer_history": [
                {
                    "ticket_id": "TCK-999",
                    "date": "2024-01-15",
                    "issue": "Delivery delay",
                    "resolution": "Refunded shipping cost"
                }
            ]
        },
        "clarify_question": {
            "clarification_question": "Could you please provide your shipping address for the replacement?"
        },
        "extract_answer": {
            "extracted_info": state.get("clarification_answer", "No answer provided")
        },
        "knowledge_base_search": {
            "kb_results": [
                {
                    "title": "Damaged Package Policy",
                    "content": "We replace damaged items within 30 days",
                    "relevance_score": 0.9
                }
            ]
        },
        "search_knowledge_base": {
            "kb_results": [
                {
                    "article_id": "KB001",
                    "title": "Return and Exchange Policy", 
                    "snippet": "Items can be returned or exchanged within 30 days of delivery",
                    "score": 0.85
                }
            ]
        },
        "escalation_decision": {
            "escalated": True,
            "escalation_reason": "High priority customer issue"
        },
        "update_ticket": {
            "ticket_updates": {
                "status": "in_progress",
                "assigned_to": "specialist_team",
                "updated_at": datetime.now().isoformat()
            }
        },
        "close_ticket": {
            "closed": False,
            "reason": "Escalated to specialist"
        },
        "update_ticket_status": {
            "status": "escalated",
            "updated_at": datetime.now().isoformat()
        },
        "store_ticket": {
            "stored": True,
            "ticket_id": state.get("ticket_id")
        },
        "execute_api_calls": {
            "api_actions": ["send_replacement_email", "update_inventory"]
        },
        "trigger_notifications": {
            "notifications": ["Email sent to customer", "Internal team notified"]
        },
        "store_conversation_log": {
            "log_stored": True,
            "conversation_id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    
    return mock_responses.get(ability_name, {"mock_response": True, "ability": ability_name})

@app.get("/")
def root():
    return {
        "message": "Atlas MCP Server is running", 
        "version": "2.0.0",
        "mongodb_connected": db is not None
    }

@app.get("/health")
def health_check():
    mongo_status = "connected" if db is not None else "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mongodb_status": mongo_status,
        "database": DATABASE_NAME,
        "mongo_uri_set": MONGO_URI is not None,
        "available_abilities": [
            "extract_entities", "enrich_records", "get_customer_history",
            "clarify_question", "extract_answer", "knowledge_base_search", 
            "search_knowledge_base", "escalation_decision", "update_ticket",
            "close_ticket", "update_ticket_status", "store_ticket",
            "execute_api_calls", "trigger_notifications", "store_conversation_log"
        ]
    }

# All the abilities that should be handled by Atlas MCP according to config

@app.post("/abilities/extract_entities")
def extract_entities(req: Request):
    """Extract entities from customer query"""
    if db is None:
        return get_mock_response("extract_entities", req.state)
    
    try:
        query = req.state.get("query", "")
        entities = {}
        
        # Simple entity extraction logic
        if "#" in query:
            entities["order_id"] = [word for word in query.split() if word.startswith("#")]
        
        if any(word in query.lower() for word in ["urgent", "asap", "emergency"]):
            entities["urgency"] = "high"
        
        return {"entities": entities}
    except Exception as e:
        return get_mock_response("extract_entities", req.state)

@app.post("/abilities/enrich_records")
def enrich_records(req: Request):
    """Enrich customer records with additional data"""
    if db is None:
        return get_mock_response("enrich_records", req.state)
    
    try:
        email = req.state.get("normalized", {}).get("email") or req.state.get("email", "").lower()
        
        # Try to find customer in database
        customer = db.customers.find_one({"email": email})
        
        if customer:
            enriched = {
                "customer_tier": customer.get("tier", "standard"),
                "account_age_days": customer.get("account_age_days", 0),
                "total_orders": customer.get("total_orders", 0),
                "last_contact": customer.get("last_contact")
            }
        else:
            # Create new customer record
            enriched = {
                "customer_tier": "standard",
                "account_age_days": 0,
                "total_orders": 0,
                "is_new_customer": True
            }
            
            db.customers.insert_one({
                "email": email,
                "name": req.state.get("customer_name"),
                "tier": "standard",
                "account_age_days": 0,
                "total_orders": 0,
                "created_at": datetime.now()
            })
        
        return {"enriched": enriched}
    except Exception as e:
        return get_mock_response("enrich_records", req.state)

@app.post("/abilities/get_customer_history")
def get_customer_history(req: Request):
    """Get customer's support history"""
    if db is None:
        return get_mock_response("get_customer_history", req.state)
    
    try:
        email = req.state.get("normalized", {}).get("email") or req.state.get("email", "").lower()
        
        # Find recent tickets for this customer
        recent_tickets = list(db.tickets.find(
            {"customer_email": email}
        ).sort("created_at", -1).limit(5))
        
        customer_history = []
        for ticket in recent_tickets:
            customer_history.append({
                "ticket_id": ticket.get("ticket_id"),
                "date": ticket.get("created_at", "").strftime("%Y-%m-%d") if ticket.get("created_at") else "",
                "issue": ticket.get("issue_summary", ""),
                "status": ticket.get("status", ""),
                "resolution": ticket.get("resolution", "")
            })
        
        return {"customer_history": customer_history}
    except Exception as e:
        return get_mock_response("get_customer_history", req.state)

@app.post("/abilities/clarify_question")
def clarify_question(req: Request):
    """Generate clarification question"""
    if db is None:
        return get_mock_response("clarify_question", req.state)
    
    try:
        query = req.state.get("query", "")
        intent = req.state.get("intent", "")
        
        if "replacement" in query.lower() and "address" not in query.lower():
            question = "Could you please provide the shipping address for your replacement?"
        elif "refund" in query.lower():
            question = "Would you prefer a refund to your original payment method or store credit?"
        else:
            question = "Could you provide more details about your request?"
        
        return {"clarification_question": question}
    except Exception as e:
        return get_mock_response("clarify_question", req.state)

@app.post("/abilities/extract_answer")
def extract_answer(req: Request):
    """Extract information from clarification answer"""
    return {"extracted_info": req.state.get("clarification_answer", "No answer provided")}

@app.post("/abilities/knowledge_base_search") 
@app.post("/abilities/search_knowledge_base")
def search_knowledge_base(req: Request):
    """Search knowledge base for relevant articles"""
    if db is None:
        return get_mock_response("knowledge_base_search", req.state)
    
    try:
        query = req.state.get("query", "")
        intent = req.state.get("intent", "")
        
        # Search knowledge base using text search
        search_terms = f"{query} {intent}".strip()
        
        kb_articles = list(db.knowledge_base.find(
            {"$text": {"$search": search_terms}}
        ).limit(3))
        
        kb_results = []
        for article in kb_articles:
            kb_results.append({
                "article_id": str(article.get("_id")),
                "title": article.get("title", ""),
                "content": article.get("content", "")[:200] + "..." if len(article.get("content", "")) > 200 else article.get("content", ""),
                "relevance_score": 0.8  # Mock score
            })
        
        return {"kb_results": kb_results}
    except Exception as e:
        return get_mock_response("knowledge_base_search", req.state)

@app.post("/abilities/escalation_decision")
def escalation_decision(req: Request):
    """Decide whether to escalate the ticket"""
    priority = req.state.get("priority", "medium").lower()
    sentiment = req.state.get("sentiment", "neutral")
    
    escalated = (priority == "high" or sentiment == "negative")
    
    return {
        "escalated": escalated,
        "escalation_reason": f"Priority: {priority}, Sentiment: {sentiment}"
    }

@app.post("/abilities/update_ticket")
def update_ticket(req: Request):
    """Update ticket information"""
    if db is None:
        return get_mock_response("update_ticket", req.state)
    
    try:
        ticket_id = req.state.get("ticket_id")
        
        update_data = {
            "status": "in_progress" if req.state.get("escalated") else "resolved",
            "updated_at": datetime.now(),
            "priority": req.state.get("priority", "medium"),
            "sentiment": req.state.get("sentiment", "neutral")
        }
        
        db.tickets.update_one(
            {"ticket_id": ticket_id},
            {"$set": update_data},
            upsert=True
        )
        
        return {"ticket_updates": update_data}
    except Exception as e:
        return get_mock_response("update_ticket", req.state)

@app.post("/abilities/close_ticket")
def close_ticket(req: Request):
    """Close or keep ticket open based on status"""
    escalated = req.state.get("escalated", False)
    
    return {
        "closed": not escalated,
        "reason": "Escalated to specialist" if escalated else "Issue resolved"
    }

@app.post("/abilities/update_ticket_status")
def update_ticket_status(req: Request):
    """Update ticket status"""
    status = "escalated" if req.state.get("escalated") else "resolved"
    
    return {
        "status": status,
        "updated_at": datetime.now().isoformat()
    }

@app.post("/abilities/store_ticket")
def store_ticket(req: Request):
    """Store ticket data in MongoDB"""
    if db is None:
        return get_mock_response("store_ticket", req.state)
    
    try:
        ticket_data = {
            "ticket_id": req.state.get("ticket_id"),
            "customer_name": req.state.get("customer_name"),
            "customer_email": req.state.get("email", "").lower(),
            "query": req.state.get("query"),
            "priority": req.state.get("priority"),
            "intent": req.state.get("intent"),
            "sentiment": req.state.get("sentiment"),
            "status": req.state.get("status", "open"),
            "created_at": datetime.now(),
            "escalated": req.state.get("escalated", False)
        }
        
        db.tickets.insert_one(ticket_data)
        return {"stored": True, "ticket_id": ticket_data["ticket_id"]}
    except Exception as e:
        return get_mock_response("store_ticket", req.state)

@app.post("/abilities/execute_api_calls")
def execute_api_calls(req: Request):
    """Execute API calls based on ticket resolution"""
    actions = []
    
    if req.state.get("intent") == "replacement_request":
        actions.append("initiate_replacement_order")
    
    if req.state.get("escalated"):
        actions.append("notify_specialist_team")
    
    actions.append("send_customer_notification")
    
    return {"api_actions": actions}

@app.post("/abilities/trigger_notifications")
def trigger_notifications(req: Request):
    """Trigger various notifications"""
    notifications = []
    
    customer_name = req.state.get("customer_name", "Customer")
    
    if req.state.get("escalated"):
        notifications.append(f"Escalation email sent to {customer_name}")
        notifications.append("Internal team notified of escalation")
    else:
        notifications.append(f"Resolution email sent to {customer_name}")
    
    return {"notifications": notifications}

@app.post("/abilities/store_conversation_log") 
def store_conversation_log(req: Request):
    """Store conversation log"""
    if db is None:
        return get_mock_response("store_conversation_log", req.state)
    
    try:
        log_data = {
            "ticket_id": req.state.get("ticket_id"),
            "conversation_log": req.state.get("logs", []),
            "final_state": req.state,
            "timestamp": datetime.now()
        }
        
        db.conversation_logs.insert_one(log_data)
        return {"log_stored": True, "conversation_id": str(log_data["_id"]) if "_id" in log_data else "unknown"}
    except Exception as e:
        return get_mock_response("store_conversation_log", req.state)

@app.post("/abilities/test")
def test_mongodb(req: Request):
    """Test MongoDB connection"""
    if db is None:
        return {"error": "MongoDB not connected", "db_status": "None"}
    
    try:
        result = db.test_collection.find_one({})
        return {
            "success": True,
            "db_status": "connected",
            "test_result": str(result) if result else "No documents found"
        }
    except Exception as e:
        return {"error": str(e), "db_status": "error"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Atlas MCP server on port 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)