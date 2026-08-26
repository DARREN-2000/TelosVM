from typing import Literal, Union

from pydantic import BaseModel


class DeclareNode(BaseModel):
    type: Literal["Declare"]
    var: str
    value: int

class AssignNode(BaseModel):
    type: Literal["Assign"]
    var: str
    value: int | str

class MathOpNode(BaseModel):
    type: Literal["MathOp"]
    target: str
    operator: Literal["add", "sub", "mul", "div"]
    left: str
    right: str

class IfNode(BaseModel):
    type: Literal["If"]
    condition_var: str
    then_body: list['TelosNode']
    else_body: list['TelosNode'] | None = None

class WhileNode(BaseModel):
    type: Literal["While"]
    condition_var: str
    body: list['TelosNode']

class CallBuiltinNode(BaseModel):
    type: Literal["CallBuiltin"]
    function: Literal["print"]
    arg_var: str

class ReturnNode(BaseModel):
    type: Literal["Return"]
    var: str

TelosNode = Union[DeclareNode, AssignNode, MathOpNode, IfNode, WhileNode, CallBuiltinNode, ReturnNode]
IfNode.model_rebuild()
WhileNode.model_rebuild()

class ModuleNode(BaseModel):
    type: Literal["Module"]
    id: str
    nodes: list[TelosNode]
