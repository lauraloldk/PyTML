"""
PyTML Core - Property System
============================
Systemer til at definere og håndtere properties og metoder på PyTML elementer.
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union


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
        description: str = "",
        choices: List[Any] = None,
        category: str = "general"
    ):
        self.name = name
        self.prop_type = prop_type
        self.default = default
        self.required = required
        self.interpolate = interpolate
        self.validator = validator
        self.description = description
        self.choices = choices
        self.category = category
    
    def validate(self, value: Any) -> bool:
        """Valider en værdi mod denne property"""
        if value is None:
            return not self.required
        
        # Type check
        if self.prop_type == bool:
            # Booleans kan være strings som 'true'/'false'
            if isinstance(value, str):
                return value.lower() in ('true', 'false', '1', '0', 'yes', 'no')
        
        # Choices check
        if self.choices is not None:
            if value not in self.choices:
                return False
        
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
                return value.lower() in ('true', '1', 'yes', 'on')
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
        
        if self.prop_type == str:
            return str(value) if value is not None else self.default
        
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Konverter til dict for serialisering"""
        return {
            'name': self.name,
            'type': self.prop_type.__name__,
            'default': self.default,
            'required': self.required,
            'interpolate': self.interpolate,
            'description': self.description,
            'choices': self.choices,
            'category': self.category
        }
    
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
        description: str = "",
        category: str = "general"
    ):
        self.name = name
        self.params = params or []
        self.handler = handler
        self.returns = returns
        self.description = description
        self.category = category
    
    def invoke(self, instance: Any, context: Dict, *args, **kwargs) -> Any:
        """Kald denne metode på et instans"""
        if self.handler:
            return self.handler(instance, context, *args, **kwargs)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konverter til dict for serialisering"""
        return {
            'name': self.name,
            'params': self.params,
            'returns': self.returns.__name__ if self.returns else None,
            'description': self.description,
            'category': self.category
        }
    
    def __repr__(self):
        params_str = ', '.join(self.params)
        return f"MethodDescriptor('{self.name}({params_str})')"


class EventDescriptor:
    """
    Beskriver en event på et PyTML element.
    
    Bruges til at definere:
    - Event navn (f.eks. 'click', 'change')
    - Parametre der sendes med eventet
    """
    
    def __init__(
        self,
        name: str,
        params: List[str] = None,
        description: str = "",
        category: str = "events"
    ):
        self.name = name
        self.params = params or []
        self.description = description
        self.category = category
    
    def to_dict(self) -> Dict[str, Any]:
        """Konverter til dict for serialisering"""
        return {
            'name': self.name,
            'params': self.params,
            'description': self.description,
            'category': self.category
        }
    
    def __repr__(self):
        return f"EventDescriptor('{self.name}')"


def extract_properties_from_class(cls) -> List[PropertyDescriptor]:
    """
    Ekstraher properties fra en klasses __init__ og set_* metoder.
    
    Analyserer:
    - __init__ parametre
    - set_* metoder
    - _propertyname attributter
    
    Returns:
        Liste af PropertyDescriptor objekter
    """
    properties = []
    seen = set()
    
    # Tjek __init__ parametre
    import inspect
    if hasattr(cls, '__init__'):
        try:
            sig = inspect.signature(cls.__init__)
            for name, param in sig.parameters.items():
                if name in ('self', 'args', 'kwargs'):
                    continue
                if name.startswith('_'):
                    continue
                if name in seen:
                    continue
                seen.add(name)
                
                # Prøv at gætte type fra default
                default = param.default if param.default != inspect.Parameter.empty else None
                prop_type = type(default) if default is not None else str
                
                properties.append(PropertyDescriptor(
                    name=name,
                    prop_type=prop_type,
                    default=default
                ))
        except (ValueError, TypeError):
            pass
    
    # Tjek set_* metoder
    for name in dir(cls):
        if name.startswith('set_') and callable(getattr(cls, name, None)):
            prop_name = name[4:]  # Fjern 'set_' prefix
            if prop_name in seen:
                continue
            if prop_name.startswith('_'):
                continue
            seen.add(prop_name)
            
            # Prøv at finde docstring for type hint
            method = getattr(cls, name)
            doc = method.__doc__ or ''
            
            properties.append(PropertyDescriptor(
                name=prop_name,
                prop_type=str,
                description=doc.strip() if doc else ''
            ))
    
    return properties


def extract_methods_from_class(cls) -> List[MethodDescriptor]:
    """
    Ekstraher metoder fra en klasse.
    
    Finder alle public metoder (ikke _ eller __).
    
    Returns:
        Liste af MethodDescriptor objekter
    """
    methods = []
    seen = set()
    
    for name in dir(cls):
        if name.startswith('_'):
            continue
        if name in seen:
            continue
        
        attr = getattr(cls, name, None)
        if not callable(attr):
            continue
        
        seen.add(name)
        
        # Prøv at finde parametre
        import inspect
        params = []
        try:
            sig = inspect.signature(attr)
            for pname in sig.parameters:
                if pname not in ('self', 'cls', 'args', 'kwargs'):
                    params.append(pname)
        except (ValueError, TypeError):
            pass
        
        doc = attr.__doc__ or ''
        
        methods.append(MethodDescriptor(
            name=name,
            params=params,
            description=doc.strip() if doc else ''
        ))
    
    return methods
