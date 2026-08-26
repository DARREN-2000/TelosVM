import json

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

class DiagnosticEngine:
    @staticmethod
    def render_error(filepath: str, source: str, error: Exception):
        if isinstance(error, json.JSONDecodeError):
            DiagnosticEngine._render_json_error(filepath, source, error)
        elif isinstance(error, ValidationError):
            DiagnosticEngine._render_pydantic_error(filepath, source, error)
        else:
            # Fallback for Semantic/Hallucination errors where we might just string-match the issue
            DiagnosticEngine._render_semantic_error(filepath, source, str(error))

    @staticmethod
    def _render_json_error(filepath: str, source: str, error: json.JSONDecodeError):
        lines = source.splitlines()
        line_idx = error.lineno - 1
        col_idx = error.colno - 1
        
        snippet = Text()
        # Show previous line if exists
        if line_idx > 0:
            snippet.append(f"{error.lineno - 1:4} | {lines[line_idx - 1]}\n", style="dim")
            
        # Show error line
        snippet.append(f"{error.lineno:4} | {lines[line_idx]}\n", style="white")
        
        # Show caret
        caret_padding = " " * (7 + col_idx) # 4 (line no) + 3 ( | ) + col
        snippet.append(f"{caret_padding}^ {error.msg}\n", style="bold red")
        
        panel = Panel(snippet, title="[bold red]Syntax Error (Invalid JSON)[/bold red]", border_style="red")
        console.print(panel)

    @staticmethod
    def _render_pydantic_error(filepath: str, source: str, error: ValidationError):
        snippet = Text()
        snippet.append(f"Invalid Intent Schema detected in [bold cyan]{filepath}[/bold cyan]\n\n", style="white")
        
        for err in error.errors():
            loc = " -> ".join(str(l) for l in err['loc'])
            msg = err['msg']
            snippet.append(f"❌ Location: [bold yellow]{loc}[/bold yellow]\n", style="red")
            snippet.append(f"   Reason:   {msg}\n\n", style="white")
            
        panel = Panel(snippet, title="[bold red]Schema Validation Error[/bold red]", border_style="red")
        console.print(panel)

    @staticmethod
    def _render_semantic_error(filepath: str, source: str, error_msg: str):
        # We try to highlight the variable or operator if it's in the message
        # e.g., "Returning undeclared var: undefined_var"
        snippet = Text()
        snippet.append(f"{error_msg}\n\n", style="bold white")
        
        lines = source.splitlines()
        for i, line in enumerate(lines):
            # Very basic heuristic for highlighting context
            if any(word in line for word in error_msg.split() if len(word) > 3):
                snippet.append(f"{i+1:4} | {line}\n", style="dim yellow")
                
        panel = Panel(snippet, title="[bold red]Semantic Gatekeeper Violation[/bold red]", subtitle="[dim]Hallucination Detected[/dim]", border_style="red")
        console.print(panel)
