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
            print("Trying rule:", rule)
            offset = n
            nodes = []
            for sym in rule.syms:
                try:
                    offset, node = parse(g, sym, s, offset)
                    nodes.append(node)
                except ParseError as e:
                    print("Backtracking on", sym)
                    err = e # TODO: If we record all of these we can get nicer error messages (expected x | y)
                    break
            else: # success, found a rule with no backtracking
                print("Rule", rule, "succeeded")
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

ast = mp.parse("""
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
""")

print("Tokens:")
for tok in mp.toks.toks:
    print(tok)

for node in ast:
    print(" ", node)

print("")
print("==============")
print("")

grammar = mkgrammar(ast)
input_str = r"""S: '(' S '.' S ')' -> { (s[1], s[3]) }
 | atom -> { s[0] };

atom: /[A-Z]+/ -> { s[0] };
"""
print("PARSE:", parseall(grammar, grammar["S"], input_str, 0))
