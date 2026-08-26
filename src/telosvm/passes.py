
from .ast import *
from .core import HallucinationError, NodeVisitor


class SemanticVerifier(NodeVisitor):
    def __init__(self):
        self.symbol_table = set()

    def verify(self, module: ModuleNode):
        self.symbol_table.clear()
        for node in module.nodes:
            self.visit(node)

    def visit_Declare(self, node: DeclareNode):
        if node.var in self.symbol_table:
            raise HallucinationError(f"Variable '{node.var}' already declared.")
        self.symbol_table.add(node.var)

    def visit_Assign(self, node: AssignNode):
        if node.var not in self.symbol_table:
            raise HallucinationError(f"Assigning to undeclared var '{node.var}'.")
        if isinstance(node.value, str) and node.value not in self.symbol_table:
            raise HallucinationError(f"Assigning from undeclared var '{node.value}'.")

    def visit_MathOp(self, node: MathOpNode):
        if node.left not in self.symbol_table: raise HallucinationError(f"Undeclared var '{node.left}'.")
        if node.right not in self.symbol_table: raise HallucinationError(f"Undeclared var '{node.right}'.")
        self.symbol_table.add(node.target)

    def visit_If(self, node: IfNode):
        if node.condition_var not in self.symbol_table: raise HallucinationError(f"Condition var '{node.condition_var}' undeclared.")
        for child in node.then_body: self.visit(child)
        if node.else_body:
            for child in node.else_body: self.visit(child)

    def visit_While(self, node: WhileNode):
        if node.condition_var not in self.symbol_table: raise HallucinationError(f"Loop condition '{node.condition_var}' undeclared.")
        for child in node.body: self.visit(child)

    def visit_CallBuiltin(self, node: CallBuiltinNode):
        if node.arg_var not in self.symbol_table: raise HallucinationError(f"Calling {node.function} on undeclared var '{node.arg_var}'.")

    def visit_Return(self, node: ReturnNode):
        if node.var not in self.symbol_table: raise HallucinationError(f"Returning undeclared var '{node.var}'.")


class ASTOptimizer(NodeVisitor):
    def __init__(self):
        self.constants = {}

    def optimize(self, module: ModuleNode):
        self.constants.clear()
        module.nodes = self.optimize_block(module.nodes)

    def optimize_block(self, nodes: list[TelosNode]) -> list[TelosNode]:
        optimized = []
        for node in nodes:
            # Check conditions BEFORE visit (since visit might clear constants)
            if isinstance(node, IfNode):
                cond_val = self.constants.get(node.condition_var)
                self.visit(node)
                if cond_val == 0:
                    if node.else_body:
                        optimized.extend(self.optimize_block(node.else_body))
                    continue
                elif cond_val is not None and cond_val != 0:
                    optimized.extend(self.optimize_block(node.then_body))
                    continue
                else:
                    node.then_body = self.optimize_block(node.then_body)
                    if node.else_body:
                        node.else_body = self.optimize_block(node.else_body)
                    optimized.append(node)
            
            elif isinstance(node, WhileNode):
                cond_val = self.constants.get(node.condition_var)
                self.visit(node)
                if cond_val == 0:
                    continue
                else:
                    node.body = self.optimize_block(node.body)
                    optimized.append(node)
            
            elif isinstance(node, MathOpNode):
                self.visit(node)
                if node.left in self.constants and node.right in self.constants:
                    from src.telosvm.ast import AssignNode
                    optimized.append(AssignNode(type="Assign", var=node.target, value=self.constants[node.target]))
                else:
                    optimized.append(node)
                    
            else:
                self.visit(node)
                optimized.append(node)
        return optimized

    def visit_Declare(self, node: DeclareNode): self.constants[node.var] = node.value
    def visit_Assign(self, node: AssignNode):
        if isinstance(node.value, int): self.constants[node.var] = node.value
        elif node.value in self.constants:
            node.value = self.constants[node.value]
            self.constants[node.var] = node.value
        else: self.constants.pop(node.var, None)

    def visit_MathOp(self, node: MathOpNode):
        if node.left in self.constants and node.right in self.constants:
            l = self.constants[node.left]
            r = self.constants[node.right]
            res = 0
            if node.operator == "add": res = l + r
            elif node.operator == "sub": res = l - r
            elif node.operator == "mul": res = l * r
            elif node.operator == "div" and r != 0: res = l // r
            self.constants[node.target] = res
        else: self.constants.pop(node.target, None)

    def visit_If(self, node: IfNode):
        self.constants.clear()

    def visit_While(self, node: WhileNode):
        self.constants.clear()

    def visit_CallBuiltin(self, node: CallBuiltinNode): pass
    def visit_Return(self, node: ReturnNode): pass


class WATGenerator(NodeVisitor):
    def __init__(self):
        self.label_counter = 0

    def generate(self, module: ModuleNode, symbol_table: set) -> str:
        wat = ["(module"]
        wat.append('  (import "env" "print" (func $print (param i32)))')
        wat.append('  (func $run (result i32)')
        for var in symbol_table: wat.append(f'    (local ${var} i32)')
        for node in module.nodes: wat.extend(self.visit(node, indent=4))
        wat.append("    i32.const 0")
        wat.append("  )")
        wat.append('  (export "run" (func $run))')
        wat.append(")")
        return "\n".join(wat)

    def visit_Declare(self, node: DeclareNode, indent: int) -> list[str]:
        ind = " " * indent
        return [f'{ind}i32.const {node.value}', f'{ind}local.set ${node.var}']

    def visit_Assign(self, node: AssignNode, indent: int) -> list[str]:
        ind = " " * indent
        lines = [f'{ind}i32.const {node.value}'] if isinstance(node.value, int) else [f'{ind}local.get ${node.value}']
        lines.append(f'{ind}local.set ${node.var}')
        return lines

    def visit_MathOp(self, node: MathOpNode, indent: int) -> list[str]:
        ind = " " * indent
        op_map = {"add": "i32.add", "sub": "i32.sub", "mul": "i32.mul", "div": "i32.div_s"}
        return [f'{ind}local.get ${node.left}', f'{ind}local.get ${node.right}', f'{ind}{op_map[node.operator]}', f'{ind}local.set ${node.target}']

    def visit_If(self, node: IfNode, indent: int) -> list[str]:
        ind = " " * indent
        lines = [f'{ind}local.get ${node.condition_var}', f'{ind}if']
        for child in node.then_body: lines.extend(self.visit(child, indent + 2))
        if node.else_body:
            lines.append(f'{ind}else')
            for child in node.else_body: lines.extend(self.visit(child, indent + 2))
        lines.append(f'{ind}end')
        return lines

    def visit_While(self, node: WhileNode, indent: int) -> list[str]:
        ind = " " * indent
        lbl = self.label_counter
        self.label_counter += 1
        lines = [f'{ind}block $exit_{lbl}', f'{ind}  loop $loop_{lbl}', f'{ind}    local.get ${node.condition_var}', f'{ind}    i32.eqz', f'{ind}    br_if $exit_{lbl}']
        for child in node.body: lines.extend(self.visit(child, indent + 4))
        lines.extend([f'{ind}    br $loop_{lbl}', f'{ind}  end', f'{ind}end'])
        return lines

    def visit_CallBuiltin(self, node: CallBuiltinNode, indent: int) -> list[str]:
        ind = " " * indent
        return [f'{ind}local.get ${node.arg_var}', f'{ind}call ${node.function}']

    def visit_Return(self, node: ReturnNode, indent: int) -> list[str]:
        ind = " " * indent
        return [f'{ind}local.get ${node.var}', f'{ind}return']
