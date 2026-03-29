"""
PyTML Core - Base Classes
=========================
Base klasser for alle PyTML nodes og elementer.
"""

from typing import Any, Dict, List, Optional


class ActionNode:
    """
    Base klasse for alle PyTML action nodes.
    
    Alle nodes (window, button, var, if, loop, etc.) arver fra denne.
    Giver fælles funktionalitet:
    - Attribut håndtering
    - Child management
    - Execution state
    - Property system integration
    """
    
    # Metadata - override i subklasser
    tag_name: str = 'node'
    is_gui_node: bool = False
    gui_type: str = None  # 'widget', 'container', 'action'
    gui_category: str = None  # 'window', 'button', etc.
    
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
    
    def execute(self, context: Dict) -> None:
        """
        Udfør denne node.
        Override i subklasser for specifik funktionalitet.
        """
        for child in self.children:
            child.execute(context)
        self._ready = True
        self._executed = True
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Hent en attribut"""
        return self.attributes.get(name, default)
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Sæt en attribut"""
        self.attributes[name] = value
    
    def __repr__(self):
        attrs = ', '.join(f'{k}={v!r}' for k, v in self.attributes.items())
        return f"<{self.tag_name} {attrs}>"


class BlockNode(ActionNode):
    """
    Container node for andre nodes.
    Bruges til <gui>, <code>, <block> etc.
    """
    
    def __init__(self, tag_name: str = 'block', attributes: Dict[str, Any] = None):
        super().__init__(tag_name, attributes)
    
    def execute(self, context: Dict) -> None:
        """Udfør alle children"""
        for child in self.children:
            child.execute(context)
        self._ready = True
        self._executed = True


class ContainerNode(ActionNode):
    """
    Node der indeholder andre nodes med visuelt hierarki.
    Bruges til windows og lignende.
    """
    
    is_gui_node = True
    gui_type = 'container'
    
    def __init__(self, tag_name: str, attributes: Dict[str, Any] = None):
        super().__init__(tag_name, attributes)
        self._widgets = {}
    
    def get_widget(self, name: str):
        """Hent en widget fra denne container"""
        return self._widgets.get(name)
    
    def add_widget(self, name: str, widget):
        """Tilføj en widget til denne container"""
        self._widgets[name] = widget
        return widget


class WidgetNode(ActionNode):
    """
    Base node for GUI widgets (button, label, entry, etc.)
    """
    
    is_gui_node = True
    gui_type = 'widget'
    
    def __init__(self, tag_name: str, attributes: Dict[str, Any] = None):
        super().__init__(tag_name, attributes)
        self._tk_widget = None
        self._parent_window = None
    
    def get_tk_widget(self):
        """Hent det underliggende tkinter widget"""
        return self._tk_widget
