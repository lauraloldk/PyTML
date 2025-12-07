"""
PyTML Variable Module
Håndterer variabler med HTML-lignende tags
Inkluderer resolve_value() funktion til variabel-interpolation i alle libs
"""

import re


def resolve_value(value, context):
    """
    Resolver en værdi der kan indeholde variabel-referencer.
    
    Understøtter:
        <varname_value>  -> værdien af variablen 'varname' ELLER entry felt
        <name_random>    -> kalder random generator (f.eks. <rnd_random>)
        <name_float>     -> kalder random float generator
        $varname         -> værdien af variablen 'varname'  
        "literal"        -> literal string (uændret)
        123              -> tal (uændret)
    
    Args:
        value: Værdien der skal resolves (string, int, list, etc.)
        context: PyTML context dict med 'variables' key
    
    Returns:
        Den resolvede værdi
    """
    if value is None:
        return None
    
    # Hvis det er en liste, resolve hvert element
    if isinstance(value, list):
        return [resolve_value(v, context) for v in value]
    
    # Hvis det ikke er en string, returner som den er
    if not isinstance(value, str):
        return value
    
    variables = context.get('variables')
    entries = context.get('entries')
    randoms = context.get('randoms')
    
    result = value
    
    # Pattern 1: <name_suffix> syntax - handles value, random, float, etc.
    tag_pattern = r'<(\w+)_(\w+)>'
    
    def replace_tag(match):
        name = match.group(1)
        suffix = match.group(2)
        full_key = f"{name}_{suffix}"
        
        # First check if there's a callable in context with this exact key
        if full_key in context:
            ctx_value = context[full_key]
            if callable(ctx_value):
                return str(ctx_value())
            return str(ctx_value)
        
        # Check randoms for random/float methods
        if randoms and name in randoms:
            rng = randoms[name]
            if suffix == 'random' and hasattr(rng, 'random'):
                return str(rng.random())
            elif suffix == 'float' and hasattr(rng, 'random_float'):
                return str(rng.random_float())
        
        # If suffix is 'value', check entries and variables
        if suffix == 'value':
            # Check entries first
            if entries and entries.get(name):
                entry = entries.get(name)
                return str(entry.get_value())
            
            # Check variables
            if variables:
                var_value = variables.get_value(name)
                if var_value is not None:
                    return str(var_value)
        
        return match.group(0)
    
    result = re.sub(tag_pattern, replace_tag, result)
    
    # Pattern 2: $varname syntax
    dollar_pattern = r'\$(\w+)'
    
    def replace_dollar(match):
        var_name = match.group(1)
        if variables:
            var_value = variables.get_value(var_name)
            return str(var_value) if var_value is not None else match.group(0)
        return match.group(0)
    
    result = re.sub(dollar_pattern, replace_dollar, result)
    
    # Hvis hele strengen blev erstattet med et tal, konverter
    if result != value:
        try:
            if '.' in result:
                return float(result)
            return int(result)
        except ValueError:
            pass
    
    return result


def resolve_as_string(value, context):
    """
    Resolver en værdi og returner ALTID som string.
    Bruges til GUI tekst felter hvor vi vil vise tal som tekst.
    """
    resolved = resolve_value(value, context)
    if resolved is None:
        return ''
    return str(resolved)


def resolve_as_int(value, context, default=0):
    """
    Resolver en værdi og returner ALTID som int.
    Bruges til positions, størrelser osv.
    """
    resolved = resolve_value(value, context)
    if resolved is None:
        return default
    try:
        return int(float(resolved))
    except (ValueError, TypeError):
        return default


def resolve_as_float(value, context, default=0.0):
    """
    Resolver en værdi og returner ALTID som float.
    """
    resolved = resolve_value(value, context)
    if resolved is None:
        return default
    try:
        return float(resolved)
    except (ValueError, TypeError):
        return default


def resolve_as_bool(value, context, default=False):
    """
    Resolver en værdi og returner ALTID som bool.
    """
    resolved = resolve_value(value, context)
    if resolved is None:
        return default
    if isinstance(resolved, bool):
        return resolved
    if isinstance(resolved, (int, float)):
        return resolved != 0
    val_str = str(resolved).lower()
    return val_str in ('true', 'yes', '1', 'on', 'enabled')


def resolve_attributes(attributes, context):
    """
    Resolver alle attributter i en dict.
    
    Args:
        attributes: Dict med attributter
        context: PyTML context
    
    Returns:
        Ny dict med resolvede værdier
    """
    resolved = {}
    for key, value in attributes.items():
        resolved[key] = resolve_value(value, context)
    return resolved


class ActionNode:
    """Base klasse for actions - importeret her for at undgå circular imports"""
    
    def __init__(self, tag_name, attributes=None):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.children = []
        self.parent = None
        self._ready = False
        self._executed = False
    
    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        return child
    
    def children_ready(self):
        return all(child.is_ready() for child in self.children)
    
    def is_ready(self):
        return self._ready and self.children_ready()
    
    def execute(self, context):
        self._ready = True
        self._executed = True


class Variable:
    """Repræsenterer en variabel i PyTML"""
    
    def __init__(self, name, value=None):
        self.name = name
        self.value = value
        self.children = []
        self.parent = None
        self._ready = False
    
    def set_value(self, value):
        """Sæt værdien af variablen"""
        self.value = value
        self._ready = True
        return self
    
    def get_value(self):
        """Hent værdien af variablen"""
        return self.value
    
    def add_child(self, child):
        """Tilføj et child element"""
        child.parent = self
        self.children.append(child)
        return child
    
    def is_ready(self):
        """Tjek om variablen og alle children er klar"""
        if not self._ready:
            return False
        return all(child.is_ready() for child in self.children)
    
    def __repr__(self):
        return f"<var name=\"{self.name}\" value=\"{self.value}\">"


class VariableStore:
    """Gemmer alle variabler i PyTML programmet"""
    
    def __init__(self):
        self.variables = {}
    
    def create(self, name, value=None):
        """Opret en ny variabel"""
        var = Variable(name, value)
        if value is not None:
            var._ready = True
        self.variables[name] = var
        return var
    
    def get(self, name):
        """Hent en variabel ved navn"""
        return self.variables.get(name)
    
    def get_value(self, name):
        """Hent værdien af en variabel"""
        var = self.get(name)
        if var:
            return var.get_value()
        return None
    
    def set(self, name, value):
        """Sæt værdien af en variabel (opret hvis den ikke findes)"""
        if name in self.variables:
            self.variables[name].set_value(value)
        else:
            self.create(name, value)
        return self.variables[name]
    
    def exists(self, name):
        """Tjek om en variabel eksisterer"""
        return name in self.variables
    
    def all_ready(self):
        """Tjek om alle variabler er klar"""
        return all(var.is_ready() for var in self.variables.values())
    
    def __repr__(self):
        return f"VariableStore({list(self.variables.keys())})"


class VarNode(ActionNode):
    """Variabel definition node: <var name="x"> og <x_value="...">"""
    
    def execute(self, context):
        name = self.attributes.get('name')
        value = self.attributes.get('value')
        
        # Først udfør alle children
        for child in self.children:
            child.execute(context)
        
        # Tjek om value er __INPUT__ (skal prompte bruger)
        if value == '__INPUT__':
            prompt = self.attributes.get('prompt', f'Enter value for {name}: ')
            value = input(prompt)
        # Tjek om value er en reference til en anden variabel
        elif value and value.startswith('$'):
            ref_name = value[1:]
            value = context['variables'].get_value(ref_name)
        # Resolve value med context (håndterer <name_random>, <name_value>, etc.)
        elif value:
            value = resolve_value(value, context)
        
        if name:
            context['variables'].set(name, value)
        
        self._ready = True
        self._executed = True


def get_line_parsers():
    """Returner linje parsere for var modulet"""
    return [
        # <var name="x" value="..."> (med value)
        (r'<var\s+name="(\w+)"\s+value="([^"]*)">', _parse_var_with_value),
        # <var name="x" value=<ref_value>> (med variabel reference)
        (r'<var\s+name="(\w+)"\s+value=<(\w+)_value>>', _parse_var_with_ref),
        # <var name="x" value=<input>> (med input prompt)
        (r'<var\s+name="(\w+)"\s+value=<input>>', _parse_var_with_input),
        # <var name="x" value=<input prompt="...">>(med input prompt)
        (r'<var\s+name="(\w+)"\s+value=<input\s+prompt="([^"]*)">>', _parse_var_with_input_prompt),
        # <var name="x" value=<input "...">> (prompt i quotes)
        (r'<var\s+name="(\w+)"\s+value=<input\s+"([^"]*)">>', _parse_var_with_input_prompt),
        # <var name="x"> (uden value)
        (r'<var\s+name="(\w+)">', _parse_var_declaration),
        # <x_value="..."> (sæt værdi)
        (r'<(\w+)_value="([^"]*)">', _parse_var_value),
        
        # === MATEMATIK ===
        # <math var="x" op="+=" value="1">
        (r'<math\s+var="(\w+)"\s+op="([^"]+)"\s+value="([^"]*)">', _parse_math_full),
        # <math var="x" op="++" > eller <math var="x" op="inc">
        (r'<math\s+var="(\w+)"\s+op="(\+\+|--|inc|dec)">', _parse_math_inc_dec),
        # Shorthand: <x_value += 1> eller <x_value++>
        (r'<(\w+)_value\s*(\+\+|--)>', _parse_math_shorthand_incdec),
        (r'<(\w+)_value\s*(\+=|-=|\*=|/=|//=|%=|\*\*=|=)\s*(.+)>', _parse_math_shorthand),
        
        # === ALIASES: <variable> === 
        # <variable name="x" value="..."> (med value) - alias for <var>
        (r'<variable\s+name="(\w+)"\s+value="([^"]*)">', _parse_var_with_value),
        # <variable name="x" value=<ref_value>> (med variabel reference)
        (r'<variable\s+name="(\w+)"\s+value=<(\w+)_value>>', _parse_var_with_ref),
        # <variable name="x" value=<input>>
        (r'<variable\s+name="(\w+)"\s+value=<input>>', _parse_var_with_input),
        # <variable name="x" value=<input prompt="...">>
        (r'<variable\s+name="(\w+)"\s+value=<input\s+prompt="([^"]*)">>', _parse_var_with_input_prompt),
        # <variable name="x" value=<input "...">>
        (r'<variable\s+name="(\w+)"\s+value=<input\s+"([^"]*)">>', _parse_var_with_input_prompt),
        # <variable name="x"> (uden value)
        (r'<variable\s+name="(\w+)">', _parse_var_declaration),
    ]


def _parse_var_with_value(match, current, context):
    """Parse <var name="x" value="...">"""
    var_name = match.group(1)
    value = match.group(2)
    node = VarNode('var', {'name': var_name, 'value': value})
    current.add_child(node)
    return None


def _parse_var_with_ref(match, current, context):
    """Parse <var name="x" value=<other_value>>"""
    var_name = match.group(1)
    ref_name = match.group(2)
    # Gem som $reference så den resolves ved execute
    node = VarNode('var', {'name': var_name, 'value': f'${ref_name}'})
    current.add_child(node)
    return None


def _parse_var_with_input(match, current, context):
    """Parse <var name="x" value=<input>>"""
    var_name = match.group(1)
    # Marker at værdien skal hentes fra input ved execute
    node = VarNode('var', {'name': var_name, 'value': '__INPUT__'})
    current.add_child(node)
    return None


def _parse_var_with_input_prompt(match, current, context):
    """Parse <var name="x" value=<input prompt="...">>"""
    var_name = match.group(1)
    prompt = match.group(2)
    # Marker at værdien skal hentes fra input med prompt
    node = VarNode('var', {'name': var_name, 'value': '__INPUT__', 'prompt': prompt})
    current.add_child(node)
    return None


def _parse_var_declaration(match, current, context):
    """Parse <var name="x">"""
    var_name = match.group(1)
    node = VarNode('var', {'name': var_name})
    current.add_child(node)
    return None  # Forbliv på samme level


def _parse_var_value(match, current, context):
    """Parse <x_value="...">"""
    var_name = match.group(1)
    value = match.group(2)
    
    # Tjek om value er en reference til anden variabel
    import re
    ref_match = re.match(r'<(\w+)_value>', value)
    if ref_match:
        ref_name = ref_match.group(1)
        value = f'${ref_name}'
    
    node = VarNode('var', {'name': var_name, 'value': value})
    current.add_child(node)
    return None


def _parse_math_full(match, current, context):
    """Parse <math var="x" op="+=" value="1">"""
    var_name = match.group(1)
    op = match.group(2)
    value = match.group(3)
    node = MathNode('math', {'var': var_name, 'op': op, 'value': value})
    current.add_child(node)
    return None


def _parse_math_inc_dec(match, current, context):
    """Parse <math var="x" op="++">"""
    var_name = match.group(1)
    op = match.group(2)
    node = MathNode('math', {'var': var_name, 'op': op, 'value': '1'})
    current.add_child(node)
    return None


def _parse_math_shorthand_incdec(match, current, context):
    """Parse <x_value++> eller <x_value-->"""
    var_name = match.group(1)
    op = match.group(2)
    node = MathNode('math', {'var': var_name, 'op': op, 'value': '1'})
    current.add_child(node)
    return None


def _parse_math_shorthand(match, current, context):
    """Parse <x_value += 1> eller <x_value = <y_value> * 2>"""
    var_name = match.group(1)
    op = match.group(2)
    value = match.group(3).strip().rstrip('>')
    node = MathNode('math', {'var': var_name, 'op': op, 'value': value})
    current.add_child(node)
    return None


# Eksporter
__all__ = ['Variable', 'VariableStore', 'VarNode', 'MathNode', 'get_line_parsers', 
           'resolve_value', 'resolve_attributes', 'evaluate_math',
           'resolve_as_string', 'resolve_as_int', 'resolve_as_float', 'resolve_as_bool']


def evaluate_math(expression, context):
    """
    Evaluer et matematisk udtryk sikkert.
    
    Understøtter:
        - Grundlæggende operatorer: + - * / // % **
        - Sammenligninger: == != < > <= >=
        - Variabler: <name_value> eller $name
        - Funktioner: abs, min, max, round, int, float, len
        - Parenteser for gruppering
    
    Args:
        expression: Matematisk udtryk som string
        context: PyTML context med variabler
    
    Returns:
        Resultatet af beregningen
    """
    import re
    import math
    
    # Resolve variabler i udtrykket først
    resolved = resolve_value(expression, context)
    
    # Hvis det allerede er et tal, returner det
    if isinstance(resolved, (int, float)):
        return resolved
    
    expr = str(resolved)
    
    # Tillad kun sikre tegn
    allowed = set('0123456789+-*/%().eE <>=!absminmaxroundintfloatlen, ')
    if not all(c in allowed or c.isalnum() or c == '_' for c in expr):
        raise ValueError(f"Ugyldigt matematisk udtryk: {expression}")
    
    # Definer sikre funktioner
    safe_functions = {
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,
        'int': int,
        'float': float,
        'len': len,
        'sqrt': math.sqrt,
        'pow': pow,
    }
    
    try:
        # Evaluer sikkert
        result = eval(expr, {"__builtins__": {}}, safe_functions)
        return result
    except Exception as e:
        raise ValueError(f"Kunne ikke evaluere '{expression}': {e}")


class MathNode(ActionNode):
    """
    Math node - udfører matematik på variabler
    
    Syntax:
        <math var="x" op="+=" value="1">     # x += 1
        <math var="x" op="=" value="y * 2">  # x = y * 2
        <x_value += 1>                        # shorthand
        <x_value = <y_value> * 2>             # shorthand med reference
    """
    
    def execute(self, context):
        var_name = self.attributes.get('var')
        op = self.attributes.get('op', '=')
        value_expr = self.attributes.get('value', '0')
        
        if not var_name:
            self._ready = True
            return
        
        variables = context.get('variables')
        if not variables:
            self._ready = True
            return
        
        # Hent nuværende værdi
        current = variables.get_value(var_name)
        if current is None:
            current = 0
        
        # Evaluer value expression
        try:
            new_value = evaluate_math(value_expr, context)
        except:
            new_value = resolve_value(value_expr, context)
            try:
                new_value = float(new_value) if '.' in str(new_value) else int(new_value)
            except:
                new_value = 0
        
        # Konverter current til tal
        try:
            current = float(current) if '.' in str(current) else int(current)
        except:
            current = 0
        
        # Udfør operation
        if op == '=' or op == ':=':
            result = new_value
        elif op == '+=' or op == 'add':
            result = current + new_value
        elif op == '-=' or op == 'sub':
            result = current - new_value
        elif op == '*=' or op == 'mul':
            result = current * new_value
        elif op == '/=' or op == 'div':
            result = current / new_value if new_value != 0 else 0
        elif op == '//=' or op == 'floordiv':
            result = current // new_value if new_value != 0 else 0
        elif op == '%=' or op == 'mod':
            result = current % new_value if new_value != 0 else 0
        elif op == '**=' or op == 'pow':
            result = current ** new_value
        elif op == '++' or op == 'inc':
            result = current + 1
        elif op == '--' or op == 'dec':
            result = current - 1
        else:
            result = new_value
        
        # Gem resultatet
        variables.set(var_name, result)
        
        self._ready = True
        self._executed = True
