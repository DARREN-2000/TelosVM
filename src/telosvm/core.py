from typing import Any
from .ast import TelosNode

class TelosCompilationError(Exception): pass
class HallucinationError(TelosCompilationError): pass
class TelosExecutionError(Exception): pass

class NodeVisitor:
    """Base Visitor Pattern for cleanly traversing the AST."""
    def visit(self, node: TelosNode, *args: Any, **kwargs: Any) -> Any:
        method_name = f'visit_{node.type}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node: TelosNode, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError(f"No visit_{node.type} method defined.")
