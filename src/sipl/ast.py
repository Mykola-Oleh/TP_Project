from dataclasses import dataclass
from typing import TypeAlias

@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int

@dataclass(frozen=True)
class Number:
    value: int
    span: SourceSpan

@dataclass(frozen=True)
class Variable:
    name: str
    span: SourceSpan

@dataclass(frozen=True)
class Unary:
    op: str
    operand: "Expression"
    span: SourceSpan

@dataclass(frozen=True)
class Binary:
    op: str
    left: "Expression"
    right: "Expression"
    span: SourceSpan

Expression: TypeAlias = Number | Variable | Unary | Binary

@dataclass(frozen=True)
class Assign:
    name: str
    value: Expression
    span: SourceSpan

@dataclass(frozen=True)
class Skip:
    span: SourceSpan

@dataclass(frozen=True)
class If:
    condition: Expression
    then_branch: "Statement"
    else_branch: "Statement"
    span: SourceSpan

@dataclass(frozen=True)
class While:
    condition: Expression
    body: "Statement"
    span: SourceSpan

@dataclass(frozen=True)
class Block:
    statements: tuple["Statement", ...]
    span: SourceSpan

Statement: TypeAlias = Assign | Skip | If | While | Block
