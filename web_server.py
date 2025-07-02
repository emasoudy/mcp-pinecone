from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import time
import os
import sys

# Add the src directory to Python path to import mcp_pinecone
sys.path.append('/app/src')

app = FastAPI(title="MCP Pinecone Web Server - Production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Pinecone client
pinecone_client = None

def get_pinecone_client():
    global pinecone_client
    if pinecone_client is None:
        try:
            from mcp_pinecone.pinecone import PineconeClient
            pinecone_client = PineconeClient()
            print("✅ Pinecone client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Pinecone client: {e}")
            pinecone_client = None
    return pinecone_client

@app.get("/")
async def mcp_root():
    """MCP protocol initialization"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True}
        },
        "serverInfo": {
            "name": "pinecone-mcp-production",
            "version": "1.0.0"
        }
    }

@app.get("/sse")
async def sse_endpoint():
    """Server-Sent Events endpoint"""
    async def event_stream():
        yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
        
        init_message = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True}
            },
            "serverInfo": {
                "name": "pinecone-mcp-production",
                "version": "1.0.0"
            }
        }
        yield f"data: {json.dumps(init_message)}\n\n"
        
        while True:
            try:
                await asyncio.sleep(30)
                heartbeat = {'type': 'heartbeat', 'timestamp': str(time.time())}
                yield f"data: {json.dumps(heartbeat)}\n\n"
            except asyncio.CancelledError:
                return

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/")
async def mcp_handler(request: Request):
    """Handle MCP JSON-RPC requests with REAL Pinecone integration"""
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
                        "description": "Search for information in the Pinecone knowledge base using semantic similarity",
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
                        "description": "Add a document to the Pinecone knowledge base for future retrieval",
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
                        "description": "List all documents stored in the Pinecone knowledge base",
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
                        "description": "Retrieve a specific document by its ID from Pinecone",
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
                        "description": "Get real statistics about the Pinecone index usage",
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
        
        # Get Pinecone client
        pc_client = get_pinecone_client()
        
        if not pc_client:
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [{
                        "type": "text",
                        "text": "❌ Pinecone client not available. Check API credentials and connection."
                    }]
                }
            }
        
        try:
            if tool_name == "semantic-search":
                query = arguments.get("query", "")
                limit = arguments.get("limit", 5)
                
                try:
                    # Generate embedding for search query
                    search_embedding = pc_client.pc.inference.embed(
                        model="multilingual-e5-large",
                        inputs=[query],
                        parameters={"input_type": "query"}
                    )
                    
                    embedding_vector = search_embedding[0]['values']
                    
                    # Pad to 1536 dimensions if needed
                    if len(embedding_vector) < 1536:
                        embedding_vector.extend([0.0] * (1536 - len(embedding_vector)))
                    elif len(embedding_vector) > 1536:
                        embedding_vector = embedding_vector[:1536]
                    
                    # Search using the embedding
                    search_results = pc_client.index.query(
                        vector=embedding_vector,
                        top_k=limit,
                        include_metadata=True
                    )
                    
                    results = search_results.get('matches', [])
                    
                    if results and len(results) > 0:
                        result_text = f"🔍 Found {len(results)} results for: '{query}'\n\n"
                        for i, result in enumerate(results, 1):
                            score = result.get('score', 0)
                            metadata = result.get('metadata', {})
                            title = metadata.get('title', f'Document {i}')
                            content = metadata.get('content', 'No content available')[:200]
                            
                            result_text += f"**{i}. {title}** (Relevance: {score:.3f})\n"
                            result_text += f"{content}...\n\n"
                    else:
                        result_text = f"🔍 No results found for: '{query}'\n\nTry different keywords or add more documents to the knowledge base."
                    
                    return {
                        "jsonrpc": "2.0", 
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": result_text
                            }]
                        }
                    }
                except Exception as search_error:
                    return {
                        "jsonrpc": "2.0", 
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"🔍 Search attempted for: '{query}'\n\n❌ Search error: {str(search_error)}"
                            }]
                        }
                    }
            
            elif tool_name == "process-document":
                content = arguments.get("content", "")
                title = arguments.get("title", "Untitled Document")
                metadata = arguments.get("metadata", {})
                
                try:
                    # Use available Pinecone model and handle dimension mismatch
                    embedding_response = pc_client.pc.inference.embed(
                        model="multilingual-e5-large",  # Available in Pinecone, produces 1024 dims
                        inputs=[content],
                        parameters={"input_type": "passage"}
                    )
                    
                    embedding_vector = embedding_response[0]['values']
                    
                    # Pad or truncate to match your 1536 index
                    if len(embedding_vector) < 1536:
                        # Pad with zeros to reach 1536
                        embedding_vector.extend([0.0] * (1536 - len(embedding_vector)))
                    elif len(embedding_vector) > 1536:
                        # Truncate to 1536
                        embedding_vector = embedding_vector[:1536]
                    
                    doc_id = f"doc_{int(time.time())}_{abs(hash(content)) % 10000}"
                    
                    vector_data = {
                        "id": doc_id,
                        "values": embedding_vector,
                        "metadata": {
                            "title": title,
                            "content": content,
                            **metadata
                        }
                    }
                    
                    upsert_response = pc_client.index.upsert(vectors=[vector_data])
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"✅ Document stored successfully!\n\n📝 Title: {title}\n📄 Content: {content[:100]}...\n🆔 Document ID: {doc_id}\n\n🎯 Your strategic insight is now stored and searchable!"
                            }]
                        }
                    }
                    
                except Exception as embed_error:
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"❌ Storage error: {str(embed_error)}\n\nDocument: '{title}'"
                            }]
                        }
                    }
            
            elif tool_name == "list-documents":
                limit = arguments.get("limit", 10)
                
                try:
                    # Query all vectors from your index
                    query_response = pc_client.index.query(
                        vector=[0.0] * 1536,  # Dummy vector for listing
                        top_k=limit,
                        include_metadata=True
                    )
                    
                    documents = query_response.get('matches', [])
                    
                    if documents and len(documents) > 0:
                        doc_text = f"📚 Knowledge Base Documents (showing {len(documents)} of up to {limit}):\n\n"
                        for i, doc in enumerate(documents, 1):
                            doc_id = doc.get('id', 'Unknown')
                            metadata = doc.get('metadata', {})
                            title = metadata.get('title', 'Untitled')
                            content_preview = metadata.get('content', '')[:100]
                            
                            doc_text += f"**{i}. {title}**\n"
                            doc_text += f"   ID: {doc_id}\n"
                            doc_text += f"   Preview: {content_preview}...\n\n"
                    else:
                        doc_text = "📚 No documents found in the knowledge base.\n\nUse the process-document tool to add your first piece of knowledge!"
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": doc_text
                            }]
                        }
                    }
                except Exception as list_error:
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"📚 List error: {str(list_error)}"
                            }]
                        }
                    }
            
            elif tool_name == "read-document":
                document_id = arguments.get("document_id", "")
                
                try:
                    # Fetch specific document by ID
                    fetch_response = pc_client.index.fetch(ids=[document_id])
                    
                    if document_id in fetch_response.get('vectors', {}):
                        doc_data = fetch_response['vectors'][document_id]
                        metadata = doc_data.get('metadata', {})
                        title = metadata.get('title', 'Untitled')
                        content = metadata.get('content', 'No content available')
                        
                        doc_text = f"📄 **{title}**\n\n{content}\n\n---\n**Document ID:** {document_id}"
                    else:
                        doc_text = f"❌ Document '{document_id}' not found."
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": doc_text
                            }]
                        }
                    }
                except Exception as read_error:
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"📄 Read error: {str(read_error)}"
                            }]
                        }
                    }
            
            elif tool_name == "pinecone-stats":
                try:
                    # Get real statistics from your index
                    stats_response = pc_client.index.describe_index_stats()
                    
                    stats_text = "📊 **Live Index Statistics**\n\n"
                    stats_text += f"🗃️ **Total vectors:** {stats_response.get('total_vector_count', 0)}\n"
                    stats_text += f"🏷️ **Namespaces:** {len(stats_response.get('namespaces', {}))}\n"
                    stats_text += f"🔢 **Dimension:** 1536\n"
                    stats_text += f"📏 **Metric:** cosine similarity\n"
                    stats_text += f"🌐 **Index:** memory-index\n\n"
                    stats_text += "✨ **Real-time data from your Pinecone index!**"
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": stats_text
                            }]
                        }
                    }
                except Exception as stats_error:
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": f"📊 Stats error: {str(stats_error)}"
                            }]
                        }
                    }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [{
                        "type": "text",
                        "text": f"❌ Unexpected error executing {tool_name}: {str(e)}"
                    }]
                }
            }
        
        return {
            "jsonrpc": "2.0", 
            "id": body.get("id"),
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"🔧 Tool '{tool_name}' called but not implemented yet."
                }]
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
                    "name": "pinecone-mcp-production",
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
    pc_client = get_pinecone_client()
    return {
        "status": "healthy", 
        "service": "mcp-pinecone-production",
        "pinecone_connected": pc_client is not None
    }

@app.get("/tools")
async def list_tools():
    return {
        "tools": [
            "semantic-search",
            "process-document", 
            "list-documents",
            "read-document",
            "pinecone-stats"
        ],
        "mode": "production",
        "pinecone_integration": "enabled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
