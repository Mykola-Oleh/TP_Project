from collections.abc import Mapping, Callable
from dataclasses import dataclass
from . import ast


class ExecutionError(RuntimeError):
    def __init__(self, message: str, location: ast.SourceSpan):
        self.location = location
        super().__init__(f"Runtime error at {location.line}:{location.column}: {message}")


class StepLimitExceeded(ExecutionError):
    pass


@dataclass(frozen=True)
class ExecutionResult:
    state: dict[str, int]
    steps: int

class Interpreter:
    def __init__(self, state: Mapping[str, int] | None = None, max_steps: int = 10000,
                 on_event: Callable[[dict], None] | None = None):
        if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        self.state = {}
        for key, value in (state or {}).items():
            if not isinstance(key, str) or not key.isidentifier():
                raise ValueError(f"Invalid variable name: {key!r}")
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Initial value of {key} must be an integer")
            self.state[key] = value
        self.max_steps = max_steps
        self.steps = 0
        self.on_event = on_event

    def _emit(self, kind: str, node: ast.Statement, **details):
        if self.on_event is not None:
            self.on_event({"event": kind, "step": self.steps,
                           "statement": type(node).__name__,
                           "span": {"line": node.span.line, "column": node.span.column,
                                    "end_line": node.span.end_line, "end_column": node.span.end_column},
                           "state": dict(self.state), **details})

    def _tick(self, node: ast.Statement):
        if self.steps >= self.max_steps:
            raise StepLimitExceeded(f"step limit ({self.max_steps}) exceeded", node.span)
        self.steps += 1

    def evaluate(self, node: ast.Expression) -> int | bool:
        if isinstance(node, ast.Number):
            return node.value
        if isinstance(node, ast.Variable):
            if node.name not in self.state:
                raise ExecutionError(f"undefined variable '{node.name}'", node.span)
            return self.state[node.name]
        if isinstance(node, ast.Unary):
            if node.op == "not":
                return not self.evaluate(node.operand)
        if isinstance(node, ast.Binary):
            if node.op == "or":
                return bool(self.evaluate(node.left)) or bool(self.evaluate(node.right))
            left, right = self.evaluate(node.left), self.evaluate(node.right)
            if node.op == "+":
                return left + right
            if node.op == "-":
                return left - right
            if node.op == "*":
                return left * right
            if node.op == "=":
                return left == right
            if node.op == ">":
                return left > right
        raise ExecutionError("unsupported expression", node.span)

    def execute(self, node: ast.Statement):
        if isinstance(node, ast.Block):
            for statement in node.statements:
                self.execute(statement)
            return
        if isinstance(node, ast.While):
            while True:
                self._tick(node)
                self._emit("BeforeStatement", node)
                result = bool(self.evaluate(node.condition))
                self._emit("ConditionEvaluated", node, value=result)
                self._emit("AfterStatement", node)
                if not result:
                    return
                self.execute(node.body)
        self._tick(node)
        self._emit("BeforeStatement", node)
        if isinstance(node, ast.Assign):
            value = self.evaluate(node.value)
            if type(value) is not int:
                raise ExecutionError("assignment requires an integer", node.span)
            old_value = self.state.get(node.name)
            self.state[node.name] = value
            self._emit("VariableChanged", node, variable=node.name,
                       old_value=old_value, new_value=value)
        elif isinstance(node, ast.Skip):
            pass
        elif isinstance(node, ast.If):
            result = bool(self.evaluate(node.condition))
            self._emit("ConditionEvaluated", node, value=result)
            self.execute(node.then_branch if result else node.else_branch)
        else:
            raise ExecutionError("unsupported statement", node.span)
        self._emit("AfterStatement", node)

    def run(self, node: ast.Statement) -> ExecutionResult:
        try:
            self.execute(node)
        except ExecutionError as exc:
            self._emit("ExecutionFinished", node, status="error", error=str(exc))
            raise
        self._emit("ExecutionFinished", node, status="success")
        return ExecutionResult(dict(self.state), self.steps)

def run(source: str, state: Mapping[str, int] | None = None, max_steps: int = 10000) -> ExecutionResult:
    from .parser import parse
    return Interpreter(state, max_steps).run(parse(source))
