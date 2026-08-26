import json
from pathlib import Path

import typer
from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .compiler import TelosVMCompiler
from .core import HallucinationError, TelosCompilationError, TelosExecutionError
from .executor import WasmExecutor

app = typer.Typer(help="TelosVM: AI-Native Compiler & Execution Control Plane", no_args_is_help=False)
console = Console()

def display_welcome_screen():
    logo_raw = r"""
   ______     __         _    ____  ___ 
  /_  __/__  / /___  ___| |  / /  |/  / 
   / / / _ \/ / __ \/ __/ | / / /|_/ /  
  / / /  __/ / /_/ /\__ \ |/ / /  / /   
 /_/  \___/_/\____/___/ |___/_/  /_/    
    """
    logo_text = Text()
    gradient_colors = ["#00f2fe", "#4facfe", "#00d2ff", "#3a7bd5", "#6a11cb", "#8f044d"]
    
    for i, line in enumerate(logo_raw.strip('\n').split('\n')):
        color = gradient_colors[i % len(gradient_colors)]
        logo_text.append(line + "\n", style=f"bold {color}")

    table = Table(show_header=False, expand=False, box=None, padding=(0, 3))
    table.add_column("Command", justify="right", style="bold #00d2ff")
    table.add_column("Description", justify="left", style="#a0a0a0")

    table.add_row("telos run", "Compile & execute a Telos JSON intent file")
    table.add_row("telos api", "Start the FastAPI Control Plane")
    
    tagline = Text("Next-Generation Virtual Machine & Compiler Infrastructure", style="italic #4facfe")
    version = Text("v2.4.0-edge", style="dim")
    
    help_text = Text()
    help_text.append("Type ", style="dim")
    help_text.append("telos --help", style="bold #8f044d")
    help_text.append(" for more information.", style="dim")

    ui_group = Group(
        Align.center(logo_text),
        Align.center(tagline),
        Align.center(version),
        Text("\n"),
        Align.center(table),
        Text("\n"),
        Align.center(help_text)
    )

    welcome_panel = Panel(
        ui_group,
        box=box.DOUBLE_EDGE,
        border_style="#6a11cb",
        title="[bold white] System Online [/]",
        subtitle="[dim] [ Telos CLI ] [/]",
        padding=(1, 4),
        width=80
    )

    console.print()
    console.print(Align.center(welcome_panel))
    console.print()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    TelosVM CLI Root.
    """
    if ctx.invoked_subcommand is None:
        display_welcome_screen()

@app.command()
def api():
    """Start the FastAPI Control Plane."""
    console.print("[bold green]Starting TelosVM API Server on port 8000...[/bold green]")
    import uvicorn
    uvicorn.run("telosvm.api:app", host="0.0.0.0", port=8000, reload=True)

@app.command()
def run(
    filepath: Path = typer.Argument(..., help="Path to the TelosVM JSON file"),
    compile_only: bool = typer.Option(False, "--compile-only", "-c", help="Only output WAT, do not execute"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON for agents")
):
    """Compile and execute a TelosVM JSON intent file."""
    if not filepath.exists():
        if json_output:
            print(json.dumps({"error": f"File {filepath} not found."}))
        else:
            console.print(f"[bold red]Error:[/bold red] File {filepath} not found.")
        raise typer.Exit(1)
        
    try:
        json_content = filepath.read_text()
        compiler = TelosVMCompiler()
        
        # Use rich progress for live loading feedback
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="[cyan]Semantic Verification...", total=None)
            module = compiler.parse_and_verify(json_content)
            
            progress.add_task(description="[magenta]Lowering to WebAssembly Text...", total=None)
            wat = compiler.compile_to_wat(module)
            
        if json_output:
            if compile_only:
                print(json.dumps({"status": "success", "wat": wat}))
                raise typer.Exit(0)
        else:
            console.print(Panel(Syntax(wat, "lisp", theme="monokai", line_numbers=True), title="[bold green]Compiled WebAssembly Text[/bold green]"))
            if compile_only:
                raise typer.Exit(0)
            console.print("\n[bold yellow]Initializing Sandboxed Wasmtime Execution...[/bold yellow]")
            
        result = WasmExecutor.execute(wat, use_rich=not json_output)
        
        if json_output:
            print(json.dumps({"status": "success", "result": result, "wat": wat}))
        else:
            console.print(f"[bold magenta]Execution Result:[/bold magenta] [white]{result}[/white]\n")
        
    except Exception as e:
        if json_output:
            print(json.dumps({"error": e.__class__.__name__, "detail": str(e)}))
            raise typer.Exit(1)
            
        import json as json_lib

        from pydantic import ValidationError

        from src.telosvm.diagnostics import DiagnosticEngine
        
        # If the file couldn't be read, source is missing
        source = json_content if 'json_content' in locals() else ""
        
        if isinstance(e, (json_lib.JSONDecodeError, ValidationError, HallucinationError, TelosCompilationError)):
            DiagnosticEngine.render_error(str(filepath), source, e)
        else:
            if isinstance(e, TelosExecutionError):
                console.print(Panel(f"[bold red]Sandbox Execution Error![/bold red]\n{str(e)}", border_style="red"))
            else:
                console.print(f"[bold red]Unexpected Error:[/bold red] {str(e)}")
        
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
