from fastapi import FastAPI
from fastapi.responses import JSONResponse
import asyncio
import json
import subprocess
import os
import sys

app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "mcp-pinecone-web", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/mcp")
async def mcp_endpoint(request: dict):
    """Handle MCP requests via HTTP"""
    try:
        # Import and use the MCP server directly
        from mcp_pinecone.server import app as mcp_app
        
        # Process the MCP request
        response = await mcp_app.handle_request(request)
        return response
        
    except Exception as e:
        return {"error": str(e), "type": "mcp_error"}

@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
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
    uvicorn.run(app, host="0.0.0.0", port=3000)
