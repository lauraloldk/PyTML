import re

# Test at label parser matcher
from libs.label import get_line_parsers

line = '<lbl1_text="<counter_value>">'
print(f"Testing line: {line}")

for pattern, func in get_line_parsers():
    m = re.match(pattern, line)
    if m:
        print(f"  MATCH with pattern: {pattern}")
        print(f"  Groups: {m.groups()}")
    else:
        print(f"  no match: {pattern}")

# Test hele compileren
print("\n--- Testing Compiler ---")
from Compiler import PyTMLCompiler

code = '''<var name="counter" value="5">
<lbl1_text="<counter_value>">
'''

compiler = PyTMLCompiler()
ast = compiler.parse(code)

print("\nAST children:")
for child in ast.children:
    print(f"  {child.tag_name}: {child.attributes}")

