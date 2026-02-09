import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio, json, sys, re, os
from contextlib import AsyncExitStack
from typing import Dict, Any, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import chat

# Reuse agent logic (simplified for single-session demo)
SYSTEM = (
    "You are a cheerful weekend helper. You can call MCP tools.\n"
    "Decide step-by-step (ReAct). If you need a tool, output ONLY JSON:\n"
    '{"action":"","args":{...}}\n'
    "If you can answer, output ONLY JSON:\n"
    '{"action":"final","answer":"..."}'
)

app = fastapi.FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# Global state for the demo
session_context = {"history": [], "session": None, "exit_stack": None}

def clean_json_text(text: str) -> str:
    """Extract JSON from potential markdown code blocks or surrounding text."""
    # Remove markdown code blocks
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        text = match.group(1)
    
    text = text.strip()
    # Try to find the outer braces if there's extra text
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1:
        text = text[first : last + 1]
    return text

def llm_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    # Detect paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    prefs_path = os.path.join(base_dir, "config", "prefs.json")

    # Reuse prefs if available
    options = {"temperature": 0.2}
    try:
        if os.path.exists(prefs_path):
            with open(prefs_path) as f:
                prefs = json.load(f)
                options["temperature"] = prefs.get("model_temperature", 0.2)
    except: pass

    resp = chat(model="mistral:7b", messages=messages, options=options)
    txt = resp["message"]["content"]
    cleaned = clean_json_text(txt)
    try:
        return json.loads(cleaned)
    except Exception:
        fix = chat(model="mistral:7b",
                   messages=[{"role": "system", "content": "Return ONLY valid JSON."},
                             {"role": "user", "content": f"Fix this JSON:\n{txt}"}],
                   options={"temperature": 0})
        return json.loads(clean_json_text(fix["message"]["content"]))

@app.on_event("startup")
async def startup():
    # Detect paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    prefs_path = os.path.join(base_dir, "config", "prefs.json")
    server_path = os.path.join(script_dir, "server_fun.py")

    # Initialize MCP Client
    exit_stack = AsyncExitStack()
    stdio = await exit_stack.enter_async_context(
        stdio_client(StdioServerParameters(command=sys.executable, args=[server_path]))
    )
    r_in, w_out = stdio
    session = await exit_stack.enter_async_context(ClientSession(r_in, w_out))
    await session.initialize()
    
    session_context["exit_stack"] = exit_stack
    session_context["session"] = session
    
    # Preferences loading removed for increased flexibility
    session_context["history"] = [{"role": "system", "content": SYSTEM}]
    print("Web Agent initialized.")

@app.on_event("shutdown")
async def shutdown():
    if session_context["exit_stack"]:
        await session_context["exit_stack"].aclose()

from fastapi.responses import StreamingResponse

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    async def event_generator():
        history = session_context["history"]
        session = session_context["session"]
        tools = (await session.list_tools()).tools
        tool_index = {t.name: t for t in tools}

        history.append({"role": "user", "content": req.message})

        # Agent Loop
        try:
            for _ in range(5):
                yield f'data: {json.dumps({"status": "Thinking..."})}\n\n'
                decision = llm_json(history)
                
                if decision.get("action") == "final":
                    answer = decision.get("answer", "")
                    history.append({"role": "assistant", "content": answer})
                    yield f'data: {json.dumps({"reply": answer})}\n\n'
                    return
                
                tname = decision.get("action")
                args = decision.get("args", {})
                
                if tname in tool_index:
                    yield f'data: {json.dumps({"status": f"Calling tool: {tname}..."})}\n\n'
                    result = await session.call_tool(tname, args)
                    payload = result.content[0].text if result.content else result.model_dump_json()
                    history.append({"role": "assistant", "content": f"[tool:{tname}] {payload}"})
                else:
                    history.append({"role": "assistant", "content": f"(unknown tool {tname})"})
        except Exception as e:
            yield f'data: {json.dumps({"status": f"Error: {str(e)}"})}\n\n'
            yield f'data: {json.dumps({"reply": "I encountered an error while processing your request. Check the logs for details."})}\n\n'
            return
                
        yield f'data: {json.dumps({"reply": "I got stuck in a loop sorry!"})}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
