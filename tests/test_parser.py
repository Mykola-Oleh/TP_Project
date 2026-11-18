import pytest
from sipl import parse, ParseError
from sipl.ast import Assign, Block, While, Binary, If

POSITIVE = [
    "begin skip end", "begin X := 1 end", "begin X := -12 end",
    "begin X := 1 + 2 * 3 end", "begin X := (1 + 2) * 3 end",
    "begin X := 5 - 2 - 1 end", "begin X := 1; Y := X + 2 end",
    "begin if X > 0 then skip else X := 0 end",
    "begin while X > 0 do X := X - 1 end",
    "begin begin skip end end",
    "begin if ¬(X = 0) then skip else skip end",
    "begin if X = 1 ∨ Y > 0 then skip else skip end",
    "begin while ¬(M = N) do if M > N then M := M - N else N := N - M end",
    "begin X := 1; while X > 0 do begin X := X - 1 end end",
]
NEGATIVE = [
    "", "skip", "X := 2", "begin end", "begin X = 2 end",
    "begin X := 1; end", "begin X := 1", "begin if X > 0 then skip end",
    "begin while X > 0 skip end", "begin X : 1 end",
    "begin X := 1 / 2 end", "begin X := 1 < 2 end",
    "begin X := 1 + * 3 end", "begin if X > 0 and Y > 0 then skip else skip end",
    "begin if X > 0 then skip else skip", "begin X := 2; ; Y := 3 end",
]
@pytest.mark.parametrize("source", POSITIVE)
def test_valid(source):
    assert isinstance(parse(source), Block)

@pytest.mark.parametrize("source", NEGATIVE)
def test_invalid(source):
    with pytest.raises(ParseError):
        parse(source)

def test_ast_types_and_spans():
    tree = parse("begin\n X := 1 + 2\nend")
    assert isinstance(tree, Block)
    assert isinstance(tree.statements[0], Assign)
    assert isinstance(tree.statements[0].value, Binary)
    assert tree.statements[0].span.line == 2

def test_while():
    tree = parse("begin while X > 0 do skip end")
    assert isinstance(tree.statements[0], While)

def test_conditional():
    tree = parse("begin if X > 0 then skip else skip end")
    assert isinstance(tree.statements[0], If)
