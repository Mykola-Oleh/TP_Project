"""Structured, ordered execution events for debugger and visualization clients."""
from collections.abc import Mapping
from dataclasses import dataclass
from . import ast
from .interpreter import Interpreter, ExecutionResult
from .parser import parse

@dataclass(frozen=True)
class TraceResult:
    result: ExecutionResult
    events: list[dict]

def trace_ast(tree: ast.Statement, state: Mapping[str, int] | None = None,
              max_steps: int = 10000) -> TraceResult:
    events: list[dict] = []
    result = Interpreter(state, max_steps, on_event=events.append).run(tree)
    return TraceResult(result, events)

def trace(source: str, state: Mapping[str, int] | None = None,
          max_steps: int = 10000) -> TraceResult:
    return trace_ast(parse(source), state, max_steps)
