"""
PyTML Core Package
==================
Fælles logik og abstrakte mekanismer for PyTML.
Definerer KUN logik - ikke properties/metoder (de hører til i libs).

Indeholder:
- base: ActionNode og andre base klasser
- resolve: Variabel interpolation (resolve_value, etc.)
- properties: Property og Method descriptors (abstrakt)
- widgets: Store og utility funktioner (ingen hardkodede properties)
"""

# Re-export alle vigtige klasser og funktioner
from core.base import ActionNode, BlockNode, ContainerNode, WidgetNode
from core.resolve import (
    resolve_value, 
    resolve_attributes, 
    resolve_as_string,
    resolve_as_int,
    resolve_as_float,
    resolve_as_bool,
    interpolate_string
)
from core.properties import (
    PropertyDescriptor, 
    MethodDescriptor, 
    EventDescriptor,
    extract_properties_from_class,
    extract_methods_from_class
)
from core.widgets import (
    Store,
    apply_attributes_via_setters,
    extract_properties_from_object
)

__all__ = [
    # Base (abstrakte node klasser)
    'ActionNode',
    'BlockNode',
    'ContainerNode',
    'WidgetNode',
    
    # Resolve (variabel interpolation logik)
    'resolve_value',
    'resolve_attributes',
    'resolve_as_string',
    'resolve_as_int',
    'resolve_as_float',
    'resolve_as_bool',
    'interpolate_string',
    
    # Properties (abstrakte descriptors)
    'PropertyDescriptor',
    'MethodDescriptor',
    'EventDescriptor',
    'extract_properties_from_class',
    'extract_methods_from_class',
    
    # Widgets (utility funktioner)
    'Store',
    'apply_attributes_via_setters',
    'extract_properties_from_object',
]
