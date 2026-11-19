import json
from xml.etree import ElementTree
from sipl.parser import parse
from sipl.ast_visualize import ast_dict, ast_text, ast_dot, ast_svg, compare_svg

SOURCE = 'begin X := 2; Y := X + 3 end'

def test_ast_dict():
    obj = ast_dict(parse(SOURCE))
    assert obj['type'] == 'Block'
    assert len(obj['statements'][0]['statements']) == 2
    assert obj['statements'][0]['statements'][1]['value']['type'] == 'Binary'
    json.dumps(obj)

def test_ast_formats():
    tree = parse(SOURCE)
    assert 'Assign: X' in ast_text(tree)
    assert 'digraph SIPL_AST' in ast_dot(tree)
    assert 'Binary: +' in ast_svg(tree)
    ElementTree.fromstring(ast_svg(tree))

def test_comparison():
    svg = compare_svg(SOURCE, parse(SOURCE))
    ElementTree.fromstring(svg)
    assert 'Parse Tree' in svg and 'Abstract Syntax Tree' in svg
    assert svg.count('data:image/svg+xml;base64,') == 2
