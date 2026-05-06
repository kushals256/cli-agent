import sys
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from agent import Agent

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

    agent = Agent()
    
    try:
        while True:
            user_input = console.input("[bold green]You:[/bold green] ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            agent.run(user_input, callback=display_state)
                
    except KeyboardInterrupt:
        console.print("\n[bold red]Stopping agent...[/bold red]")
    finally:
        agent.cleanup()
        console.print("[bold cyan]Goodbye![/bold cyan]")

if __name__ == "__main__":
    main()
