from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import time

app = FastAPI(title="MCP Pinecone Web Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def mcp_root():
    """Simplified MCP response without jsonrpc wrapper"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True}
        },
        "serverInfo": {
            "name": "pinecone-mcp",
            "version": "1.0.0"
        }
    }

@app.get("/sse")
async def sse_endpoint():
    """Server-Sent Events endpoint for MCP"""
    async def event_stream():
        # Send initial connection
        yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
        
        # Send MCP initialization
        init_message = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True}
            },
            "serverInfo": {
                "name": "pinecone-mcp",
                "version": "1.0.0"
            }
        }
        yield f"data: {json.dumps(init_message)}\n\n"
        
        # Keep connection alive with heartbeat
        while True:
            try:
                await asyncio.sleep(30)
                heartbeat = {
                    'type': 'heartbeat', 
                    'timestamp': str(time.time())
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
            except asyncio.CancelledError:
                return

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/")
async def mcp_handler(request: Request):
    """Handle MCP JSON-RPC requests"""
    try:
        body = await request.json()
    except:
        return {"error": "Invalid JSON"}
    
    if body.get("method") == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "semantic-search",
                        "description": "Search for information in the knowledge base using semantic similarity",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string", 
                                    "description": "Search query to find relevant information"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Maximum number of results to return",
                                    "default": 5
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "process-document", 
                        "description": "Add a document to the knowledge base for future retrieval",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string", 
                                    "description": "The main content of the document"
                                },
                                "title": {
                                    "type": "string", 
                                    "description": "Title or identifier for the document"
                                },
                                "metadata": {
                                    "type": "object",
                                    "description": "Additional metadata about the document"
                                }
                            },
                            "required": ["content"]
                        }
                    },
                    {
                        "name": "list-documents",
                        "description": "List all documents stored in the knowledge base",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "description": "Maximum number of documents to return",
                                    "default": 10
                                }
                            }
                        }
                    },
                    {
                        "name": "read-document",
                        "description": "Retrieve a specific document by its ID",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "document_id": {
                                    "type": "string",
                                    "description": "Unique identifier of the document to retrieve"
                                }
                            },
                            "required": ["document_id"]
                        }
                    },
                    {
                        "name": "pinecone-stats",
                        "description": "Get statistics about the Pinecone index usage",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }
    
    elif body.get("method") == "tools/call":
        tool_name = body.get("params", {}).get("name")
        arguments = body.get("params", {}).get("arguments", {})
        
        if tool_name == "semantic-search":
            query = arguments.get("query", "")
            return {
                "jsonrpc": "2.0", 
                "id": body.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🔍 Searching for: '{query}'\n\n📄 Found relevant information:\n- Sample result 1 related to your query\n- Sample result 2 with matching content\n- Sample result 3 from knowledge base\n\n(This is a demo response - actual search would query Pinecone)"
                        }
                    ]
                }
            }
        elif tool_name == "process-document":
            content = arguments.get("content", "")
            title = arguments.get("title", "Untitled Document")
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✅ Document processed successfully!\n\n📝 Title: {title}\n📄 Content length: {len(content)} characters\n🗂️ Added to knowledge base\n\n(This is a demo response - actual processing would store in Pinecone)"
                        }
                    ]
                }
            }
        elif tool_name == "list-documents":
            limit = arguments.get("limit", 10)
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"📚 Knowledge Base Documents (showing up to {limit}):\n\n1. Document ID: doc_001 - 'Introduction to AI'\n2. Document ID: doc_002 - 'Machine Learning Basics'\n3. Document ID: doc_003 - 'Vector Databases Guide'\n\n(This is a demo response - actual listing would query Pinecone)"
                        }
                    ]
                }
            }
        elif tool_name == "pinecone-stats":
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "📊 Pinecone Index Statistics:\n\n🗃️ Total vectors: 1,247\n💾 Index size: 15.2 MB\n🔧 Dimensions: 1536\n📈 Query count today: 42\n⚡ Average query time: 23ms\n\n(This is a demo response - actual stats would query Pinecone)"
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0", 
                "id": body.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"🔧 Tool '{tool_name}' called with arguments: {json.dumps(arguments, indent=2)}\n\n(Demo response - tool integration pending)"
                        }
                    ]
                }
            }
    
    elif body.get("method") == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True, "listChanged": True}
                },
                "serverInfo": {
                    "name": "pinecone-mcp",
                    "version": "1.0.0"
                }
            }
        }
    
    return {
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "error": {
            "code": -32601,
            "message": f"Method '{body.get('method')}' not found"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp-pinecone-web"}

@app.get("/tools")
async def list_tools():
    return {
        "tools": [
            "semantic-search",
            "process-document", 
            "list-documents",
            "read-document",
            "pinecone-stats"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
