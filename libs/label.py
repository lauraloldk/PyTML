"""
PyTML Label Module
Håndterer labels/tekst i GUI vinduer
Understøtter variabel-interpolation i alle argumenter.

Syntax:
    <label text="Hej verden" name="lbl1" parent="wnd1">
    <label text=<greeting_value> name="lbl1" parent="wnd1" x="10" y="50">
    <lbl1_text="Ny tekst">
"""

import tkinter as tk
from tkinter import ttk

# Import resolve_value for variabel-interpolation
from libs.var import resolve_value, resolve_attributes, resolve_as_string


# Marker som GUI Node type
GUI_NODE_TYPE = "widget"


class ActionNode:
    """Base klasse for actions"""
    
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


class Label:
    """Repræsenterer et label i PyTML GUI"""
    
    def __init__(self, name, text="Label", x=0, y=0, width=100, height=25):
        self.name = name
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_size = 10
        self.font_family = "Segoe UI"
        self.foreground = "#000000"
        self.parent_window = None
        self._tk_label = None
        self._ready = False
    
    def create(self, parent_window):
        """Opret label i et vindue"""
        self.parent_window = parent_window
        tk_win = parent_window.get_tk_window()
        if tk_win:
            self._tk_label = ttk.Label(tk_win, text=self.text)
            self._tk_label.place(x=self.x, y=self.y, width=self.width, height=self.height)
        self._ready = True
        return self
    
    def set_text(self, text):
        """Sæt label tekst"""
        self.text = text
        if self._tk_label:
            self._tk_label.config(text=text)
        return self
    
    def set_position(self, x, y):
        """Sæt position"""
        self.x = x
        self.y = y
        if self._tk_label:
            self._tk_label.place(x=x, y=y)
        return self
    
    def set_foreground(self, color):
        """Sæt tekstfarve"""
        self.foreground = color
        if self._tk_label:
            self._tk_label.config(foreground=color)
        return self
    
    def is_ready(self):
        return self._ready
    
    def __repr__(self):
        return f'<label name="{self.name}" text="{self.text}">'


class LabelStore:
    """Gemmer alle labels"""
    
    def __init__(self):
        self.labels = {}
    
    def create(self, name, text="Label", x=0, y=0, width=100, height=25):
        """Opret et nyt label"""
        label = Label(name, text, x, y, width, height)
        self.labels[name] = label
        return label
    
    def get(self, name):
        """Hent et label ved navn"""
        return self.labels.get(name)
    
    def exists(self, name):
        """Tjek om et label eksisterer"""
        return name in self.labels


class LabelNode(ActionNode):
    """
    Label node - GUI Node type
    <label text="Hello" name="lbl1" parent="wnd1" x="10" y="20">
    Understøtter variabel-interpolation i alle argumenter.
    """
    
    # Marker som GUI node
    is_gui_node = True
    gui_type = "widget"
    gui_category = "label"
    
    def execute(self, context):
        for child in self.children:
            child.execute(context)
        
        # Resolve alle attributter med variabel-interpolation
        resolved = resolve_attributes(self.attributes, context)
        
        name = resolved.get('name')
        text = resolved.get('text', 'Label')
        parent_name = resolved.get('parent')
        x = int(resolved.get('x', 0))
        y = int(resolved.get('y', 0))
        width = int(resolved.get('width', 100))
        height = int(resolved.get('height', 25))
        
        if name:
            if 'labels' not in context:
                context['labels'] = LabelStore()
            
            label = context['labels'].create(name, str(text), x, y, width, height)
            
            # Tilføj til parent vindue hvis angivet
            if parent_name and 'windows' in context:
                parent_window = context['windows'].get(parent_name)
                if parent_window:
                    label.create(parent_window)
        
        self._ready = True
        self._executed = True


class LabelActionNode(ActionNode):
    """Label action nodes: <lbl1_text="...">"""
    
    is_gui_node = True
    gui_type = "action"
    
    def execute(self, context):
        name = self.attributes.get('label_name')
        action = self.attributes.get('action')
        raw_value = self.attributes.get('value')
        
        if 'labels' not in context:
            self._ready = True
            return
        
        label = context['labels'].get(name)
        if not label:
            self._ready = True
            return
        
        if action == 'text':
            # Brug resolve_as_string for at sikre tekst output
            text_value = resolve_as_string(raw_value, context)
            label.set_text(text_value)
        elif action == 'foreground':
            value = resolve_value(raw_value, context)
            label.set_foreground(value)
        elif action == 'position':
            value = resolve_value(raw_value, context)
            if isinstance(value, list) and len(value) >= 2:
                label.set_position(int(value[0]), int(value[1]))
        
        self._ready = True
        self._executed = True


def get_line_parsers():
    """Returner linje parsere for label modulet"""
    return [
        # <label text="Hello" name="lbl1" parent="wnd1">
        # Bruger greedy match til sidste > for at håndtere nested <var_value>
        (r'<label\s+(.+)>$', _parse_label_declaration),
        # NOTE: _text parser er flyttet til generisk widget handler i Compiler
    ]


def _parse_label_declaration(match, current, context):
    """
    Parse <label text="..." name="lbl1" parent="wnd1">
    Understøtter også: <label text=<text_value> name="lbl1">
    """
    import re
    attrs_str = match.group(1)
    
    attributes = {}
    
    # Parse attributter med quotes: attr="value"
    for attr_match in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
        attributes[attr_match.group(1)] = attr_match.group(2)
    
    # Parse attributter med variabel reference: attr=<var_value>
    for attr_match in re.finditer(r'(\w+)=(<\w+_value>)', attrs_str):
        attributes[attr_match.group(1)] = attr_match.group(2)
    
    node = LabelNode('label', attributes)
    current.add_child(node)
    return None


def _parse_label_text(match, current, context):
    """Parse <lbl1_text="..."> - tekst kan indeholde <var_value> referencer"""
    label_name = match.group(1)
    text = match.group(2)  # Kan være "hello" eller "<counter_value>" eller "Count: <x_value>"
    node = LabelActionNode('label_action', {
        'label_name': label_name,
        'action': 'text',
        'value': text
    })
    current.add_child(node)
    return None


def _parse_label_text_ref(match, current, context):
    """Parse <lbl1_text=<var_value>> - uden quotes"""
    label_name = match.group(1)
    text = match.group(2)  # <var_value>
    node = LabelActionNode('label_action', {
        'label_name': label_name,
        'action': 'text',
        'value': text
    })
    current.add_child(node)
    return None


# GUI Editor info
def get_gui_info():
    """Returner GUI editor information"""
    return {
        'type': 'widget',
        'category': 'label',
        'display_name': 'Label',
        'icon': '📝',
        'default_size': (100, 25),
        'properties': ['name', 'text', 'x', 'y', 'width', 'height', 'parent'],
        'syntax': '<label text="Label" name="lbl1" parent="wnd1" x="0" y="0">'
    }


# Eksporter
__all__ = [
    'Label',
    'LabelStore',
    'LabelNode',
    'LabelActionNode',
    'get_line_parsers',
    'get_gui_info',
    'GUI_NODE_TYPE'
]
