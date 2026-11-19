import base64
import dataclasses
import json
from html import escape
from xml.etree import ElementTree as ET

from . import ast as nodes
from .visualize import parse_tree, to_derivation_svg


def ast_dict(node):
    if not dataclasses.is_dataclass(node):
        raise TypeError('Expected an AST dataclass node')
    result = {'type': type(node).__name__, 'span': dataclasses.asdict(node.span)}
    for field in dataclasses.fields(node):
        if field.name == 'span':
            continue
        value = getattr(node, field.name)
        if dataclasses.is_dataclass(value):
            result[field.name] = ast_dict(value)
        elif isinstance(value, tuple):
            result[field.name] = [ast_dict(x) for x in value]
        else:
            result[field.name] = value
    return result


def _children(node):
    for field in dataclasses.fields(node):
        if field.name == 'span':
            continue
        value = getattr(node, field.name)
        if dataclasses.is_dataclass(value):
            yield value
        elif isinstance(value, tuple):
            yield from (x for x in value if dataclasses.is_dataclass(x))


def _label(node):
    if isinstance(node, nodes.Assign):
        return f'Assign: {node.name}'
    if isinstance(node, nodes.Variable):
        return f'Variable: {node.name}'
    if isinstance(node, nodes.Number):
        return f'Number: {node.value}'
    if isinstance(node, (nodes.Binary, nodes.Unary)):
        return f'{type(node).__name__}: {node.op}'
    return type(node).__name__


def ast_text(root):
    lines = []
    def visit(node, depth):
        lines.append('  ' * depth + _label(node))
        for child in _children(node):
            visit(child, depth + 1)
    visit(root, 0)
    return '\n'.join(lines)


def ast_dot(root):
    lines = ['digraph SIPL_AST {', '  graph [rankdir=TB, ordering=out];',
             '  node [shape=box, style=rounded, fontname="Arial"];']
    counter = 0
    def visit(node):
        nonlocal counter
        current = counter
        counter += 1
        label = _label(node).replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'  n{current} [label="{label}"];')
        for child in _children(node):
            child_id = visit(child)
            lines.append(f'  n{current} -> n{child_id};')
        return current
    visit(root)
    lines.append('}')
    return '\n'.join(lines) + '\n'


def ast_svg(root):
    positions = {}
    cursor = 0
    max_depth = 0
    def layout(node, depth):
        nonlocal cursor, max_depth
        max_depth = max(max_depth, depth)
        children = list(_children(node))
        if children:
            xs = [layout(c, depth + 1) for c in children]
            x = (xs[0] + xs[-1]) / 2
        else:
            x = cursor
            cursor += 1
        positions[id(node)] = (x, depth)
        return x
    layout(root, 0)
    spacing = 160
    width = max(420, (cursor - 1) * spacing + 200)
    height = (max_depth + 1) * 105 + 95
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="Arial, sans-serif">']
    def xy(node):
        x, depth = positions[id(node)]
        return 100 + x * spacing, 65 + depth * 105
    def edges(node):
        x, y = xy(node)
        for child in _children(node):
            cx, cy = xy(child)
            parts.append(f'<line x1="{x}" y1="{y+18}" x2="{cx}" y2="{cy-25}" stroke="#475569" stroke-width="1.5"/>')
            edges(child)
    def labels(node):
        x, y = xy(node)
        label = escape(_label(node))
        box_width = max(112, len(_label(node)) * 8 + 22)
        parts.append(f'<rect x="{x-box_width/2}" y="{y-20}" width="{box_width}" height="40" rx="7" fill="#eff6ff" stroke="#2563eb"/>')
        parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="14" fill="#0f172a">{label}</text>')
        for child in _children(node):
            labels(child)
    edges(root)
    labels(root)
    parts.append('</g></svg>')
    return '\n'.join(parts)


def compare_svg(source, root):
    concrete = to_derivation_svg(parse_tree(source), source)
    abstract = ast_svg(root)
    def dimensions(svg):
        element = ET.fromstring(svg)
        return int(float(element.attrib['width'])), int(float(element.attrib['height']))
    lw, lh = dimensions(concrete)
    rw, rh = dimensions(abstract)
    left_w = 1050
    right_w = 850
    left_h = max(220, round(lh * left_w / lw))
    right_h = max(220, round(rh * right_w / rw))
    height = max(left_h, right_h) + 115
    width = left_w + right_w + 72
    def uri(svg):
        return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')).decode('ascii')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
            f'<rect width="100%" height="100%" fill="white"/>\n'
            f'<text x="24" y="38" font-family="Arial" font-size="23" font-weight="bold">Parse Tree</text>\n'
            f'<text x="{left_w+48}" y="38" font-family="Arial" font-size="23" font-weight="bold">Abstract Syntax Tree (AST)</text>\n'
            f'<image x="12" y="60" width="{left_w}" height="{left_h}" href="{uri(concrete)}"/>\n'
            f'<line x1="{left_w+36}" y1="20" x2="{left_w+36}" y2="{height-20}" stroke="#cbd5e1"/>\n'
            f'<image x="{left_w+48}" y="60" width="{right_w}" height="{right_h}" href="{uri(abstract)}"/>\n'
            '</svg>\n')
