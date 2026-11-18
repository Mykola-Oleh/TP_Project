from pathlib import Path
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedInput
from . import ast

class ParseError(ValueError):
    def __init__(self, line: int, column: int, detail: str):
        self.line, self.column = line, column
        super().__init__(f"Syntax error at {line}:{column}: {detail}")

def span(meta):
    return ast.SourceSpan(meta.line, meta.column, meta.end_line, meta.end_column)

@v_args(meta=True)
class ASTBuilder(Transformer):
    def number(self, meta, items):
        return ast.Number(int(items[0]), span(meta))
    def variable(self, meta, items):
        return ast.Variable(str(items[0]), span(meta))
    def grouped_expr(self, meta, items):
        return items[0]
    def grouped_condition(self, meta, items):
        return items[0]
    def compare(self, meta, items):
        return ast.Binary(str(items[1]), items[0], items[2], span(meta))
    def not_expr(self, meta, items):
        return ast.Unary("not", items[0], span(meta))
    def or_expr(self, meta, items):
        return self._fold(items, span(meta), "or")
    def and_expr(self, meta, items):
        return self._fold(items, span(meta), "and")
    def sum_expr(self, meta, items):
        return self._fold(items, span(meta))
    def product_expr(self, meta, items):
        return self._fold(items, span(meta), "*")
    @staticmethod
    def _fold(items, location, default=None):
        node = items[0]
        if default:
            for item in items[1:]:
                node = ast.Binary(default, node, item, location)
        else:
            for i in range(1, len(items), 2):
                node = ast.Binary(str(items[i]), node, items[i+1], location)
        return node
    def program(self, meta, items):
        return ast.Block((items[0],), span(meta))
    def sequence(self, meta, items):
        if len(items) == 1:
            return items[0]
        return ast.Block(tuple(items), span(meta))
    def assignment(self, meta, items):
        return ast.Assign(str(items[0]), items[1], span(meta))
    def skip(self, meta, items):
        return ast.Skip(span(meta))
    def conditional(self, meta, items):
        return ast.If(items[0], items[1], items[2], span(meta))
    def loop(self, meta, items):
        return ast.While(items[0], items[1], span(meta))
    def block(self, meta, items):
        return ast.Block(tuple(x for x in items if x is not None), span(meta))

_grammar = Path(__file__).with_name("grammar.lark").read_text(encoding="utf-8")
_parser = Lark(_grammar, parser="lalr", propagate_positions=True, maybe_placeholders=False)

def parse(source: str) -> ast.Statement:
    try:
        return ASTBuilder().transform(_parser.parse(source))
    except UnexpectedInput as exc:
        raise ParseError(exc.line, exc.column, "unexpected token or incomplete program") from exc
