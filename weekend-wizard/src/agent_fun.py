import asyncio, json, sys, re, os, logging
from typing import Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import chat  # pip install ollama

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wizard.log"),
    ]
)
logger = logging.getLogger("WeekendWizard")

SYSTEM = (
    "You are a cheerful weekend helper. You can call MCP tools.\n"
    "Decide step-by-step (ReAct). If you need a tool, output ONLY JSON:\n"
    '{"action":"","args":{...}}\n'
    "If you can answer, output ONLY JSON:\n"
    '{"action":"final","answer":"..."}'
)

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

MODEL_PARAMS = {"temperature": 0.2, "top_p": 0.9}

def llm_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    # Use global params
    logger.info("Calling LLM...")
    resp = chat(model="mistral:7b", messages=messages, options=MODEL_PARAMS)
    txt = resp["message"]["content"]
    logger.debug(f"LLM Raw Output: {txt}")
    
    cleaned = clean_json_text(txt)
    try:
        return json.loads(cleaned)
    except Exception:
        # force JSON if model drifted
        fix = chat(model="mistral:7b",
                   messages=[{"role": "system", "content": "Return ONLY valid JSON."},
                             {"role": "user", "content": f"Fix this JSON:\n{txt}"}],
                   options={"temperature": 0})
        fix_txt = fix["message"]["content"]
        cleaned_fix = clean_json_text(fix_txt)
        try:
            return json.loads(cleaned_fix)
        except Exception as e:
            print(f"\n[Error parsing JSON] Original: {txt!r}\nFix attempt: {fix_txt!r}")
            return {}

async def main():
    # Detect paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    prefs_path = os.path.join(base_dir, "config", "prefs.json")
    server_path = os.path.join(script_dir, "server_fun.py")

    # Load prefs
    prefs = {}
    try:
        with open(prefs_path, "r") as f:
            prefs = json.load(f)
            print(f"Loaded preferences: {prefs}")
    except FileNotFoundError:
        pass

    # Update global params from prefs if present
    if "model_temperature" in prefs:
        MODEL_PARAMS["temperature"] = prefs["model_temperature"]
    if "model_top_p" in prefs:
        MODEL_PARAMS["top_p"] = prefs["model_top_p"]

    # personalized system prompt
    personal_context = ""
    if prefs.get("favorite_genre"):
        personal_context += f" User loves {prefs['favorite_genre']} books."
    if prefs.get("home_city"):
        personal_context += f" User lives in {prefs['home_city']}."

    # server_path is now pre-defined above
    exit_stack = AsyncExitStack()
    # Note: We assume python is in path and used to run the server. 
    # If in venv, it should use the same python or explicit path.
    # To be safe, we can default to sys.executable to run the server with same python interpreter.
    
    stdio = await exit_stack.enter_async_context(
        stdio_client(StdioServerParameters(command=sys.executable, args=[server_path]))
    )
    r_in, w_out = stdio
    session = await exit_stack.enter_async_context(ClientSession(r_in, w_out))
    await session.initialize()

    tools = (await session.list_tools()).tools
    tool_index = {t.name: t for t in tools}
    print("Connected tools:", list(tool_index.keys()))

    history = [{"role": "system", "content": SYSTEM + personal_context}]
    try:
        while True:
            user = input("\nYou: ").strip()
            if not user or user.lower() in {"exit","quit"}: break
            history.append({"role": "user", "content": user})

            for _ in range(4):  # small safety loop
                print("🧙‍♂️ Thinking...", end="\r")
                decision = llm_json(history)
                if decision.get("action") == "final":
                    answer = decision.get("answer","")
                    # one-shot reflection
                    reflect = chat(model="mistral:7b",
                                   messages=[{"role":"system","content":"Check for mistakes or missing tool calls. If fine, reply 'looks good'; else give corrected answer."},
                                             {"role":"user","content": answer}],
                                   options={"temperature": 0})
                    if reflect["message"]["content"].strip().lower() != "looks good":
                        answer = reflect["message"]["content"]
                    print("\nAgent:", answer)
                    history.append({"role":"assistant","content": answer})
                    break

                tname = decision.get("action")
                args = decision.get("args", {})
                if tname not in tool_index:
                    logger.warning(f"Model tried to call unknown tool: {tname}")
                    history.append({"role":"assistant","content": f"(unknown tool {tname})"})
                    continue

                print(f"🔍 Calling tool: {tname}...", end="\r")
                logger.info(f"Calling tool: {tname} with args: {args}")
                result = await session.call_tool(tname, args)
                payload = result.content[0].text if result.content else result.model_dump_json()
                print(f"✅ Tool {tname} returned data.       ")
                history.append({"role":"assistant","content": f"[tool:{tname}] {payload}"})
    finally:
        await exit_stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())
