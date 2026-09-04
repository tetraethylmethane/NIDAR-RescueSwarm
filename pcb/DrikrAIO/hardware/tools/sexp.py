"""Minimal KiCad s-expression reader for read-only inspection."""
import re

TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+')


def parse(text):
    tok = TOKEN.findall(text)

    def build(i):
        out = []
        while i < len(tok):
            t = tok[i]
            if t == '(':
                sub, i = build(i + 1)
                out.append(sub)
            elif t == ')':
                return out, i + 1
            else:
                out.append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
                i += 1
        return out, i

    res, _ = build(0)
    return res[0] if len(res) == 1 else res


def findall(node, name):
    if isinstance(node, list):
        if node and node[0] == name:
            yield node
        for c in node:
            if isinstance(c, list):
                yield from findall(c, name)


def props(sym):
    return {p[1]: (p[2] if len(p) > 2 else "")
            for p in findall(sym, "property") if len(p) > 1}
