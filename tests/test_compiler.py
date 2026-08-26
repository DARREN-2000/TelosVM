import pytest
import json
from src.telosvm.compiler import TelosVMCompiler
from src.telosvm.executor import WasmExecutor
from src.telosvm.core import HallucinationError, TelosCompilationError

@pytest.fixture
def compiler():
    return TelosVMCompiler()

def compile_and_run(compiler, intent_dict):
    ast = compiler.parse_and_verify(json.dumps(intent_dict))
    wat = compiler.compile_to_wat(ast)
    return WasmExecutor.execute(wat)

def test_e2e_basic_return(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Declare", "var": "x", "value": 42},
            {"type": "Return", "var": "x"}
        ]
    }
    assert compile_and_run(compiler, intent) == 42

def test_e2e_variable_reassignment(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Declare", "var": "x", "value": 10},
            {"type": "Assign", "var": "x", "value": 20},
            {"type": "Return", "var": "x"}
        ]
    }
    assert compile_and_run(compiler, intent) == 20

def test_e2e_constant_folding(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Declare", "var": "a", "value": 5},
            {"type": "Declare", "var": "b", "value": 10},
            {"type": "Declare", "var": "c", "value": 0},
            {"type": "MathOp", "target": "c", "operator": "mul", "left": "a", "right": "b"},
            {"type": "Return", "var": "c"}
        ]
    }
    ast = compiler.parse_and_verify(json.dumps(intent))
    wat = compiler.compile_to_wat(ast)
    assert "i32.mul" not in wat
    assert WasmExecutor.execute(wat) == 50

def test_e2e_dead_code_elimination(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Declare", "var": "flag", "value": 0},
            {"type": "Declare", "var": "result", "value": 100},
            {
                "type": "If", "condition_var": "flag",
                "then_body": [{"type": "Assign", "var": "result", "value": 500}],
                "else_body": [{"type": "Assign", "var": "result", "value": 200}]
            },
            {"type": "Return", "var": "result"}
        ]
    }
    ast = compiler.parse_and_verify(json.dumps(intent))
    wat = compiler.compile_to_wat(ast)
    assert "if" not in wat
    assert WasmExecutor.execute(wat) == 200

def test_e2e_while_loop(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Declare", "var": "counter", "value": 3},
            {"type": "Declare", "var": "result", "value": 10},
            {
                "type": "While", "condition_var": "counter",
                "body": [
                    {"type": "Declare", "var": "one", "value": 1},
                    {"type": "MathOp", "target": "result", "operator": "add", "left": "result", "right": "one"},
                    {"type": "MathOp", "target": "counter", "operator": "sub", "left": "counter", "right": "one"}
                ]
            },
            {"type": "Return", "var": "result"}
        ]
    }
    assert compile_and_run(compiler, intent) == 13

def test_e2e_division(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Declare", "var": "a", "value": 20},
            {"type": "Declare", "var": "b", "value": 4},
            {"type": "Declare", "var": "c", "value": 0},
            {"type": "MathOp", "target": "c", "operator": "div", "left": "a", "right": "b"},
            {"type": "Return", "var": "c"}
        ]
    }
    assert compile_and_run(compiler, intent) == 5

def test_semantic_duplicate_declare(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Declare", "var": "x", "value": 1},
            {"type": "Declare", "var": "x", "value": 2}
        ]
    }
    with pytest.raises(HallucinationError, match="already declared"):
        compiler.parse_and_verify(json.dumps(intent))

def test_semantic_undeclared_variable(compiler):
    intent = {
        "type": "Module", "id": "main",
        "nodes": [
            {"type": "Return", "var": "undefined_var"}
        ]
    }
    with pytest.raises(HallucinationError, match="Returning undeclared var"):
        compiler.parse_and_verify(json.dumps(intent))
