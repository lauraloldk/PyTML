"""
PyTML Core - Variable Resolution
================================
Funktioner til at resolve variabel-referencer i PyTML værdier.

Understøtter flere syntakser:
- <varname_value> -> værdien af variablen
- <name_random>   -> random tal fra navngivet generator
- $varname        -> alternativ variabel syntax
"""

import re
from typing import Any, Dict, List, Union


def resolve_value(value: Any, context: Dict) -> Any:
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


def resolve_as_string(value: Any, context: Dict) -> str:
    """
    Resolver en værdi og returner ALTID som string.
    Bruges til GUI tekst felter hvor vi vil vise tal som tekst.
    """
    resolved = resolve_value(value, context)
    if resolved is None:
        return ''
    return str(resolved)


def resolve_as_int(value: Any, context: Dict, default: int = 0) -> int:
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


def resolve_as_float(value: Any, context: Dict, default: float = 0.0) -> float:
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


def resolve_as_bool(value: Any, context: Dict, default: bool = False) -> bool:
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


def resolve_attributes(attributes: Dict[str, Any], context: Dict) -> Dict[str, Any]:
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


def interpolate_string(template: str, context: Dict) -> str:
    """
    Interpoler en template string med variabel værdier.
    
    Erstatter {varname} og <varname_value> med faktiske værdier.
    
    Args:
        template: String med variabel placeholders
        context: PyTML context
    
    Returns:
        Interpoleret string
    """
    result = template
    
    # Først håndter <name_value> syntax
    result = resolve_value(result, context)
    
    # Derefter håndter {name} syntax
    if '{' in str(result):
        variables = context.get('variables')
        if variables:
            pattern = r'\{(\w+)\}'
            def replace_brace(match):
                var_name = match.group(1)
                var_value = variables.get_value(var_name)
                return str(var_value) if var_value is not None else match.group(0)
            result = re.sub(pattern, replace_brace, str(result))
    
    return str(result)
