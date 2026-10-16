"""Convert a Panorama layout XML file into the text-KV3 form of the engine's compiled
layout block ("LaCo"), mirroring the structure ValveResourceFormat prints for vxml_c files.

Node shapes (as seen in Deadlock's compiled layouts):
  ROOT / STYLES / SCRIPTS / SNIPPETS / PANEL(name) / SNIPPET(name)  -> container nodes
  INCLUDE -> child REFERENCE_COMPILED(name=path without s2r://)
  PANEL_ATTRIBUTE(name) -> child PANEL_ATTRIBUTE_VALUE(name=value)
  SCRIPT_BODY(name=code)
A node with one sub-node uses `child = {...}`, with several `vecChildren = [...]`.
"""
import re
import xml.etree.ElementTree as ET

KV3_HEADER = ('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} '
              'format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->')


def kv_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


class Node:
    def __init__(self, etype, name=None, line=None):
        self.etype, self.name, self.line, self.children = etype, name, line, []


def convert_element(el, parser_lines) -> Node:
    tag = el.tag
    line = parser_lines.get(id(el))
    if tag == "root":
        n = Node("ROOT")
    elif tag == "styles":
        n = Node("STYLES", line=line)
    elif tag == "scripts":
        n = Node("SCRIPTS", line=line)
    elif tag == "snippets":
        n = Node("SNIPPETS", line=line)
    elif tag == "snippet":
        n = Node("SNIPPET", el.get("name"), line)
    elif tag == "include":
        n = Node("INCLUDE", line=line)
        src = el.get("src", "")
        if src.startswith("s2r://"):
            n.children.append(Node("REFERENCE_COMPILED", src[len("s2r://"):]))
        elif src.startswith("file://"):
            n.children.append(Node("REFERENCE_PASSTHROUGH", src[len("file://"):]))
        else:
            n.children.append(Node("REFERENCE_COMPILED", src))
        return n
    elif tag == "script":
        return Node("SCRIPT_BODY", el.text or "", line)
    else:
        n = Node("PANEL", tag, line)
        for k, v in el.attrib.items():
            a = Node("PANEL_ATTRIBUTE", k)
            a.children.append(Node("PANEL_ATTRIBUTE_VALUE", v))
            n.children.append(a)
    for ch in el:
        n.children.append(convert_element(ch, parser_lines))
    return n


def emit(n: Node, indent: int) -> str:
    t = "\t" * indent
    out = [f"{t}{{", f"{t}\teType = {kv_str(n.etype)}"]
    if n.name is not None:
        out.append(f"{t}\tname = {kv_str(n.name)}")
    if len(n.children) == 1:
        out.append(f"{t}\tchild = ")
        out.append(emit(n.children[0], indent + 1))
    elif len(n.children) > 1:
        out.append(f"{t}\tvecChildren = ")
        out.append(f"{t}\t[")
        for c in n.children:
            out.append(emit(c, indent + 2) + ",")
        out.append(f"{t}\t]")
    if n.line is not None:
        out.append(f"{t}\tsourceLineColumn = [ {n.line[0]}, {n.line[1]} ]")
    elif n.etype == "ROOT":
        out.append(f"{t}\tsourceLineColumn = [  ]")
    out.append(f"{t}}}")
    return "\n".join(out)


def element_lines(xml_text: str, root_el) -> dict:
    """Map id(element) -> (line, column) by matching start tags in document order."""
    tags = [m for m in re.finditer(r"<([A-Za-z_][\w.-]*)", xml_text)]
    lines = {}
    pos = 0
    for el, m in zip(root_el.iter(), tags):
        line = xml_text.count("\n", 0, m.start()) + 1
        col = m.start() - (xml_text.rfind("\n", 0, m.start()) + 1) + 1
        lines[id(el)] = (line, col)
    return lines


def xml_to_laco(xml_text: str) -> str:
    root_el = ET.fromstring(xml_text)
    root = convert_element(root_el, element_lines(xml_text, root_el))
    body = emit(root, 2)
    return f"{KV3_HEADER}\n{{\n\tm_AST = \n\t{{\n\t\tm_pRoot = \n{body}\n\t}}\n}}\n"


if __name__ == "__main__":
    import sys
    print(xml_to_laco(open(sys.argv[1], encoding="utf-8").read()))
