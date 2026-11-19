import json
import shutil
import pytest
from sipl.visualize import parse_tree, tree_dict, to_json, to_text, to_dot, to_svg

def test_concrete_tree_and_locations():
    tree = parse_tree("begin X := 3 end")
    obj = tree_dict(tree)
    assert obj["name"] == "program"
    assert obj["span"]["line"] == 1
    assert "assignment" in to_text(tree)
    assert '"span"' in to_json(tree)
    assert json.loads(to_json(tree))["name"] == "program"

def test_dot():
    dot = to_dot(parse_tree("begin skip end"))
    assert "digraph SIPL" in dot
    assert "->" in dot
    assert "1:1" in dot

@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz not installed")
def test_svg():
    assert "<svg" in to_svg(parse_tree("begin skip end"))


def test_derivation_has_numbered_terminals():
    from sipl.visualize import derivation_tree, to_derivation_dot
    tree = parse_tree('begin X := 2 end')
    root = derivation_tree(tree)
    assert root.label == '<program>'
    dot = to_derivation_dot(tree)
    assert 'COLOR="red"' in dot
    assert '&lt;statement&gt;' in dot
    assert 'footer' in dot


def test_derivation_svg():
    from sipl.visualize import to_derivation_svg
    if shutil.which('dot') is None:
        pytest.skip('Graphviz not installed')
    svg = to_derivation_svg(parse_tree('begin skip end'))
    assert '<svg' in svg
    assert '#df1717' in svg


def test_english_derivation_svg_layout():
    from sipl.visualize import to_derivation_svg
    svg = to_derivation_svg(parse_tree("begin X := 2 end"), "begin\n X := 2\nend")
    assert "&lt;program&gt;" in svg
    assert "Terminal sequence" in svg
    assert "SIPL source" in svg
    assert 'marker-end="url(#arrow)"' in svg
