from pydantic import ValidationError
from .ast import ModuleNode
from .core import TelosCompilationError
from .passes import SemanticVerifier, ASTOptimizer, WATGenerator

class TelosVMCompiler:
    def __init__(self):
        self.verifier = SemanticVerifier()
        self.optimizer = ASTOptimizer()
        self.generator = WATGenerator()

    def parse_and_verify(self, json_payload: str) -> ModuleNode:
        try:
            module = ModuleNode.model_validate_json(json_payload)
        except ValidationError as e:
            raise TelosCompilationError(f"Syntax/Schema Error: {e}")
        
        self.verifier.verify(module)
        self.optimizer.optimize(module)
        return module

    def compile_to_wat(self, module: ModuleNode) -> str:
        return self.generator.generate(module, self.verifier.symbol_table)
