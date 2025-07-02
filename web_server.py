from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def mcp_root():
    """MCP protocol initialization endpoint"""
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                }
            },
            "serverInfo": {
                "name": "pinecone-mcp",
                "version": "1.0.0"
            }
        }
    }

@app.post("/")
async def mcp_handler(request: Request):
    """Handle MCP JSON-RPC requests"""
    body = await request.json()
    
    if body.get("method") == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "semantic-search",
                        "description": "Search for information in the knowledge base",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "process-document", 
                        "description": "Add document to knowledge base",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "Document content"},
                                "title": {"type": "string", "description": "Document title"}
                            },
                            "required": ["content"]
                        }
                    }
                ]
            }
        }
    
    elif body.get("method") == "tools/call":
        tool_name = body.get("params", {}).get("name")
        arguments = body.get("params", {}).get("arguments", {})
        
        # Here you would integrate with your actual MCP pinecone functions
        return {
            "jsonrpc": "2.0", 
            "id": body.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Tool {tool_name} called with args: {arguments}"
                    }
                ]
            }
        }
    
    return {
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "error": {
            "code": -32601,
            "message": "Method not found"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
