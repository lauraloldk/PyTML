"""
PyTML Core - Widget Utilities
=============================
Abstrakte utility-funktioner og stores for widgets.
Definerer KUN mekanismer - ikke properties/metoder.

Properties og metoder defineres i de specifikke lib filer.
"""

from typing import Any, Dict, Optional, List


class Store:
    """
    Generisk store til at gemme og hente objekter ved navn.
    Bruges af ButtonStore, LabelStore, EntryStore, WindowStore, etc.
    """
    
    def __init__(self):
        self._items: Dict[str, Any] = {}
    
    def add(self, name: str, item: Any) -> Any:
        """Tilføj item til store"""
        self._items[name] = item
        return item
    
    def get(self, name: str) -> Optional[Any]:
        """Hent item ved navn"""
        return self._items.get(name)
    
    def exists(self, name: str) -> bool:
        """Tjek om item eksisterer"""
        return name in self._items
    
    def remove(self, name: str) -> bool:
        """Fjern item"""
        if name in self._items:
            del self._items[name]
            return True
        return False
    
    def all(self) -> List[Any]:
        """Hent alle items"""
        return list(self._items.values())
    
    def names(self) -> List[str]:
        """Hent alle navne"""
        return list(self._items.keys())
    
    def clear(self):
        """Ryd store"""
        self._items.clear()
    
    def __iter__(self):
        return iter(self._items.values())
    
    def __len__(self):
        return len(self._items)
    
    def __contains__(self, name: str):
        return name in self._items


def apply_attributes_via_setters(obj: Any, attributes: Dict[str, Any], 
                                  skip_attrs: set = None) -> None:
    """
    Anvend attributter på et objekt via dets set_* metoder.
    
    Bruges af alle widget nodes til at anvende resolved attributes.
    
    Args:
        obj: Objekt der skal have attributter sat
        attributes: Dict med attributter
        skip_attrs: Set af attributter der skal springes over
    """
    skip = skip_attrs or set()
    
    for attr_name, value in attributes.items():
        if attr_name in skip:
            continue
        
        setter_name = f'set_{attr_name}'
        if hasattr(obj, setter_name):
            setter = getattr(obj, setter_name)
            if callable(setter):
                try:
                    setter(value)
                except Exception:
                    pass  # Ignorer fejl i setters


def extract_properties_from_object(obj_or_cls) -> List[Dict[str, Any]]:
    """
    Ekstraher properties dynamisk fra et objekts/klasses __init__ og set_* metoder.
    
    Bruges af Properties/GUIEdit panels til at vise properties.
    INGEN hardkodede properties - alt kommer fra klassen selv.
    
    Args:
        obj_or_cls: Objekt eller klasse der skal analyseres
    
    Returns:
        Liste af property dicts med name, type, default, etc.
    """
    import inspect
    
    cls = obj_or_cls if isinstance(obj_or_cls, type) else type(obj_or_cls)
    
    properties = []
    seen = set()
    
    # Tjek __init__ parametre
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
                
                # Gæt type fra default
                default = param.default if param.default != inspect.Parameter.empty else None
                prop_type = type(default).__name__ if default is not None else 'str'
                
                properties.append({
                    'name': name,
                    'type': prop_type,
                    'default': default
                })
        except (ValueError, TypeError):
            pass
    
    # Tjek set_* metoder
    for name in dir(cls):
        if name.startswith('set_') and callable(getattr(cls, name, None)):
            prop_name = name[4:]  # Fjern 'set_' prefix
            if prop_name in seen or prop_name.startswith('_'):
                continue
            seen.add(prop_name)
            
            method = getattr(cls, name)
            doc = method.__doc__ or ''
            
            properties.append({
                'name': prop_name,
                'type': 'str',
                'description': doc.strip() if doc else ''
            })
    
    return properties
