from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Any, Dict, Optional, Union
import uuid
import time
import json
import asyncio
from datetime import datetime

from latticepy.engine.interfaces.chatinterface import Chatinterface
from latticepy.engine.interfaces.clientinterface import VectorDBlist, Promptlist, LLMmodels, LlmConnections 
from latticepy.engine.interfaces.clientinterface import ConnectionModel, PromptModel
from latticepy.engine.interfaces.agentinterface import LatticeAgent
from latticepy.engine.interfaces.serverinterface import servertooldata, ToolServer


app = FastAPI(  
    title="Lattice server",
    description="server API for LatticeAI",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# In-memory database (replace with proper DB in production)
API_KEYS = {"sk-test123456789": "test-user"}

# --- Pydantic Models ---

class Message(BaseModel):
    role: str
    content: str
    more: Optional[str] = None
    name: Optional[str] = None

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class ChatRequest(BaseModel):
    agent: str
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    options: Optional[dict] = None
    template: Optional[str] = None
    format: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    headers: Dict[str, Any]
    choices: List[Choice]
    usage: Dict[str, int]

# --- Helper Functions ---

def get_timestamp():
    return datetime.now().isoformat() + "Z"

def create_completion_id():
    return f"cmpl-{str(uuid.uuid4())}"

async def generate_ai_response(messages, model, tag):
    """
    Async function to generate AI response
    """
    user_messages = [m for m in messages if m.role == "user"]
    if not user_messages:
        return "I don't see any user messages to respond to."

    last_message = user_messages[-1].content

    # Very simple response logic
    modelo=LLMmodels()
    models=(modelo.list()).keys()
    if model not in models:
        return f"Model {model} not found."
    try:
        print("calling chat interface")
        reply = Chatinterface(last_message, model, tag)
        return reply.chat()
    except Exception as e:
        print(e)
        return "Thank you for your message. Unable to reply to your message."

# Helper function to count tokens (simplified)
def count_tokens(messages):
    # In a real implementation, use a tokenizer like tiktoken
    # This is a very simplified approximation
    text = " ".join([m.content for m in messages])
    return len(text.split())

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = credentials.credentials
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return api_key

# --- Endpoint Implementations ---

@app.get("/api/lattice/version")
async def version():
    return {"version": "0.0.97"}

@app.get("/api/lattice/tags")
async def get_all_models():
    tags=[]
    try:
        models=LLMmodels()
        latticemodels = models.list()
        tags.extend(latticemodels.keys())
        agents=LatticeAgent.list()
        tags.extend(agents.keys())
        return JSONResponse({
            'tags':tags
        })
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))

@app.get("/openapi.json")
async def get_openapi():
    return app.openapi()

@app.post("/chat/completions", response_model=Union[ChatCompletionResponse, None])
@app.post("/api/lattice/chat", response_model=Union[ChatCompletionResponse, None])
async def chatwithagent(request: ChatRequest):
    completion_id = f"chatcmpl-{str(uuid.uuid4())}"
    ai_response, additonal_context, headers = await generate_ai_response(request.messages, request.model, request.agent)
    completion_tokens = count_tokens([Message(role="assistant", content=ai_response)])
    prompt_tokens = count_tokens(request.messages)
    print(additonal_context)
    response = {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "headers": headers,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "more": additonal_context,
                    "content": ai_response
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }
    return response



# -------  connection API endpoints ------------
@app.post("/api/lattice/connections")
async def create_connection(request: ConnectionModel):
    try:
        CONNECTIONS=LlmConnections.list()
        print("Creating connection:", request)
        if not request.id or not request.url:
            raise HTTPException(status_code=400, detail="ID and URL are required")
        if request.id in CONNECTIONS:
            raise HTTPException(status_code=400, detail="Connection already exists")
        LlmConnections.add(request.id, request)
        print("Connection created:", request.id)    
        return JSONResponse({
            "status": "success",
            "connection_id": request.id,
            "message": "Connection created successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/connections")
async def list_connections():
    try:
        connections = LlmConnections.listdown()
        return JSONResponse({
            "connections": list(connections)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/connections/{connection_id}")
async def get_connection(connection_id: str):
    try:
        connection = LlmConnections.get(connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        return JSONResponse({
            "connection": connection.model_dump()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/lattice/connections/{connection_id}")
async def delete_connection(connection_id: str):
    try:
        if connection_id not in LlmConnections.list():
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Delete the connection
        LlmConnections.delete(connection_id)
        return JSONResponse({
            "status": "success",
            "connection_id": connection_id,
            "message": "Connection deleted successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# -------  prompt API endpoints ------------
@app.get("/api/lattice/prompts")
async def list_prompts():
    try:
        prompts = Promptlist.listdown()
        return JSONResponse({
            "prompts": list(prompts)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/lattice/prompts")
async def create_prompt(request: PromptModel):
    try:
        if not request.id or not request.prompt:
            raise HTTPException(status_code=400, detail="ID and prompt are required")
        # Check if the prompt with the same ID already exists
        existing_prompts = Promptlist.list()
        if request.id in existing_prompts:
            raise HTTPException(status_code=400, detail="Prompt with this ID already exists")
        # Add the prompt to the list
        Promptlist.add(request.id, request)
        return JSONResponse({
            "status": "success",
            "prompt_id": request.id,
            "message": "Prompt created successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/prompts/{prompt_id}")
async def get_prompt(prompt_id: str):
    try:
        prompt = Promptlist.get(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        return JSONResponse({
            "prompt": prompt.model_dump()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/lattice/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    try:
        if prompt_id not in Promptlist.list():
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        # Delete the prompt
        Promptlist.delete(prompt_id)
        return JSONResponse({
            "status": "success",
            "prompt_id": prompt_id,
            "message": "Prompt deleted successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------ model API endpoints -------------
@app.get("/api/lattice/models")
async def list_models_details():
    models=LLMmodels()
    latticemodels = models.listdown()
    if not latticemodels:
        raise HTTPException(status_code=404, detail="No models found")
    return {
        "models": latticemodels
    }

@app.get("/api/lattice/models/{model_id}")
async def get_model_details(model_id: str):
    models=LLMmodels()
    model = models.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "model": model.model_dump()
    }


# -------  agent API endpoints ------------
@app.post("/api/lattice/agents")
async def create_lattice_agents(request: LatticeAgent):
    try:
        # Here you would implement the logic to create a model
        # For now, we just return a dummy response
        request.create()
        return JSONResponse({
            "status": "success",
            "agent": f"Agent {request.id} created"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lattice/agents")
async def get_lattice_agents():
    try:
        agents=LatticeAgent.listdown()
        if not agents:
            raise HTTPException(status_code=404, detail="Agents not found")
        
        return JSONResponse({
            "Lattice Agents": agents
        })
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/agents/{agent_id}")
async def get_agents_info(agent_id: str):
    try:
        agents=LatticeAgent.listdown()
        if agent_id not in agents:
            raise HTTPException(status_code=404, detail="Agents not found")
        agent_details = LatticeAgent.get(agent_id)
        return JSONResponse({
            "Lattice Agents": agent_details
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/lattice/agents/{agent_id}")
async def del_agents_info(agent_id: str):
    try:
        agents=LatticeAgent.listdown()
        if agent_id not in agents:
            raise HTTPException(status_code=404, detail="Agents not found")
        agent_details = LatticeAgent.delete(agent_id)
        print(agent_details)
        if agent_details:
            return JSONResponse({
                "status": f"successfully deleted {agent_id}"
            })
        else:
            HTTPException(status_code=500, detail="unable to delete")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------- Tool Server Endpoints -------------
    
@app.get("/api/lattice/toolserver")
async def get_tool_servers():
    try:
        s= servertooldata()
        return JSONResponse({
            "Lattice Servers": s.list()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/toolserver/{server_id}")
async def get_tool_server(server_id: str):
    try:
        s= servertooldata()
        server_details=s.tooldata
        return JSONResponse({
            "Lattice Tool Servers": server_details[server_id]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/lattice/toolserver/{server_id}")
async def del_tool_server(server_id: str):
    try:
        s= servertooldata()
        servers=s.tooldata
        if server_id not in servers.keys():
            raise HTTPException(status_code=404, detail="Agents not found")
        if s.delete(server_id):
            return JSONResponse({
                "status": f"successfully deleted {server_id}"
            })
        else:
            HTTPException(status_code=500, detail="unable to delete")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/lattice/toolserver")
async def create_lattice_server(request: ToolServer):
    try:
        print("server being added")
        print(request)
        servertooldata.add(request)
        return JSONResponse({
            "status": "successfully added",
        })
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


# -------  vector DB API endpoints ------------
@app.get("/api/lattice/vectordbs")
async def list_vectordbs():
    return VectorDBlist.list()

# -----  workflow API endpoints ------------
@app.get("/api/lattice/workflows")
async def list_workflows():
    pass


def startwebserver(host, port):
    import uvicorn
    uvicorn.run('latticepy.engine.services.webserver:app', host="0.0.0.0", port=port, workers=1, reload=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('latticepy.engine.services.webserver:app', host="0.0.0.0", port=3000, workers=4)
