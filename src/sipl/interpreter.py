"""Execution of the core SIPL language over integer-valued states."""
from collections.abc import Mapping
from dataclasses import dataclass
from sipl import ast


class ExecutionError(RuntimeError):
    """Runtime error tied to a source location."""
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
    def __init__(self, state: Mapping[str, int] | None = None, max_steps: int = 10000):
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
                if not self.evaluate(node.condition):
                    return
                self.execute(node.body)
        self._tick(node)
        if isinstance(node, ast.Assign):
            value = self.evaluate(node.value)
            if type(value) is not int:
                raise ExecutionError("assignment requires an integer", node.span)
            self.state[node.name] = value
        elif isinstance(node, ast.Skip):
            return
        elif isinstance(node, ast.If):
            if self.evaluate(node.condition):
                self.execute(node.then_branch)
            else:
                self.execute(node.else_branch)
        else:
            raise ExecutionError("unsupported statement", node.span)

    def run(self, node: ast.Statement) -> ExecutionResult:
        self.execute(node)
        return ExecutionResult(dict(self.state), self.steps)


def run(source: str, state: Mapping[str, int] | None = None, max_steps: int = 10000) -> ExecutionResult:
    from .parser import parse
    return Interpreter(state, max_steps).run(parse(source))
