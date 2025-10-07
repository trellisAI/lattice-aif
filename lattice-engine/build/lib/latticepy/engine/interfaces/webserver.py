from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Any, Dict, Optional, Union
import uuid
import time
import json
import asyncio
from datetime import datetime

from LatticePy.interfaces.chatinterface import Chatinterface
from LatticePy.interfaces.clientinterface import VectorDBlist, Promptlist, LatticeTools, LLMmodels, LlmConnections 
from LatticePy.interfaces.clientinterface import ConnectionModel, PromptModel, ToolsModel
from LatticePy.interfaces.agentinterface import LatticeAgent

class ToolsModelReq(ToolsModel):
    toollist: Union[str, List[Dict[str, Any]]] = "[]"

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

# --- Pydantic Models ---



class ChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None

class ChatRequest(BaseModel):
    tag: str
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    options: Optional[dict] = None
    template: Optional[str] = None
    format: Optional[str] = None

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
        if not prompts:
            raise HTTPException(status_code=404, detail="No prompts found")
        
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

# -------  tools API endpoints ------------
@app.post("/api/lattice/tools")
async def add_tools(request: ToolsModelReq):
    try:
        if not request.id or not request.toollist:
            raise HTTPException(status_code=400, detail="ID and tools are required")
        # Check if the tools with the same ID already exist
        existing_tools = LatticeTools.list()
        if request.id in existing_tools:
            raise HTTPException(status_code=400, detail="Tools with this ID already exist")
        # Add the tools to the list
        import json
        if isinstance(request.toollist, list):
            request.toollist = json.dumps(request.toollist)
        else:
            raise HTTPException(status_code=400, detail="Tools list must be a JSON string with list of tools within or list of tools")
        # Add the tools to the LatticeTools
        print("Adding tools:", request)
        LatticeTools.add(request.id, request)
        return JSONResponse({
            "status": "success",
            "tools_id": request.id,
            "message": "Tools created successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
       
@app.get("/api/lattice/tools")
async def list_tools():
    try:
        tools = list(LatticeTools.listdown())
        if not tools:
            raise HTTPException(status_code=404, detail="No tools found")
        
        return JSONResponse({
            "tools": tools
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/tools/{tools_id}")
async def get_tools(tools_id: str):
    try:
        tools = LatticeTools.get(tools_id)
        if not tools:
            raise HTTPException(status_code=404, detail="Tools not found")
        
        return JSONResponse({
            "tools": tools.model_dump()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#@app.put("/api/lattice/tools/{tools_id}")
    
@app.delete("/api/lattice/tools/{tools_id}")
async def delete_tools(tools_id: str):
    try:
        if tools_id not in LatticeTools.list():
            raise HTTPException(status_code=404, detail="Tools not found")
        
        # Delete the tools
        LatticeTools.delete(tools_id)
        return JSONResponse({
            "status": "success",
            "tools_id": tools_id,
            "message": "Tools deleted successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/tools/{tools_id}/functions")
async def get_tool_functions(tools_id: str):
    try:
        alltools= LatticeTools.list()
        if tools_id not in alltools:
            raise HTTPException(status_code=404, detail="Tools not found")
        toolinfo=(LatticeTools.get(tools_id)).toollist
        import json
        toolfunctions=json.loads(toolinfo)
        function=[]
        for fun in toolfunctions:
            function.append(fun.get('function').get('name'))
        return JSONResponse({
            'functions': function
        })   
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lattice/tool/functions")
async def get_all_functions():
    try:
        
        alltools= LatticeTools.list()
        print(alltools)
        funcs=[]
        import json
        for tool in alltools:
            print(tool)
            toolinfo=(LatticeTools.get(tool)).toollist
            print(toolinfo)
            toolfunctions=json.loads(toolinfo)
            for fun in toolfunctions:
                funcs.append(fun.get('function').get('name'))
        return JSONResponse({
            'functions': funcs
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/lattice/tool/functions/{func_id}")
async def get_functions_details(func_id: str):
    try:
        alltools= LatticeTools.list()
        print(alltools)
        import json
        for tool in alltools:
            print(tool)
            toolinfo=(LatticeTools.get(tool)).toollist
            print(toolinfo)
            toolfunctions=json.loads(toolinfo)
            for fun in toolfunctions:
                if fun.get('function').get('name') == func_id:
                    return JSONResponse({
                        'function_details': fun.get('function')
                    })
        else:
            JSONResponse({
                'details': 'No such function found'

            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------  chat API endpoints ------------
@app.post("/api/chat")
@app.post("/api/lattice/chat")
async def chat(req: ChatRequest):
    try:
        if not req.messages or len(req.messages) == 0:
            raise HTTPException(status_code=400, detail="No messages provided")
        ai_response=await generate_ai_response(req.messages, req.model, req.tag)
        if not ai_response:
            raise HTTPException(status_code=500, detail="Failed to generate AI response")
        if req.stream:
            async def streamer():
                timestamp = get_timestamp()
                # Simulate streaming chat response
                # Yield initial response
                words = ai_response.split(" ")
                for i, word in enumerate(words):
                    await asyncio.sleep(0.05) 
                    yield json.dumps({
                        "model": req.model,
                        "created_at": timestamp,
                        "message": {
                            "role": "assistant",
                            "content": word
                        },
                        "done": False
                    })
                    await asyncio.sleep(0.1)

            return StreamingResponse(streamer(), media_type="application/json")

        return JSONResponse({
            "model": req.model,
            "created_at": get_timestamp(),
            "message": {
                "role": "assistant",
                "content": ai_response
            },
            "done": True
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    uvicorn.run('LatticePy.interfaces.webserver:app', host="0.0.0.0", port=port, workers=4)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('LatticePy.interfaces.webserver:app', host="0.0.0.0", port=3000, workers=4)
