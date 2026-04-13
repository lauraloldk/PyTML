"""
PyTML Entry Module
Håndterer tekstfelter/input i GUI vinduer
Understøtter variabel-interpolation i alle argumenter.

Syntax:
    <entry name="txtInput" parent="wnd1">
    <entry name="nameField" parent="wnd1" placeholder=<hint_value> x="10" y="50">
    <txtInput_value="Startværdi">
    <txtInput_placeholder="Hint tekst">
    <txtInput_readonly="true">
    <txtInput_backgroundcolor="#ffffcc">
    <txtInput_textcolor="#333333">
"""

import tkinter as tk
from tkinter import ttk

# Import resolve_value for variabel-interpolation
from libs.var import resolve_value, resolve_attributes
from libs.core import ActionNode


# Marker som GUI Node type
GUI_NODE_TYPE = "widget"


class Entry:
    """Repræsenterer et tekstfelt i PyTML GUI"""
    
    def __init__(self, name, x=0, y=0, width=150, height=25):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.placeholder = ""
        self.readonly = False
        self.parent_window = None
        self._tk_entry = None
        self._tk_var = None
        self._ready = False
        self._backgroundcolor = None
        self._textcolor = None
    
    def create(self, parent_window):
        """Opret entry i et vindue"""
        self.parent_window = parent_window
        tk_win = parent_window.get_tk_window()
        if tk_win:
            self._tk_var = tk.StringVar()
            self._tk_entry = tk.Entry(tk_win, textvariable=self._tk_var)
            if getattr(parent_window, 'is_layout_container', False):
                pack_side = getattr(parent_window, 'pack_side', 'top')
                pack_fill = getattr(parent_window, 'pack_fill', 'x')
                spacing = getattr(parent_window, 'spacing', 2)
                self._tk_entry.pack(side=pack_side, fill=pack_fill,
                                    padx=spacing, pady=spacing)
            else:
                self._tk_entry.place(x=self.x, y=self.y, width=self.width, height=self.height)

            # Placeholder support
            if self.placeholder:
                self._setup_placeholder()

        self._ready = True
        return self
    
    def _setup_placeholder(self):
        """Opsæt placeholder tekst"""
        if not self._tk_entry:
            return
        
        def on_focus_in(event):
            if self._tk_entry.get() == self.placeholder:
                self._tk_entry.delete(0, tk.END)
                self._tk_entry.config(foreground='black')
        
        def on_focus_out(event):
            if not self._tk_entry.get():
                self._tk_entry.insert(0, self.placeholder)
                self._tk_entry.config(foreground='gray')
        
        self._tk_entry.insert(0, self.placeholder)
        self._tk_entry.config(foreground='gray')
        self._tk_entry.bind('<FocusIn>', on_focus_in)
        self._tk_entry.bind('<FocusOut>', on_focus_out)
    
    def get_value(self):
        """Hent tekstfeltets værdi"""
        if self._tk_var:
            val = self._tk_var.get()
            if val == self.placeholder:
                return ""
            return val
        return ""
    
    def set_value(self, value):
        """Sæt tekstfeltets værdi"""
        if self._tk_var:
            self._tk_var.set(value)
        return self
    
    def set_placeholder(self, placeholder):
        """Sæt placeholder tekst"""
        self.placeholder = placeholder
        if self._tk_entry and not self.get_value():
            self._setup_placeholder()
        return self
    
    def set_readonly(self, readonly):
        """Sæt readonly status"""
        self.readonly = readonly
        if self._tk_entry:
            self._tk_entry.config(state='readonly' if readonly else 'normal')
        return self
    
    def set_position(self, x, y):
        """Sæt position"""
        self.x = x
        self.y = y
        if self._tk_entry:
            self._tk_entry.place(x=x, y=y)
        return self
    
    def set_backgroundcolor(self, color):
        """Sæt baggrundsfarve"""
        self._backgroundcolor = color
        if self._tk_entry:
            self._tk_entry.configure(background=color)
        return self
    
    def set_textcolor(self, color):
        """Sæt tekstfarve"""
        self._textcolor = color
        if self._tk_entry:
            self._tk_entry.configure(foreground=color)
        return self
    
    def is_ready(self):
        return self._ready
    
    def __repr__(self):
        return f'<entry name="{self.name}">'


class EntryStore:
    """Gemmer alle entry felter"""
    
    def __init__(self):
        self.entries = {}
    
    def create(self, name, x=0, y=0, width=150, height=25):
        """Opret et nyt entry felt"""
        entry = Entry(name, x, y, width, height)
        self.entries[name] = entry
        return entry
    
    def get(self, name):
        """Hent et entry ved navn"""
        return self.entries.get(name)
    
    def exists(self, name):
        """Tjek om et entry eksisterer"""
        return name in self.entries
    
    def get_value(self, name):
        """Hent værdi fra et entry"""
        entry = self.get(name)
        if entry:
            return entry.get_value()
        return ""


class EntryNode(ActionNode):
    """
    Entry node - GUI Node type
    <entry name="txtInput" parent="wnd1" x="10" y="20">
    Understøtter variabel-interpolation i alle argumenter.
    """
    
    # Marker som GUI node
    is_gui_node = True
    gui_type = "widget"
    gui_category = "entry"
    
    def execute(self, context):
        for child in self.children:
            child.execute(context)
        
        # Resolve alle attributter med variabel-interpolation
        resolved = resolve_attributes(self.attributes, context)
        
        name = resolved.get('name')
        parent_name = resolved.get('parent')
        x = int(resolved.get('x', 0))
        y = int(resolved.get('y', 0))
        width = int(resolved.get('width', 150))
        height = int(resolved.get('height', 25))
        placeholder = str(resolved.get('placeholder', ''))
        
        if name:
            if 'entries' not in context:
                context['entries'] = EntryStore()
            
            entry = context['entries'].create(name, x, y, width, height)
            entry.placeholder = placeholder
            
            # Tilføj til parent vindue hvis angivet
            if parent_name and 'windows' in context:
                parent_window = context['windows'].get(parent_name)
                if parent_window:
                    entry.create(parent_window)
                    
                    # Anvend alle ekstra attributter via set_* metoder
                    skip_attrs = {'name', 'parent', 'x', 'y', 'width', 'height', 'placeholder'}
                    for pytml_name, value in resolved.items():
                        if pytml_name in skip_attrs:
                            continue
                        setter_name = f'set_{pytml_name}'
                        if hasattr(entry, setter_name):
                            getattr(entry, setter_name)(value)
        
        self._ready = True
        self._executed = True


class EntryActionNode(ActionNode):
    """Entry action nodes: <txtInput_value="...">, <txtInput_readonly="true">"""
    
    is_gui_node = True
    gui_type = "action"
    
    def execute(self, context):
        # Resolve attributter med variabel-interpolation
        resolved = resolve_attributes(self.attributes, context)
        
        name = resolved.get('entry_name')
        action = resolved.get('action')
        value = resolved.get('value')
        
        if 'entries' not in context:
            self._ready = True
            return
        
        entry = context['entries'].get(name)
        if not entry:
            self._ready = True
            return
        
        if action == 'value':
            entry.set_value(str(value))
        elif action == 'placeholder':
            entry.set_placeholder(str(value))
        elif action == 'readonly':
            entry.set_readonly(str(value).lower() == 'true')
        
        self._ready = True
        self._executed = True


def get_line_parsers():
    """Returner linje parsere for entry modulet"""
    return [
        # <entry name="txtInput" parent="wnd1">
        # Bruger greedy match til sidste > for at håndtere nested <var_value>
        (r'<entry\s+(.+)>$', _parse_entry_declaration),
        # <txtInput_value="..."> eller <txtInput_value=<var_value>>
        (r'<(\w+)_value=(?:"([^"]*)"|(<\w+_value>))>', _parse_entry_value),
        # <txtInput_placeholder="..."> eller med var
        (r'<(\w+)_placeholder=(?:"([^"]*)"|(<\w+_value>))>', _parse_entry_placeholder),
        # <txtInput_readonly="true">
        (r'<(\w+)_readonly="(\w+)">', _parse_entry_readonly),
    ]


def _parse_entry_declaration(match, current, context):
    """
    Parse <entry name="..." parent="wnd1">
    Understøtter også: <entry name="txt" placeholder=<hint_value>>
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
    
    node = EntryNode('entry', attributes)
    current.add_child(node)
    return None


def _parse_entry_value(match, current, context):
    """Parse <txtInput_value="..."> eller <txtInput_value=<var_value>>"""
    entry_name = match.group(1)
    # group(2) er quoted string, group(3) er variabel reference
    value = match.group(2) if match.group(2) is not None else match.group(3)
    node = EntryActionNode('entry_action', {
        'entry_name': entry_name,
        'action': 'value',
        'value': value
    })
    current.add_child(node)
    return None


def _parse_entry_placeholder(match, current, context):
    """Parse <txtInput_placeholder="..."> eller med variabel"""
    entry_name = match.group(1)
    # group(2) er quoted string, group(3) er variabel reference
    placeholder = match.group(2) if match.group(2) is not None else match.group(3)
    node = EntryActionNode('entry_action', {
        'entry_name': entry_name,
        'action': 'placeholder',
        'value': placeholder
    })
    current.add_child(node)
    return None


def _parse_entry_readonly(match, current, context):
    """Parse <txtInput_readonly="true">"""
    entry_name = match.group(1)
    readonly = match.group(2)
    node = EntryActionNode('entry_action', {
        'entry_name': entry_name,
        'action': 'readonly',
        'value': readonly
    })
    current.add_child(node)
    return None


# GUI Editor info
def get_gui_info():
    """Return GUI editor information - dynamically extracted"""
    return {
        'type': 'widget',
        'category': 'entry',
        'display_name': 'Entry',
        'icon': '✏️',
        'framework': 'tkinter',
        'default_size': (150, 25),
        'editor_colors': {'bg': '#3c3c3c', 'border': '#858585', 'text': '#d4d4d4'},
        'properties': _extract_properties(Entry),
        'syntax': '<entry name="txtInput" parent="wnd1" x="0" y="0">'
    }


def _extract_properties(cls):
    """Dynamically extract all properties from a class"""
    import inspect
    props = []
    
    # From __init__ parameters
    try:
        sig = inspect.signature(cls.__init__)
        for name, param in sig.parameters.items():
            if name != 'self' and not name.startswith('_'):
                prop_info = {'name': name, 'type': 'string'}
                if param.default != inspect.Parameter.empty:
                    default = param.default
                    prop_info['default'] = default
                    if isinstance(default, bool):
                        prop_info['type'] = 'bool'
                    elif isinstance(default, int):
                        prop_info['type'] = 'int'
                    elif isinstance(default, str) and default.startswith('#'):
                        prop_info['type'] = 'color'
                if 'color' in name.lower():
                    prop_info['type'] = 'color'
                props.append(prop_info)
    except:
        pass
    
    # From set_* methods
    for method_name in dir(cls):
        if method_name.startswith('set_') and not method_name.startswith('set__'):
            prop_name = method_name[4:]  # Remove 'set_'
            # Skip internal/deprecated methods
            if prop_name in ('position',):
                continue
            if not any(p['name'] == prop_name for p in props):
                prop_info = {'name': prop_name, 'type': 'string'}
                if 'color' in prop_name.lower():
                    prop_info['type'] = 'color'
                elif prop_name in ('enabled', 'readonly', 'visible'):
                    prop_info['type'] = 'bool'
                elif prop_name in ('x', 'y', 'width', 'height'):
                    prop_info['type'] = 'int'
                props.append(prop_info)
    
    # Add parent for widgets
    if not any(p['name'] == 'parent' for p in props):
        props.append({'name': 'parent', 'type': 'element_ref'})
    
    return props


# Eksporter
__all__ = [
    'Entry',
    'EntryStore',
    'EntryNode',
    'EntryActionNode',
    'get_line_parsers',
    'get_gui_info',
    'GUI_NODE_TYPE'
]
