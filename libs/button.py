"""
PyTML Button Module
Håndterer knapper i GUI vinduer
Understøtter variabel-interpolation i alle argumenter.

Syntax:
    <button text="Klik her" name="btn1" parent="wnd1">
    <button text=<btntext_value> name="btn1" parent="wnd1" x="10" y="50">
    <btn1_click="action">
    <btn1_text="Ny tekst">
    <btn1_enabled="true">
"""

import tkinter as tk
from tkinter import ttk

# Import resolve_value for variabel-interpolation
from libs.var import resolve_value, resolve_attributes


# Marker som GUI Node type
GUI_NODE_TYPE = "widget"

# PyTML navn -> tkinter navn mapping
# LibEditor tilføjer automatisk nye entries her
CONFIG_MAP = {
    # Farver
    'clickcolor': 'activebackground',
    'frontcolor': 'fg',
    'foreground': 'fg',
    'background': 'bg',
    'textcolor': 'fg',
    'hovercolor': 'activebackground',
    # Tekst
    'text': 'text',
    # Tilstand
    'enabled': 'state',
    'disabled': 'state',
    # Font
    'fontsize': 'font',
    'fontfamily': 'font',
    # Cursor
    'cursor': 'cursor',
    'pointer': 'cursor',
}


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


class Button:
    """Repræsenterer en knap i PyTML GUI"""
    
    def __init__(self, name, text="Button", x=0, y=0, width=100, height=30):
        self.name = name
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.enabled = True
        self.parent_window = None
        self._tk_button = None
        self._click_handler = None
        self._context = None  # Reference til PyTML context for events
        self._ready = False
    
    def create(self, parent_window, context=None, **extra_config):
        """Opret knappen i et vindue"""
        self.parent_window = parent_window
        self._context = context
        tk_win = parent_window.get_tk_window()
        if tk_win:
            # Brug tk.Button (ikke ttk) for at understøtte activebackground osv.
            config = {'text': self.text, 'command': self._on_click}
            config.update(extra_config)
            self._tk_button = tk.Button(tk_win, **config)
            self._tk_button.place(x=self.x, y=self.y, width=self.width, height=self.height)
        self._ready = True
        return self
    
    def _on_click(self):
        """Intern click handler - registrer event i context"""
        # Registrer event i context
        if self._context is not None:
            if 'events' not in self._context:
                self._context['events'] = {}
            self._context['events'][f'{self.name}_click'] = True
        
        # Kald custom handler hvis sat
        if self._click_handler:
            self._click_handler()
    
    def set_click_handler(self, handler):
        """Sæt click handler"""
        self._click_handler = handler
        return self
    
    def set_text(self, text):
        """Sæt knappens tekst"""
        self.text = text
        if self._tk_button:
            self._tk_button.config(text=text)
        return self
    
    def set_enabled(self, enabled):
        """Aktiver/deaktiver knappen"""
        self.enabled = enabled
        if self._tk_button:
            self._tk_button.config(state='normal' if enabled else 'disabled')
        return self
    
    def set_position(self, x, y):
        """Sæt position"""
        self.x = x
        self.y = y
        if self._tk_button:
            self._tk_button.place(x=x, y=y)
        return self

    def set_clickcolor(self, value):
        """Sæt clickcolor (farve når der klikkes)"""
        self.clickcolor = value
        if self._tk_button:
            self._tk_button.configure(activebackground=value)
        return self

    def set_frontcolor(self, value):
        """Sæt frontcolor"""
        self.frontcolor = value
        if self._tk_widget:
            self._tk_widget.configure(activeforeground=value)
        return self


    
    def is_ready(self):
        return self._ready
    
    def __repr__(self):
        return f'<button name="{self.name}" text="{self.text}">'


class ButtonStore:
    """Gemmer alle knapper"""
    
    def __init__(self):
        self.buttons = {}
    
    def create(self, name, text="Button", x=0, y=0, width=100, height=30):
        """Opret en ny knap"""
        button = Button(name, text, x, y, width, height)
        self.buttons[name] = button
        return button
    
    def get(self, name):
        """Hent en knap ved navn"""
        return self.buttons.get(name)
    
    def exists(self, name):
        """Tjek om en knap eksisterer"""
        return name in self.buttons


class ButtonNode(ActionNode):
    """
    Button node - GUI Node type
    <button text="Klik" name="btn1" parent="wnd1" x="10" y="20">
    Understøtter variabel-interpolation i alle argumenter.
    """
    
    # Marker som GUI node
    is_gui_node = True
    gui_type = "widget"
    gui_category = "button"
    
    def execute(self, context):
        for child in self.children:
            child.execute(context)
        
        # Resolve alle attributter med variabel-interpolation
        resolved = resolve_attributes(self.attributes, context)
        
        name = resolved.get('name')
        text = resolved.get('text', 'Button')
        parent_name = resolved.get('parent')
        x = int(resolved.get('x', 0))
        y = int(resolved.get('y', 0))
        width = int(resolved.get('width', 100))
        height = int(resolved.get('height', 30))
        
        if name:
            if 'buttons' not in context:
                context['buttons'] = ButtonStore()
            
            button = context['buttons'].create(name, text, x, y, width, height)
            
            # Automatisk map alle PyTML attributter til tkinter via CONFIG_MAP
            extra_config = {}
            skip_attrs = {'name', 'text', 'parent', 'x', 'y', 'width', 'height'}
            for pytml_name, value in resolved.items():
                if pytml_name in skip_attrs:
                    continue
                # Slå op i CONFIG_MAP - hvis ikke fundet, brug navnet direkte
                tk_name = CONFIG_MAP.get(pytml_name, pytml_name)
                extra_config[tk_name] = value
            
            # Tilføj til parent vindue hvis angivet
            if parent_name and 'windows' in context:
                parent_window = context['windows'].get(parent_name)
                if parent_window:
                    button.create(parent_window, context, **extra_config)  # Send context og config
        
        self._ready = True
        self._executed = True


class ButtonActionNode(ActionNode):
    """Button action nodes: <btn1_text="...">, <btn1_enabled="true">"""
    
    is_gui_node = True
    gui_type = "action"
    
    def execute(self, context):
        # Resolve attributter med variabel-interpolation
        resolved = resolve_attributes(self.attributes, context)
        
        name = resolved.get('button_name')
        action = resolved.get('action')
        value = resolved.get('value')
        
        if 'buttons' not in context:
            self._ready = True
            return
        
        button = context['buttons'].get(name)
        if not button:
            self._ready = True
            return
        
        if action == 'text':
            button.set_text(str(value))
        elif action == 'enabled':
            enabled = str(value).lower() == 'true'
            button.set_enabled(enabled)
        elif action == 'position':
            if isinstance(value, list) and len(value) >= 2:
                button.set_position(int(value[0]), int(value[1]))
        
        self._ready = True
        self._executed = True


def get_line_parsers():
    """Returner linje parsere for button modulet"""
    return [
        # <button text="Klik" name="btn1" parent="wnd1">
        # Bruger greedy match til sidste > for at håndtere nested <var_value>
        (r'<button\s+(.+)>$', _parse_button_declaration),
        # <btn1_enabled="true">
        (r'<(\w+)_enabled="(\w+)">', _parse_button_enabled),
        # NOTE: _text parser er flyttet til generisk widget handler i Compiler
    ]


def _parse_button_declaration(match, current, context):
    """
    Parse <button text="..." name="btn1" parent="wnd1">
    Understøtter også: <button text=<text_value> name="btn1">
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
    
    node = ButtonNode('button', attributes)
    current.add_child(node)
    return None


def _parse_button_text(match, current, context):
    """Parse <btn1_text="..."> eller <btn1_text=<var_value>>"""
    button_name = match.group(1)
    # group(2) er quoted string, group(3) er variabel reference
    text = match.group(2) if match.group(2) is not None else match.group(3)
    node = ButtonActionNode('button_action', {
        'button_name': button_name,
        'action': 'text',
        'value': text
    })
    current.add_child(node)
    return None


def _parse_button_enabled(match, current, context):
    """Parse <btn1_enabled="true">"""
    button_name = match.group(1)
    enabled = match.group(2)
    node = ButtonActionNode('button_action', {
        'button_name': button_name,
        'action': 'enabled',
        'value': enabled
    })
    current.add_child(node)
    return None


# GUI Editor info
def get_gui_info():
    """Return GUI editor information"""
    return {
        'type': 'widget',
        'category': 'button',
        'display_name': 'Button',
        'icon': '🔘',
        'framework': 'tkinter',
        'default_size': (100, 30),
        'properties': ['name', 'text', 'x', 'y', 'width', 'height', 'parent'],
        'syntax': '<button text="Button" name="btn1" parent="wnd1" x="0" y="0">'
    }


# Eksporter
__all__ = [
    'Button',
    'ButtonStore',
    'ButtonNode',
    'ButtonActionNode',
    'get_line_parsers',
    'get_gui_info',
    'GUI_NODE_TYPE'
]
