import re

# Grammar AST
def node(name, props):
    def set_props(self, *propvs):
        for prop, value in zip(props.split(), propvs):
            setattr(self, prop, value)
    return type(name, (Node,), {"__init__": set_props,
                                "__repr__": lambda self: "<%s: %s>" % (name, " ".join("%s=%r" % (k,v) for k,v in self.__dict__.items())),
                                "__eq__": lambda self, other: self.__class__.__name__ == other.__class__.__name__ and self.__dict__ == other.__dict__
                                })

class Node: pass
Lit = node('Lit', 'v')
Nonterminal = node('Nonterminal', 'n')
Regex = node('Regex', 'r')
Ident = node('Ident', 'n')
Rule = node('Rule', 'syms tf')
Prod = node('Prod', 'nt rules')

# Grammar -> dict of prod name: prod
def mkgrammar(ast):
    return {prod.nt: prod for prod in ast}

# Backtracking recursive descent parser

def is_(x,y): return isinstance(x,y)

class ParseError(Exception): pass

# Given a grammar node, return an English description of what should be expected
def expected(g, p):
    if is_(p, Prod): return " or ".join([expected(g, rule) for rule in p.rules])
    if is_(p, Rule): return expected(g, p.syms[0])
    elif is_(p, Lit): return repr(p.v)
    elif is_(p, Nonterminal): return expected(g, g[p.n])
    elif is_(p, Regex): return "/%s/" % p.r
    else: raise Exception()

# Core parser
# g = grammar, p = production, s = string (constant), n = string offset, v = verbose
def parse(g, p, s, n, v):
    if is_(p, Prod):
        err = Exception("Parse error")
        for rule in p.rules:
            if v: print("Trying rule:", rule)
            offset = n
            nodes = []
            for sym in rule.syms:
                try:
                    offset, node = parse(g, sym, s, offset, v)
                    nodes.append(node)
                except ParseError as e:
                    if v: print("Backtracking on", sym)
                    err = e # TODO: If we record all of these we can get nicer error messages (expected x | y)
                    break
            else: # success, found a rule with no backtracking
                if v: print("Rule", rule, "succeeded")
                if rule.tf: nodes = rule.tf(nodes)
                return offset, nodes
        raise ParseError("Expected %s" % expected(g, p)) # raise err
    elif is_(p, Lit):
        if len(s) - n < len(p.v):
            raise ParseError("Parse error")
        r = s[n:n + len(p.v)]
        if r != p.v:
            raise ParseError("Parse error: expected '%s', got '%s'" % (p.v, r))
        return n + len(p.v), r
    elif is_(p, Regex):
        m = re.match(p.r, s[n:])
        if m is None: raise ParseError("Parse error: /%s/ failed to match '%s[...]'" % (p.r, s[n:n+16]))
        return n + len(m.group(0)), m.group(0)
    elif is_(p, Nonterminal):
        return parse(g, g[p.n], s, n, v)
    else: raise Exception("Unhandled parse node: " + str(p))

# Parse entire string, erroring if it's not entirely matched
def parseall(g, p, s, n, v):
    (n, r) = parse(g, p, s, n, v)
    if n != len(s):
        raise ParseError("Didn't match entire string")
    return r

### Metagrammar

# Parse a transformation string
def parse_tf(tf):
    code = tf.lstrip("->").strip().lstrip("{").rstrip('}')
    return lambda s: eval(code, None, {'s':s})

nt = Nonterminal

bootstrap_grammar = mkgrammar([
    # S: prods -> { s[0] };
    Prod("S", [ Rule([ nt("prods") ], lambda s: s[0]) ]),

    # prods: prod ws prods -> { [s[0]] + s[2] }
    #      | prod -> { [s[0]] };
    Prod("prods", [
        Rule([ nt("prod"), nt("ws"), nt("prods") ], lambda s: [s[0]] + s[2]),
        Rule([ nt("prod") ], lambda s: [s[0]])
    ]),

    # prod: ident ':' ws rules ws ';' ws -> { Prod(s[0], s[3]) };
    Prod("prod", [
        Rule([ nt("ident"), Lit(":"), nt("ws"), nt("rules"), nt("ws"), Lit(";"), nt("ws") ], lambda s: Prod(s[0], s[3]))
    ]),

    # rules: rule ws '|' ws rules -> { [s[0]] + s[4] }
    #      | rule -> { [s[0]] };
    Prod("rules", [
        Rule([ nt("rule"), nt("ws"), Lit("|"), nt("ws"), nt("rules") ], lambda s: [s[0]] + s[4]),
        Rule([ nt("rule") ], lambda s: [s[0]])
    ]),

    # rule: syms ws '-> {' /[^}]+/ '}' -> { Rule(s[0], s[3].lstrip("->").strip().lstrip("{").rstrip(chr(125))) };
    #     | syms -> { Rule(s[0], None) };
    Prod("rule", [
        Rule([ nt("syms"), nt("ws"), Lit("-> {"), Regex(r"[^}]+"), Lit("}") ], lambda s: Rule(s[0], parse_tf(s[3]))),
        Rule([ nt("syms") ], lambda s: Rule(s[0], None))
    ]),

    # syms: sym ws syms -> { [s[0]] + s[2] }
    #     | sym -> { [s[0]] }
    Prod("syms", [
        Rule([ nt("sym"), nt("ws"), nt("syms") ], lambda s: [s[0]] + s[2]),
        Rule([ nt("sym") ], lambda s: [s[0]])
    ]),

    # sym: ident -> { Nonterminal(s[0]) }
    #     | /\\u002f[^\\u002f]+\\u002f/ -> { Regex(s[0][1:-1]) }
    #     | /'[^']+'/ -> { Lit(s[0][1:-1]) };
    Prod("sym", [
        Rule([ nt("ident") ], lambda s: nt(s[0])),
        Rule([ Regex(r"/[^/]+/") ], lambda s: Regex(s[0][1:-1])),
        Rule([ Regex(r"'[^']+'") ], lambda s: Lit(s[0][1:-1]))
    ]),

    # ident: /[a-zA-Z_]+/ -> { s[0] };
    # ws: /\s*/ -> { None };
    Prod("ident", [ Rule([ Regex(r"[a-zA-Z_]+") ], lambda s: s[0]) ]),
    Prod("ws", [ Rule([ Regex(r"\s*") ], lambda s: None) ])
])

# Make a grammar from a grammar definition string
def grammar(grammar_def):
    g = parseall(bootstrap_grammar, bootstrap_grammar["S"], grammar_def, 0, False)
    return mkgrammar(g)

# build a grammar
gram = grammar("""S: '(' S '.' S ')' -> { (s[1], s[3]) }
 | atom -> { s[0] };
atom: /[A-Z]+/ -> { s[0] };
""")

# test parse
input_str = "(A.(B.(C.NIL)))"
print("PARSE:", parseall(gram, gram["S"], input_str, 0, True))
