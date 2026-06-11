import os
import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from agent import Agent
from llm import validate_api_key
from tools import ensure_playwright_browsers

console = Console()

def display_state(state):
    step = state.get("step", "UNKNOWN")
    content = state.get("content", "")
    
    color = "white"
    if step == "START": color = "cyan"
    elif step == "THINK": color = "yellow"
    elif step == "TOOL": color = "magenta"
    elif step == "OBSERVE": color = "green"
    elif step == "OUTPUT": color = "blue"

    panel = Panel(
        content,
        title=f"[bold {color}]{step}[/bold {color}]",
        border_style=color
    )
    console.print(panel)

def main():
    console.print(Panel.fit(
        "Welcome to [bold cyan]Frontend Reconstruction Agent[/bold cyan]",
        border_style="cyan"
    ))

    key_error = validate_api_key()
    if key_error:
        console.print(Panel(key_error, title="[bold red]API Key Required[/bold red]", border_style="red"))
        sys.exit(1)

    with console.status("[bold yellow]Checking Playwright browsers...[/bold yellow]"):
        try:
            ensure_playwright_browsers()
        except RuntimeError as e:
            console.print(Panel(str(e), title="[bold red]Playwright Setup Failed[/bold red]", border_style="red"))
            sys.exit(1)

    agent = Agent()
    
    try:
        while True:
            user_input = console.input("[bold green]You:[/bold green] ")
            if user_input.lower() in ["exit", "quit"]:
                break

            # Shell shortcuts — run locally instead of sending to the LLM
            if user_input.strip().lower().startswith("open "):
                path = user_input.strip().split(maxsplit=1)[1]
                if os.path.exists(path):
                    subprocess.run(["open", path], check=False)
                    console.print(f"[green]Opened {path} in your browser.[/green]")
                else:
                    console.print(f"[red]File not found: {path}[/red]")
                continue
            
            try:
                agent.run(user_input, callback=display_state)
            except RuntimeError as e:
                console.print(Panel(str(e), title="[bold red]Error[/bold red]", border_style="red"))
                
    except KeyboardInterrupt:
        console.print("\n[bold red]Stopping agent...[/bold red]")
    finally:
        try:
            agent.cleanup()
        except Exception:
            pass
        console.print("[bold cyan]Goodbye![/bold cyan]")

if __name__ == "__main__":
    main()
