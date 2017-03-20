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

# test


# toks = Tokstream(tokenize("""
# S: x | y;

# x: 'a' 'b' 'c';
# y: 'a' 'd' 'b';
# """))

mp.toks = mp.Tokstream(mp.tokenize("""
S: '(' S '.' S ')' -> { (s[1], s[3]) }
 | atom -> { s[0] };

atom: /[A-Z]+/ -> { s[0] };
"""))

print("Tokens:")
for tok in mp.toks.toks:
    print(tok)


ast = list(mp.parse())
for node in ast:
    print(" ", node)

print("")
print("==============")
print("")

def tf(n):
    print("N:", n)
    return (n[1], n[3])

grammar = mkgrammar(ast)
#grammar["S"].rules[0].tf = tf
#grammar["S"].rules[1].tf = lambda n: n[0]
#for rule in grammar["atom"].rules: rule.tf = lambda n: n[0]
print("PARSE:", parse(grammar, grammar["S"], "(A.(B.(ZF.NIL)))", 0))
