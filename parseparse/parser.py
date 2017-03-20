import metaparser as mp
import re

def mkgrammar(ast):
    symtab = {}

    for prod in ast:
        symtab[prod.nt] = prod

    return symtab

# backtracking recursive descent parser

def is_(x,y): return isinstance(x,y)

class ParseError(Exception): pass

def expected(g, p):
    # Given a grammar node, return an English description of what should be expected
    if is_(p, mp.Prod): return " or ".join([expected(g, rule) for rule in p.rules])
    if is_(p, mp.Rule): return expected(g, p.syms[0])
    elif is_(p, mp.Lit): return repr(p.v)
    elif is_(p, mp.Nonterminal): return expected(g, g[p.n])
    elif is_(p, mp.Regex): return "/%s/" % p.r
    else: raise Exception()

def parse(g, p, s, n):
    if is_(p, mp.Prod):
        err = Exception("Parse error")
        for rule in p.rules:
            # print("Trying rule:", rule)
            offset = n
            nodes = []
            for sym in rule.syms:
                try:
                    offset, node = parse(g, sym, s, offset)
                    nodes.append(node)
                except ParseError as e:
                    # print("Backtracking on", sym)
                    err = e # TODO: If we record all of these we can get nicer error messages (expected x | y)
                    break
            else: # success, found a rule with no backtracking
                # print("Rule", rule, "succeeded")
                if rule.tf: nodes = rule.tf(nodes)
                return offset, nodes
        raise ParseError("Expected %s" % expected(g, p)) # raise err
    elif is_(p, mp.Lit):
        if len(s) - n < len(p.v):
            raise ParseError("Parse error")
        r = s[n:n + len(p.v)]
        if r != p.v:
            raise ParseError("Parse error: expected '%s', got '%s'" % (p.v, r))
        return n + len(p.v), r
    elif is_(p, mp.Regex):
        m = re.match(p.r, s[n:])
        if m is None: raise ParseError("Parse error: /%s/ failed to match '%s[...]'" % (p.r, s[n:n+16]))
        return n + len(m.group(0)), m.group(0)
    elif is_(p, mp.Nonterminal):
        return parse(g, g[p.n], s, n)
    else: raise Exception("Unhandled parse node: " + str(p))

def parseall(g, p, s, n):
    (n, r) = parse(g, p, s, n)
    if n != len(s):
        raise ParseError("Didn't match entire string")
    return r

# test

def parse_tf(tf_str):
    return tf_str.lstrip("->").strip().lstrip("{").rstrip("}")

nt = mp.Nonterminal
prod = mp.Prod
rule = mp.Rule
lit = mp.Lit
regex = mp.Regex

def parse_tf(tf):
    code = tf.lstrip("->").strip().lstrip("{").rstrip('}')
    return lambda s: eval(code, None, {'s':s})

bootstrap_grammar = mkgrammar([
    # S: prods -> { s[0] };
    prod("S", [ rule([ nt("prods") ], lambda s: s[0]) ]),

    # prods: prod ws prods -> { [s[0]] + s[2] }
    #      | prod -> { [s[0]] };
    prod("prods", [
        rule([ nt("prod"), nt("ws"), nt("prods") ], lambda s: [s[0]] + s[2]),
        rule([ nt("prod") ], lambda s: [s[0]])
    ]),

    # prod: ident ':' ws rules ws ';' ws -> { Prod(s[0], s[3]) };
    prod("prod", [
        rule([ nt("ident"), lit(":"), nt("ws"), nt("rules"), nt("ws"), lit(";"), nt("ws") ], lambda s: prod(s[0], s[3]))
    ]),

    # rules: rule ws '|' ws rules -> { [s[0]] + s[4] }
    #      | rule -> { [s[0]] };
    prod("rules", [
        rule([ nt("rule"), nt("ws"), lit("|"), nt("ws"), nt("rules") ], lambda s: [s[0]] + s[4]),
        rule([ nt("rule") ], lambda s: [s[0]])
    ]),

    # rule: syms ws '-> {' /[^}]+/ '}' -> { Rule(s[0], s[3].lstrip("->").strip().lstrip("{").rstrip(chr(125))) };
    #     | syms -> { Rule(s[0], None) };
    prod("rule", [
        rule([ nt("syms"), nt("ws"), lit("-> {"), regex(r"[^}]+"), lit("}") ], lambda s: rule(s[0], parse_tf(s[3]))),
        rule([ nt("syms") ], lambda s: rule(s[0], None))
    ]),

    # syms: sym ws syms -> { [s[0]] + s[2] }
    #     | sym -> { [s[0]] }
    prod("syms", [
        rule([ nt("sym"), nt("ws"), nt("syms") ], lambda s: [s[0]] + s[2]),
        rule([ nt("sym") ], lambda s: [s[0]])
    ]),

    # sym: ident -> { Nonterminal(s[0]) }
    #     | /\\u002f[^\\u002f]+\\u002f/ -> { Regex(s[0][1:-1]) }
    #     | /'[^']+'/ -> { Lit(s[0][1:-1]) };
    prod("sym", [
        rule([ nt("ident") ], lambda s: nt(s[0])),
        rule([ regex(r"\u002f[^\u002f]+\u002f") ], lambda s: regex(s[0][1:-1])),
        rule([ regex(r"'[^']+'") ], lambda s: lit(s[0][1:-1]))
    ]),

    # ident: /[a-zA-Z_]+/ -> { s[0] };
    # ws: /\s*/ -> { None };
    prod("ident", [ rule([ regex(r"[a-zA-Z_]+") ], lambda s: s[0]) ]),
    prod("ws", [ rule([ regex(r"\s*") ], lambda s: None) ])
])

# meta grammar
"""
S: prods;

prods: prod ws prods -> { [s[0]] + s[2] }
     | prod -> { [s[0]] };
prod: ident ':' ws rules ws ';' ws -> { Prod(s[0], s[3]) };
rules: rule ws '|' ws rules -> { [s[0]] + s[4] }
     | rule -> { [s[0]] };

rule: syms ws '-> {' /[^}]+/ '}' -> { Rule(s[0], s[3].lstrip("->").strip().lstrip("{").rstrip(chr(125))) };
    | syms -> { Rule(s[0], None) };

syms: sym ws syms -> { [s[0]] + s[2] }
    | sym -> { [s[0]] }
sym: ident -> { Nonterminal(s[0]) }
    | /\\u002f[^\\u002f]+\\u002f/ -> { Regex(s[0][1:-1]) }
    | /'[^']+'/ -> { Lit(s[0][1:-1]) };

ident: /[a-zA-Z_]+/ -> { s[0] };
ws: /\s*/ -> { None };
"""

def grammar(grammar_def):
    g = parseall(bootstrap_grammar, bootstrap_grammar["S"], grammar_def, 0)
    return mkgrammar(g)

# build a grammar
gram = grammar("""S: '(' S '.' S ')' -> { (s[1], s[3]) }
 | atom -> { s[0] };
atom: /[A-Z]+/ -> { s[0] };
""")

input_str = "(A.(B.(C.NIL)))"
print("PARSE:", parseall(gram, gram["S"], input_str, 0))
