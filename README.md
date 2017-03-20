**Parseparse** is a simple tiny backtracking recursive descent parser written in Python.

It is mainly for educational purposes, although I may use it in small personal projects.

It includes a bootstrapped metagrammar so that it can parse a BNF grammar definition.

Parse trees can be transformed with Python expressions on the fly (and is thus suitable for constructing abstract syntax trees, or even interpreting expressions inline.)

### Example

S-expression parsing:

    # build a grammar
    gram = grammar("""S: '(' S '.' S ')' -> { (s[1], s[3]) }
     | atom -> { s[0] };
    atom: /[A-Z]+/ -> { s[0] };
    """)

    # test parse
    input_str = "(A.(B.(C.NIL)))"
    print("PARSE:", parseall(gram, gram["S"], input_str, 0, True))

    # output:
    # PARSE: ('A', ('B', ('C', 'NIL')))

Please see the source code for details on what `parseall` does.
In short, you give it a grammar (in this case built from a definition), a starting production (in this case the 'S' production), an input string, an offset (0 being the start), and if the parser should be verbose (for debugging).

### Future Work

It should be trivial to memoize `parse`, which may lend itself to being a [Packrat](http://bford.info/packrat) parser, for a good optimization.
