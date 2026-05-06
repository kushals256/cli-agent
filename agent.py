import json
import re
from llm import LLM
from tools import ToolRegistry, register_all_tools
from prompt import SYSTEM_PROMPT
from rich.console import Console

console = Console()


def extract_json_from_response(text):
    """
    Robustly extract a JSON object from LLM output.
    Handles: markdown fences, multiple objects, broken escaping in content fields.
    """
    text = text.strip()

    # Strip markdown fences
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Attempt 1: raw_decode (handles trailing junk / multiple objects)
    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(text)
        return obj
    except json.JSONDecodeError:
        pass

    # Attempt 2: regex-based extraction for TOOL steps with file content
    # The model often breaks JSON when embedding file content with quotes.
    # Strategy: extract the known fields manually.
    tool_match = re.search(
        r'"step"\s*:\s*"TOOL".*?"tool_name"\s*:\s*"(\w+)".*?"tool_args"\s*:\s*\{',
        text, re.DOTALL
    )
    if tool_match and "fs_write_file" in tool_match.group(1):
        # Extract path
        path_match = re.search(r'"path"\s*:\s*"([^"]+)"', text)
        # Extract content: everything between "content": " and the last "}
        content_match = re.search(
            r'"tool_args"\s*:\s*\{\s*"path"\s*:\s*"[^"]+"\s*,\s*"content"\s*:\s*"',
            text, re.DOTALL
        )
        if path_match and content_match:
            start = content_match.end()
            # Find the closing pattern: "}} or "} at the end
            # Work backwards from the end to find the closing braces
            end_text = text[start:]
            # Remove trailing braces and quotes
            # The content ends with something like: "}\n} or "\n}\n}
            # Find last occurrence of "}
            last_close = end_text.rfind('"')
            if last_close > 0:
                file_content = end_text[:last_close]
                # Unescape the content
                file_content = file_content.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
                return {
                    "step": "TOOL",
                    "content": "Saving file.",
                    "tool_name": "fs_write_file",
                    "tool_args": {
                        "path": path_match.group(1),
                        "content": file_content
                    }
                }

    # Attempt 3: Try to find any JSON object with braces
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[brace_start:i + 1])
                except json.JSONDecodeError:
                    break

    return None


class Agent:
    def __init__(self, model="google/gemma-3n-e2b-it"):
        self.llm = LLM(model=model)
        self.registry = ToolRegistry()
        register_all_tools(self.registry)
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _trim_messages(self):
        """
        Shrink the conversation history to keep API payloads small.
        - Keep system prompt and last 6 messages intact.
        - For older messages, replace large content with summaries.
        """
        if len(self.messages) <= 8:
            return
        
        # Keep: system (index 0), first user message (index 1), and last 6 messages
        keep_tail = 6
        for i in range(2, len(self.messages) - keep_tail):
            msg = self.messages[i]
            content = msg.get("content", "")
            
            # Shrink large OBSERVE messages (DOM, styles, file saves)
            if len(content) > 500:
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and parsed.get("step") == "OBSERVE":
                        original = parsed["content"]
                        parsed["content"] = original[:200] + "... [trimmed]"
                        self.messages[i]["content"] = json.dumps(parsed)
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass
                
                # Shrink large assistant messages (generated file content)
                if msg["role"] == "assistant" and len(content) > 500:
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict) and parsed.get("tool_name") == "fs_write_file":
                            parsed["tool_args"]["content"] = "[file content saved successfully — trimmed from history]"
                            self.messages[i]["content"] = json.dumps(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass

    def run(self, user_input, callback=None, max_steps=25):
        self.messages.append({"role": "user", "content": user_input})
        step_count = 0
        retries = 0
        max_retries = 3
        
        while step_count < max_steps:
            step_count += 1
            # Trim old messages to keep API payload small
            self._trim_messages()
            # Get LLM response via streaming
            assistant_msg = ""
            with console.status(f"[bold yellow]Agent is thinking (Step {step_count}/{max_steps})...[/bold yellow]"):
                for chunk in self.llm.chat(self.messages, stream=True):
                    assistant_msg += chunk
            
            state = extract_json_from_response(assistant_msg)
            
            if state is None:
                retries += 1
                console.print(f"[bold red]Parse error (retry {retries}/{max_retries})[/bold red]")
                console.print(f"[dim]Raw (first 200 chars): {assistant_msg[:200]}[/dim]")
                if retries >= max_retries:
                    console.print("[bold red]Max retries reached. Stopping.[/bold red]")
                    break
                self.messages.append({"role": "assistant", "content": assistant_msg})
                self.messages.append({"role": "user", "content": "Your response was not valid JSON. Respond with EXACTLY ONE JSON object. Try again."})
                continue
            
            # Reset retries on success
            retries = 0
            self.messages.append({"role": "assistant", "content": json.dumps(state)})

            if callback:
                callback(state)

            if state["step"] == "OUTPUT":
                break

            if state["step"] in ["START", "THINK"]:
                self.messages.append({"role": "user", "content": "Proceed to the next step."})

            if state["step"] == "TOOL":
                tool_name = state.get("tool_name", "")
                tool_args = state.get("tool_args", {})
                
                try:
                    result = self.registry.execute(tool_name, tool_args)
                except Exception as e:
                    result = f"Tool error: {e}"
                
                observe_msg = {
                    "step": "OBSERVE",
                    "content": str(result)[:2000]  # Limit observe size
                }
                
                self.messages.append({"role": "user", "content": json.dumps(observe_msg)})
                
                if callback:
                    callback(observe_msg)
        
        if step_count >= max_steps:
            max_step_msg = {
                "step": "OUTPUT",
                "content": "Maximum steps reached. Stopping to save API credits."
            }
            if callback:
                callback(max_step_msg)
    
    def cleanup(self):
        self.registry.cleanup()
