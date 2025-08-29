# LangGraph Customer Support Agent

A graph-based customer support automation system built with LangGraph that orchestrates workflow stages through Model Context Protocol (MCP) servers.

## Architecture Overview

The system implements an 11-stage customer support workflow using LangGraph for orchestration, with abilities distributed across specialized MCP servers:

- **COMMON Server** : Handles NLP tasks, sentiment analysis, and response generation
- **ATLAS Server**  : Manages data persistence, knowledge base search, and external integrations

## System Components

### Core Files

- `agent.py` - Main LangGraph orchestrator with workflow logic
- `agent_config.yaml` - Configuration mapping stages to abilities and servers
- `common_mcp.py` -     MCP server for text processing
- `minimal_atlas_mcp.py` - MCP server for data operations

### Workflow Stages

1. **INTAKE** - Accept incoming support requests
2. **UNDERSTAND** - Parse text and extract entities, intent, sentiment
3. **PREPARE** - Normalize fields, enrich with customer data, calculate flags
4. **ASK** - Generate clarification questions for customers
5. **WAIT** - Process clarification responses
6. **RETRIEVE** - Search knowledge base for relevant solutions
7. **DECIDE** - Evaluate solutions and route to escalation or resolution
8. **UPDATE** - Modify ticket status and close if escalated
9. **CREATE** - Generate customer response using AI
10. **DO** - Execute API calls and trigger notifications
11. **COMPLETE** - Output final structured payload

## Prerequisites

### Dependencies
```bash
pip install langgraph requests pyyaml rich pymongo openai python-dotenv fastapi uvicorn
```

### Environment Setup
Create a `.env` file with:
```
OPENAI_API_KEY=your_openai_api_key
MONGODB_URI=mongodb://localhost:27017
MONGO_DATABASE=support_system
```

### MongoDB Setup
Ensure MongoDB is running locally or update connection string in `.env`

## Installation & Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env` file
4. Start MCP servers:
   ```bash
   # Terminal 1 - Start COMMON server (OpenAI)
   python common_mcp.py

   # Terminal 2 - Start ATLAS server (MongoDB)  
   python minimal_atlas_mcp.py
   ```

## Running the Agent

### Demo Mode
```bash
python agent.py --demo
```

### Custom Input
```bash
python agent.py --input '{"customer_name": "John Doe", "email": "john@example.com", "query": "My order is delayed", "priority": "High", "ticket_id": "TCK-123"}'
```

## Configuration

The `agent_config.yaml` file defines:
- Stage execution modes (deterministic/non-deterministic)
- Ability-to-server routing
- Input schema validation

Example configuration structure:
```yaml
stages:
  - id: UNDERSTAND
    mode: deterministic
    abilities: [parse_request_text, extract_entities, extract_intent]
    servers: [COMMON, ATLAS, COMMON]
```

## State Management

The system maintains persistent state across all stages using a TypedDict structure:

```python
class SupportState(TypedDict):
    # Input fields
    customer_name: str
    email: str
    query: str
    priority: str
    ticket_id: str
    
    # Derived fields
    intent: str
    sentiment: str
    entities: Dict[str, Any]
    kb_results: List[Dict[str, Any]]
    # ... additional state fields
```

## MCP Server Integration

### COMMON Server Abilities
- Text parsing and entity extraction
- Intent classification using OpenAI
- Sentiment analysis
- AI-powered response generation
- Solution evaluation scoring

### ATLAS Server Abilities  
- Customer data enrichment from MongoDB
- Knowledge base search
- Ticket status management
- Escalation decisions
- Notification triggers

## Error Handling

The system includes comprehensive error handling:
- **Graceful Degradation**: Falls back to mock responses when services are unavailable
- **Retry Logic**: Configurable timeouts for HTTP requests
- **Logging**: Detailed execution logs with MCP server routing information

## Output Format

The system produces structured output showing:
- Final state with all enriched fields
- Execution logs detailing stage progression
- MCP server routing decisions
- Generated responses and actions taken

## Example Output

```
Final Structured Payload:
┌─────────────────┬─────────────────────────────────────────┐
│ Field           │ Value                                   │
├─────────────────┼─────────────────────────────────────────┤
│ customer_name   │ Aisha Jain                             │
│ intent          │ replacement_request                     │
│ sentiment       │ negative                               │
│ solution_score  │ 85                                     │
│ escalated       │ True                                   │
└─────────────────┴─────────────────────────────────────────┘

Execution Logs:
- INTAKE complete.
- [COMMON] parse_request_text → {"parsed": {...}}
- [ATLAS] extract_entities → {"entities": {...}}
- DECIDE scored solution.
- Router: score 85 < 90 → UPDATE.
```

## Customization

### Adding New Abilities
1. Implement the ability in the appropriate MCP server
2. Add routing configuration in `agent_config.yaml`
3. Update state schema if new fields are needed

### Modifying Workflow Logic
- Edit stage node functions in `agent.py`
- Adjust conditional routing logic in router functions
- Update graph edges for new stage transitions

## Testing

The system includes health check endpoints:
- `http://localhost:8001/health` - COMMON server status
- `http://localhost:8002/health` - ATLAS server status

## Troubleshooting

### Common Issues
- **MongoDB Connection**: Verify MongoDB is running and connection string is correct
- **OpenAI API**: Ensure API key is valid and has sufficient credits
- **Port Conflicts**: Check that ports 8001 and 8002 are available

### Debug Mode
Set logging level to DEBUG in the MCP servers for detailed execution traces.

## License

This project is licensed under the MIT License.
