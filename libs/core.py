"""
PyTML Core Module
=================
Fælles base klasser, properties og metoder for alle libs.
Dette eliminerer duplikering og sikrer konsistent opførsel.

Indeholder:
- ActionNode: Base klasse for alle nodes
- PropertyDescriptor: System til at definere properties
- MethodDescriptor: System til at definere metoder
- resolve_value/resolve_attributes: Variabel interpolation
"""

import re
from typing import Any, Dict, List, Optional, Callable, Type, Union


# =============================================================================
# PROPERTY SYSTEM
# =============================================================================

class PropertyDescriptor:
    """
    Beskriver en property på et PyTML element.
    
    Bruges til at definere:
    - Navn og type
    - Default værdi
    - Validering
    - Om den kan interpoleres (indeholde variabler)
    
    Eksempel:
        PropertyDescriptor('text', str, default='', interpolate=True)
        PropertyDescriptor('x', int, default=0)
        PropertyDescriptor('enabled', bool, default=True)
    """
    
    def __init__(
        self,
        name: str,
        prop_type: Type,
        default: Any = None,
        required: bool = False,
        interpolate: bool = True,
        validator: Optional[Callable[[Any], bool]] = None,
        description: str = ""
    ):
        self.name = name
        self.prop_type = prop_type
        self.default = default
        self.required = required
        self.interpolate = interpolate
        self.validator = validator
        self.description = description
    
    def validate(self, value: Any) -> bool:
        """Valider en værdi mod denne property"""
        if value is None:
            return not self.required
        
        # Type check
        if self.prop_type == bool:
            # Booleans kan være strings som 'true'/'false'
            if isinstance(value, str):
                return value.lower() in ('true', 'false', '1', '0', 'yes', 'no')
        
        # Custom validator
        if self.validator:
            return self.validator(value)
        
        return True
    
    def convert(self, value: Any) -> Any:
        """Konverter en værdi til den rigtige type"""
        if value is None:
            return self.default
        
        if self.prop_type == bool:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        
        if self.prop_type == int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return self.default
        
        if self.prop_type == float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return self.default
        
        return value
    
    def __repr__(self):
        return f"PropertyDescriptor('{self.name}', {self.prop_type.__name__}, default={self.default})"


class MethodDescriptor:
    """
    Beskriver en metode/action på et PyTML element.
    
    Bruges til at definere:
    - Navn og parametre
    - Return type
    - Implementering
    
    Eksempel:
        MethodDescriptor('show', handler=lambda self, ctx: self.widget.show())
        MethodDescriptor('set_text', params=['value'], handler=...)
    """
    
    def __init__(
        self,
        name: str,
        params: List[str] = None,
        handler: Optional[Callable] = None,
        returns: Type = None,
        description: str = ""
    ):
        self.name = name
        self.params = params or []
        self.handler = handler
        self.returns = returns
        self.description = description
    
    def __repr__(self):
        params_str = ', '.join(self.params)
        return f"MethodDescriptor('{self.name}({params_str})')"


# =============================================================================
# BASE NODE CLASSES
# =============================================================================

class ActionNode:
    """
    Base klasse for alle PyTML nodes.
    
    Alle nodes (window, button, var, if, loop, etc.) arver fra denne.
    Giver fælles funktionalitet:
    - Attribut håndtering
    - Child management
    - Execution state
    - Property system integration
    """
    
    # Override i subklasser for at definere properties
    _properties: Dict[str, PropertyDescriptor] = {}
    
    # Override i subklasser for at definere metoder
    _methods: Dict[str, MethodDescriptor] = {}
    
    # Metadata
    tag_name: str = 'node'
    is_gui_node: bool = False
    gui_type: str = None  # 'widget', 'container', 'action'
    
    def __init__(self, tag_name: str, attributes: Dict[str, Any] = None):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.children: List['ActionNode'] = []
        self.parent: Optional['ActionNode'] = None
        self._ready = False
        self._executed = False
    
    def add_child(self, child: 'ActionNode') -> 'ActionNode':
        """Tilføj et child element"""
        child.parent = self
        self.children.append(child)
        return child
    
    def remove_child(self, child: 'ActionNode') -> bool:
        """Fjern et child element"""
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            return True
        return False
    
    def children_ready(self) -> bool:
        """Tjek om alle children er klar"""
        return all(child.is_ready() for child in self.children)
    
    def is_ready(self) -> bool:
        """Tjek om denne node er klar"""
        return self._ready and self.children_ready()
    
    def get_property(self, name: str, context: Dict = None) -> Any:
        """
        Hent en property værdi med automatisk interpolation.
        
        Args:
            name: Property navn
            context: PyTML context for variabel interpolation
        """
        value = self.attributes.get(name)
        
        # Tjek om property findes i schema
        prop_desc = self._properties.get(name)
        
        if value is None and prop_desc:
            value = prop_desc.default
        
        # Interpoler hvis tilladt
        if context and prop_desc and prop_desc.interpolate:
            value = resolve_value(value, context)
        
        # Konverter til rigtig type
        if prop_desc:
            value = prop_desc.convert(value)
        
        return value
    
    def set_property(self, name: str, value: Any):
        """Sæt en property værdi"""
        self.attributes[name] = value
    
    def execute(self, context: Dict) -> Any:
        """
        Udfør denne node.
        Override i subklasser for specifik opførsel.
        """
        # Udfør alle children
        for child in self.children:
            child.execute(context)
        
        self._ready = True
        self._executed = True
        return None
    
    def __repr__(self):
        attrs = ', '.join(f'{k}="{v}"' for k, v in self.attributes.items())
        return f'<{self.tag_name} {attrs}>'


class ContainerNode(ActionNode):
    """
    Base klasse for nodes der indeholder andre nodes.
    F.eks. window, gui, block, if, loop.
    """
    
    is_container = True
    
    def execute(self, context: Dict) -> Any:
        """Udfør alle children i rækkefølge"""
        results = []
        for child in self.children:
            result = child.execute(context)
            if result is not None:
                results.append(result)
        
        self._ready = True
        self._executed = True
        return results if results else None


class WidgetNode(ActionNode):
    """
    Base klasse for GUI widgets.
    F.eks. button, entry, label.
    """
    
    is_gui_node = True
    gui_type = 'widget'
    
    # Fælles properties for alle widgets
    _properties = {
        'name': PropertyDescriptor('name', str, required=True),
        'parent': PropertyDescriptor('parent', str),
        'x': PropertyDescriptor('x', int, default=0),
        'y': PropertyDescriptor('y', int, default=0),
        'width': PropertyDescriptor('width', int, default=100),
        'height': PropertyDescriptor('height', int, default=30),
        'enabled': PropertyDescriptor('enabled', bool, default=True),
        'visible': PropertyDescriptor('visible', bool, default=True),
    }


# =============================================================================
# VARIABEL INTERPOLATION
# =============================================================================

def resolve_value(value: Any, context: Dict) -> Any:
    """
    Resolver en værdi der kan indeholde variabel-referencer.
    
    Understøtter:
        <varname_value>  -> værdien af variablen 'varname' ELLER entry felt
        <name_random>    -> kalder callable i context (f.eks. random generator)
        $varname         -> værdien af variablen 'varname'  
        "literal"        -> literal string (uændret)
        123              -> tal (uændret)
    
    Args:
        value: Værdien der skal resolves
        context: PyTML context dict
    
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
    
    result = value
    
    # Pattern 1: <name_value> or <name_something> syntax
    tag_pattern = r'<(\w+)_(\w+)>'
    
    def replace_tag(match):
        name = match.group(1)
        suffix = match.group(2)
        full_key = f"{name}_{suffix}"
        
        # First check if there's a callable in context with this exact key
        # This handles things like <rnd_random> -> context['rnd_random']()
        if full_key in context:
            ctx_value = context[full_key]
            if callable(ctx_value):
                return str(ctx_value())
            return str(ctx_value)
        
        # If suffix is 'value', check entries and variables
        if suffix == 'value':
            # Check entries first
            if entries:
                entry = entries.get(name) if hasattr(entries, 'get') else None
                if entry:
                    return str(entry.get_value() if hasattr(entry, 'get_value') else entry)
            
            # Check variables
            if variables:
                var_value = variables.get_value(name) if hasattr(variables, 'get_value') else variables.get(name)
                if var_value is not None:
                    return str(var_value)
        
        # Check randoms for specific methods
        randoms = context.get('randoms')
        if randoms and name in randoms:
            rng = randoms[name]
            if suffix == 'random' and hasattr(rng, 'random'):
                return str(rng.random())
            elif suffix == 'float' and hasattr(rng, 'random_float'):
                return str(rng.random_float())
        
        return match.group(0)
    
    result = re.sub(tag_pattern, replace_tag, result)
    
    # Pattern 2: $varname syntax
    dollar_pattern = r'\$(\w+)'
    
    def replace_dollar(match):
        var_name = match.group(1)
        if variables:
            var_value = variables.get_value(var_name) if hasattr(variables, 'get_value') else variables.get(var_name)
            if var_value is not None:
                return str(var_value)
        return match.group(0)
    
    result = re.sub(dollar_pattern, replace_dollar, result)
    
    return result


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


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_stack_args(arg_string: str) -> List[str]:
    """
    Parse stack argumenter (komma-separerede værdier i quotes)
    "300","350" -> ['300', '350']
    "300" -> ['300']
    """
    matches = re.findall(r'"([^"]*)"', arg_string)
    return matches if matches else [arg_string]


def parse_bool(value: Any) -> bool:
    """Parse en værdi til boolean"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'PropertyDescriptor',
    'MethodDescriptor',
    'ActionNode',
    'ContainerNode',
    'WidgetNode',
    'resolve_value',
    'resolve_attributes',
    'parse_stack_args',
    'parse_bool',
]
