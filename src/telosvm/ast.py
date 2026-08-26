from typing import List, Union, Literal, Optional
from pydantic import BaseModel

class DeclareNode(BaseModel):
    type: Literal["Declare"]
    var: str
    value: int

class AssignNode(BaseModel):
    type: Literal["Assign"]
    var: str
    value: Union[int, str]

class MathOpNode(BaseModel):
    type: Literal["MathOp"]
    target: str
    operator: Literal["add", "sub", "mul", "div"]
    left: str
    right: str

class IfNode(BaseModel):
    type: Literal["If"]
    condition_var: str
    then_body: List['TelosNode']
    else_body: Optional[List['TelosNode']] = None

class WhileNode(BaseModel):
    type: Literal["While"]
    condition_var: str
    body: List['TelosNode']

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
    nodes: List[TelosNode]
