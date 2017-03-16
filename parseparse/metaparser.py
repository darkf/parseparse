import re

scanner = re.Scanner([
    (r"[a-zA-Z_]\w*", lambda _,t: ("IDENT", t)),
    (r":", lambda _,t: ("COLON",)),
    (r"\|", lambda _,t: ("OR",)),
    (r"/([^/])+/", lambda _,t: ("REGEX", t[1:-1])),
    (r"'([^']*)'", lambda _,t: ("STR", t[1:-1])),
    (r";", lambda _,t: ("SEMI",)),
    (r"\s+", None),
    ])

def tokenize(s):
    tokens, remainder = scanner.scan(s)
    if remainder != "":
        print("Remainder:", remainder)
        raise Exception()
    return tokens

class Tokstream:
    def __init__(self, tokens):
        self.toks = list(tokens)
        self.n = 0

    def peek(self):
        if self.n >= len(self.toks): return None
        return self.toks[self.n]

    def consume(self):
        if self.n >= len(self.toks): return None
        t = self.toks[self.n]
        self.n += 1
        return t

    def nonempty(self):
        return self.peek() is not None

# ast
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

toks = None

# parse

def expect(t):
    c = toks.consume()
    assert c[0] == t, "expected token %s, got token %s" % (t, c[0])
    return c

def parse_rule():
    while True:
        t = toks.peek()
        if t[0] == "SEMI": break
        elif t[0] == "OR": return
        t = toks.consume()

        if t[0] == "STR": yield Lit(t[1]) #("lit", t[1])
        elif t[0] == "IDENT": yield Nonterminal(t[1]) #("nt", t[1])
        elif t[0] == "REGEX": yield Regex(t[1])
        else: raise Exception(t)

    toks.consume() # consume SEMI

def parse_prod():
    rules = []

    nt = expect("IDENT")
    expect("COLON")
    
    rules.append(Rule(list(parse_rule()), None))

    while toks.nonempty() and toks.peek()[0] == "OR":
        toks.consume()
        rules.append(Rule(list(parse_rule()), None))

    return Prod(nt[1], rules)

def parse():
    while toks.peek():
        yield parse_prod()

