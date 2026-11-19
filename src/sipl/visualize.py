import json
import shutil
import subprocess
from pathlib import Path
from lark import Lark, Tree, Token
from lark.exceptions import UnexpectedInput
from .parser import ParseError
from dataclasses import dataclass
from html import escape as html_escape

_GRAMMAR = Path(__file__).with_name("grammar.lark")
_PARSER = Lark(_GRAMMAR.read_text(encoding="utf-8"), parser="lalr", propagate_positions=True, keep_all_tokens=True)

def parse_tree(source: str) -> Tree:
    try:
        return _PARSER.parse(source)
    except UnexpectedInput as exc:
        raise ParseError(exc.line, exc.column, "unexpected token or incomplete program") from exc

def _location(node):
    if isinstance(node, Token):
        return {"line": node.line, "column": node.column, "end_line": node.end_line, "end_column": node.end_column}
    m = node.meta
    return {"line": m.line, "column": m.column, "end_line": m.end_line, "end_column": m.end_column}

def tree_dict(node):
    if isinstance(node, Token):
        return {"kind": "token", "type": node.type, "value": str(node), "span": _location(node)}
    return {"kind": "rule", "name": str(node.data), "span": _location(node),
            "children": [tree_dict(child) for child in node.children]}

def to_json(tree):
    return json.dumps(tree_dict(tree), ensure_ascii=False, indent=2)

def to_text(tree):
    lines = []
    def visit(node, depth):
        pos = _location(node)
        label = (f"{node.type}: {str(node)!r}" if isinstance(node, Token) else str(node.data))
        lines.append(f"{'  '*depth}{label} [{pos['line']}:{pos['column']}-{pos['end_line']}:{pos['end_column']}]")
        if isinstance(node, Tree):
            for child in node.children:
                visit(child, depth + 1)
    visit(tree, 0)
    return "\n".join(lines)

def to_dot(tree):
    lines = ['digraph SIPL {', '  graph [rankdir=TB];', '  node [shape=box, fontname="Arial"];']
    count = 0
    def esc(value):
        return str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    def visit(node, parent=None):
        nonlocal count
        ident = f"n{count}"
        count += 1
        loc = _location(node)
        name = (f"{node.type}: {node}" if isinstance(node, Token) else str(node.data))
        label = f"{name}\n{loc['line']}:{loc['column']}-{loc['end_line']}:{loc['end_column']}"
        lines.append(f'  {ident} [label="{esc(label)}"];')
        if parent is not None:
            lines.append(f'  {parent} -> {ident};')
        if isinstance(node, Tree):
            for child in node.children:
                visit(child, ident)
    visit(tree)
    lines.append('}')
    return "\n".join(lines) + "\n"

def to_svg(tree):
    if not shutil.which("dot"):
        raise RuntimeError("Graphviz 'dot' is required for SVG: https://graphviz.org/download/")
    result = subprocess.run(["dot", "-Tsvg"], input=to_dot(tree), text=True,
                            capture_output=True, encoding="utf-8", check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Graphviz failed")
    return result.stdout

@dataclass
class DerivationNode:
    label: str
    children: tuple = ()
    terminal: bool = False
    number: int | None = None


def derivation_tree(tree: Tree) -> DerivationNode:
    def term(value):
        return DerivationNode(str(value), terminal=True)

    def nt(label, *children):
        return DerivationNode(f"<{label}>", tuple(children))

    def convert(node):
        if isinstance(node, Token):
            return term(node)
        rule = str(node.data)
        ch = list(node.children)
        if rule == 'program':
            return nt('program', *(convert(c) for c in ch))
        if rule == 'sequence':
            statements = [convert(c) for c in ch if not (isinstance(c, Token) and str(c) == ';')]
            if not statements:
                raise ValueError('Empty statement sequence')
            current = statements[0]
            for nxt in statements[1:]:
                current = nt('statement', current, term(';'), nxt)
            return current
        if rule in ('assignment', 'skip', 'conditional', 'loop', 'block'):
            if rule == 'assignment':
                return nt('statement', nt('variable', convert(ch[0])), convert(ch[1]), nt('expression', convert(ch[2])))
            return nt('statement', *(convert(c) for c in ch))
        if rule == 'variable':
            return nt('variable', *(convert(c) for c in ch))
        if rule == 'number':
            return nt('number', *(convert(c) for c in ch))
        if rule in ('sum_expr', 'product_expr', 'grouped_expr'):
            parts = [convert(c) for c in ch]
            if rule == 'grouped_expr':
                return nt('expression', *parts)
            if len(parts) == 1:
                return parts[0]
            current = parts[0]
            for i in range(1, len(parts), 2):
                current = nt('expression', nt('expression', current), parts[i], nt('expression', parts[i + 1]))
            return current
        if rule in ('or_expr', 'not_expr', 'compare', 'grouped_condition'):
            parts = [convert(c) for c in ch]
            if rule == 'or_expr' and len(parts) == 1:
                return parts[0]
            if rule == 'or_expr':
                current = parts[0]
                for i in range(1, len(parts), 2):
                    current = nt('condition', nt('condition', current), parts[i], nt('condition', parts[i + 1]))
                return current
            return nt('condition', *parts)
        return nt(rule, *(convert(c) for c in ch))

    result = convert(tree)
    counter = 0
    def number_leaves(node):
        nonlocal counter
        if node.terminal:
            counter += 1
            node.number = counter
        for child in node.children:
            number_leaves(child)
    number_leaves(result)
    return result


def to_derivation_dot(tree: Tree, source: str | None = None) -> str:
    root = derivation_tree(tree)
    lines = [
        'digraph SIPL_Derivation {',
        '  graph [rankdir=TB, bgcolor="white", pad="0.3", nodesep="0.24", ranksep="0.62", splines=line, ordering=out];',
        '  node [shape=plaintext, fontname="Arial", fontsize=13];',
        '  edge [arrowsize=0.55, penwidth=0.8, color="black"];',
    ]
    leaves = []
    next_id = 0
    def label(node):
        name = html_escape(node.label)
        if node.terminal:
            return f'<<FONT COLOR="red"><B>{node.number}</B></FONT>  {name}>'
        return f'<{name}>'
    def visit(node):
        nonlocal next_id
        ident = f'n{next_id}'
        next_id += 1
        lines.append(f'  {ident} [label={label(node)}];')
        if node.terminal:
            leaves.append(node)
        for child in node.children:
            child_id = visit(child)
            lines.append(f'  {ident} -> {child_id};')
        return ident
    visit(root)
    footer = ' '.join(f'<FONT COLOR="red"><B>{n.number}</B></FONT> {html_escape(n.label)}' for n in leaves)
    lines.append(f'  footer [label=<{footer}>, fontsize=12];')
    lines.append('  {rank=sink; footer;}')
    if source is not None:
        code = '<BR ALIGN="LEFT"/>'.join(html_escape(s) if s.strip() else ' ' for s in source.strip().splitlines())
        lines.append(f'  source [label=<<FONT POINT-SIZE="13">{code}</FONT>>, shape=plaintext];')
        lines.append('  {rank=source; source;}')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def to_derivation_svg(tree: Tree, source: str | None = None) -> str:
    from xml.sax.saxutils import escape
    import math

    root = derivation_tree(tree)
    leaves = []
    positions = {}
    max_depth = 0
    leaf_cursor = 0

    def layout(node, depth):
        nonlocal leaf_cursor, max_depth
        max_depth = max(max_depth, depth)
        if not node.children:
            x = float(leaf_cursor)
            leaf_cursor += 1
            leaves.append(node)
        else:
            xs = [layout(child, depth + 1) for child in node.children]
            x = (xs[0] + xs[-1]) / 2
        positions[id(node)] = (x, depth)
        return x

    layout(root, 0)
    leaf_spacing = 108
    margin = 65
    tree_width = max(680, (leaf_cursor - 1) * leaf_spacing + 2 * margin)
    level_spacing = 88
    tree_bottom = 70 + max_depth * level_spacing
    source_lines = source.strip('\n').splitlines() if source and source.strip() else []
    source_width = max(360, min(750, 90 + max((len(s) for s in source_lines), default=0) * 9)) if source_lines else 0
    gap = 70 if source_lines else 0
    panel_x = tree_width + gap
    width = tree_width + gap + source_width

    footer_items = []
    line_x = 32.0
    line_y = 0.0
    for leaf in leaves:
        item_width = max(48, len(leaf.label) * 9 + len(str(leaf.number)) * 10 + 22)
        if line_x + item_width > tree_width - 32 and line_x > 32:
            line_x = 32
            line_y += 30
        footer_items.append((leaf, line_x, line_y))
        line_x += item_width

    footer_top = tree_bottom + 90
    footer_height = max(100, line_y + 76)
    height = max(footer_top + footer_height, 100 + len(source_lines) * 26)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#111"/></marker></defs>',
        '<g font-family="Arial, Helvetica, sans-serif" fill="#111">',
    ]

    def coords(node):
        x, depth = positions[id(node)]
        return margin + x * leaf_spacing, 52 + depth * level_spacing

    def draw_edges(node):
        x, y = coords(node)
        for child in node.children:
            cx, cy = coords(child)
            parts.append(f'<line x1="{x:.1f}" y1="{y+12:.1f}" x2="{cx:.1f}" y2="{cy-17:.1f}" stroke="#111" stroke-width="1.1" marker-end="url(#arrow)"/>')
            draw_edges(child)

    def draw_labels(node):
        x, y = coords(node)
        if node.terminal:
            parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="15" text-anchor="middle"><tspan fill="#df1717" font-weight="bold">{node.number}</tspan><tspan dx="5">{escape(node.label)}</tspan></text>')
        else:
            parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="15" text-anchor="middle">{escape(node.label)}</text>')
        for child in node.children:
            draw_labels(child)

    draw_edges(root)
    draw_labels(root)

    parts.append(f'<line x1="24" y1="{footer_top-30:.1f}" x2="{tree_width-24:.1f}" y2="{footer_top-30:.1f}" stroke="#ddd"/>')
    parts.append(f'<text x="32" y="{footer_top-9:.1f}" font-size="15" font-weight="bold">Terminal sequence</text>')
    for leaf, x, offset in footer_items:
        y = footer_top + 20 + offset
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="14"><tspan fill="#df1717" font-weight="bold">{leaf.number}</tspan><tspan dx="5">{escape(leaf.label)}</tspan></text>')

    if source_lines:
        parts.append(f'<line x1="{panel_x-35:.1f}" y1="25" x2="{panel_x-35:.1f}" y2="{height-25:.1f}" stroke="#ddd"/>')
        parts.append(f'<text x="{panel_x:.1f}" y="48" font-size="18" font-weight="bold">SIPL source</text>')
        for i, line in enumerate(source_lines):
            parts.append(f'<text x="{panel_x:.1f}" y="{82+i*26:.1f}" xml:space="preserve" font-family="Consolas, monospace" font-size="16">{escape(line)}</text>')

    parts.append('</g></svg>')
    return '\n'.join(parts) + '\n'
