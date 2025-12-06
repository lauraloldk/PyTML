"""
PyTML Window Module
Håndterer vinduer med HTML-lignende tags og "stacks" (multi-argument tags)
Understøtter variabel-interpolation i alle argumenter.

Syntax:
    <window title="Test" size="300","350" name="wnd1">
    <window title=<title_value> size="300" name="wnd1">  // Med variabel
    <wnd1_show>
    <wnd1_hide>
    <wnd1_title="Ny Titel">
    <wnd1_size="400","500">
"""

import tkinter as tk
from tkinter import ttk

# Import resolve_value for variabel-interpolation
from libs.var import resolve_value, resolve_attributes, resolve_as_string


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


class Window:
    """Repræsenterer et vindue i PyTML"""
    
    def __init__(self, name, title="PyTML Window", width=300, height=300):
        self.name = name
        self.title = title
        self.width = width
        self.height = height
        self.visible = False
        self.children = []
        self.parent = None
        self._ready = False
        self._tk_window = None
        self._widgets = {}
    
    def _create_window(self):
        """Opret det faktiske tkinter vindue"""
        if self._tk_window is None:
            self._tk_window = tk.Toplevel()
            self._tk_window.title(self.title)
            self._tk_window.geometry(f"{self.width}x{self.height}")
            self._tk_window.protocol("WM_DELETE_WINDOW", self.hide)
        return self._tk_window
    
    def show(self):
        """Vis vinduet"""
        self._create_window()
        self._tk_window.deiconify()
        self.visible = True
        self._ready = True
        return self
    
    def hide(self):
        """Skjul vinduet"""
        if self._tk_window:
            self._tk_window.withdraw()
        self.visible = False
        return self
    
    def close(self):
        """Luk vinduet helt"""
        if self._tk_window:
            self._tk_window.destroy()
            self._tk_window = None
        self.visible = False
        return self
    
    def set_title(self, title):
        """Sæt vinduets titel"""
        self.title = title
        if self._tk_window:
            self._tk_window.title(title)
        return self

    def exit(self):
        """Kald destroy"""
        if self._tk_window:
            self._tk_window.destroy()
        return self

    
    def set_size(self, width, height=None):
        """Sæt vinduets størrelse"""
        if height is None:
            height = width  # Hvis kun én værdi, brug den for begge
        self.width = width
        self.height = height
        if self._tk_window:
            self._tk_window.geometry(f"{self.width}x{self.height}")
        return self
    
    def add_child(self, child):
        """Tilføj et child element (widget)"""
        child.parent = self
        self.children.append(child)
        return child
    
    def is_ready(self):
        """Tjek om vinduet og alle children er klar"""
        if not self._ready:
            return False
        return all(child.is_ready() for child in self.children if hasattr(child, 'is_ready'))
    
    def get_tk_window(self):
        """Hent det underliggende tkinter vindue"""
        return self._tk_window
    
    def __repr__(self):
        return f'<window name="{self.name}" title="{self.title}" size="{self.width}x{self.height}">'


class WindowStore:
    """Gemmer alle vinduer i PyTML programmet"""
    
    def __init__(self):
        self.windows = {}
        self._tk_root = None
    
    def _ensure_root(self):
        """Sørg for at der er et tk root vindue"""
        if self._tk_root is None:
            self._tk_root = tk.Tk()
            self._tk_root.withdraw()  # Skjul root vinduet
        return self._tk_root
    
    def create(self, name, title="PyTML Window", width=300, height=300):
        """Opret et nyt vindue"""
        self._ensure_root()
        window = Window(name, title, width, height)
        self.windows[name] = window
        return window
    
    def get(self, name):
        """Hent et vindue ved navn"""
        return self.windows.get(name)
    
    def exists(self, name):
        """Tjek om et vindue eksisterer"""
        return name in self.windows
    
    def show(self, name):
        """Vis et vindue"""
        window = self.get(name)
        if window:
            window.show()
        return window
    
    def hide(self, name):
        """Skjul et vindue"""
        window = self.get(name)
        if window:
            window.hide()
        return window
    
    def close_all(self):
        """Luk alle vinduer"""
        for window in self.windows.values():
            window.close()
        if self._tk_root:
            self._tk_root.destroy()
            self._tk_root = None
    
    def mainloop(self):
        """Start tkinter mainloop"""
        if self._tk_root:
            self._tk_root.mainloop()
    
    def __repr__(self):
        return f"WindowStore({list(self.windows.keys())})"


class WindowNode(ActionNode):
    """
    Window definition node (Stack node med flere argumenter):
    <window title="Test" size="300","350" name="wnd1">
    <window title=<title_value> size="300","350" name="wnd1">  // Med variabel
    """
    
    # Marker som GUI node
    is_gui_node = True
    gui_type = "container"
    gui_category = "window"
    
    def execute(self, context):
        # Først udfør alle children
        for child in self.children:
            child.execute(context)
        
        # Resolve alle attributter med variabel-interpolation
        resolved = resolve_attributes(self.attributes, context)
        
        name = resolved.get('name')
        title = resolved.get('title', 'PyTML Window')
        size = resolved.get('size', [300, 300])
        
        # Håndter size som liste eller enkelt værdi
        if isinstance(size, list):
            width = int(size[0])
            height = int(size[1]) if len(size) > 1 else width
        else:
            width = height = int(size)
        
        if name:
            # Sørg for at windows store eksisterer
            if 'windows' not in context:
                context['windows'] = WindowStore()
            context['windows'].create(name, title, width, height)
        
        self._ready = True
        self._executed = True


class WindowActionNode(ActionNode):
    """
    Window action nodes:
    <wnd1_show>, <wnd1_hide>, <wnd1_title="...">, <wnd1_size="...">
    Understøtter variabel-interpolation.
    """
    
    def execute(self, context):
        name = self.attributes.get('window_name')
        action = self.attributes.get('action')
        raw_value = self.attributes.get('value')
        
        if 'windows' not in context:
            self._ready = True
            self._executed = True
            return
        
        window = context['windows'].get(name)
        if not window:
            self._ready = True
            self._executed = True
            return
        
        if action == 'show':
            window.show()
        elif action == 'hide':
            window.hide()
        elif action == 'close':
            window.close()
        elif action == 'title':
            # Brug resolve_as_string for at håndtere tal som tekst
            title_value = resolve_as_string(raw_value, context)
            window.set_title(title_value)
        elif action == 'size':
            value = resolve_value(raw_value, context)
            if isinstance(value, list):
                window.set_size(int(value[0]), int(value[1]) if len(value) > 1 else None)
            else:
                window.set_size(int(value))
        
        self._ready = True
        self._executed = True


def parse_stack_args(arg_string):
    """
    Parse stack argumenter (komma-separerede værdier i quotes)
    "300","350" -> [300, 350]
    "300" -> [300]
    """
    import re
    matches = re.findall(r'"([^"]*)"', arg_string)
    return matches if matches else [arg_string]


def get_line_parsers():
    """Returner linje parsere for window modulet"""
    return [
        # <window title="Test" size="300","350" name="wnd1">
        # Bruger greedy match til sidste > på linjen for at håndtere nested <var_value>
        (r'<window\s+(.+)>$', _parse_window_declaration),
        # <wnd1_show>
        (r'<(\w+)_show>', _parse_window_show),
        # <wnd1_hide>
        (r'<(\w+)_hide>', _parse_window_hide),
        # <wnd1_close>
        (r'<(\w+)_close>', _parse_window_close),
        # <wnd1_title="..."> eller <wnd1_title=<var_value>> eller <wnd1_title ="<var_value>">
        # Tillader valgfrit mellemrum før =
        (r'<(\w+)_title\s*=\s*"(<[^>]+>)">', _parse_window_title_var),  # Med nested tag i quotes
        (r'<(\w+)_title\s*=\s*(<\w+_value>)>', _parse_window_title_ref),  # Med direkte variabel ref
        (r'<(\w+)_title\s*=\s*"([^"]*)">', _parse_window_title),  # Med literal string
        # <wnd1_size="300","350"> eller <wnd1_size="300">
        (r'<(\w+)_size=(.+)>$', _parse_window_size),
    ]


def _parse_window_declaration(match, current, context):
    """
    Parse <window title="Test" size="300","350" name="wnd1">
    Understøtter også: <window title=<title_value> name="wnd1">
    """
    import re
    attrs_str = match.group(1)
    
    attributes = {}
    
    # Parse title="..." eller title=<var_value>
    title_match = re.search(r'title=(?:"([^"]*)"|(<\w+_value>))', attrs_str)
    if title_match:
        if title_match.group(1) is not None:
            attributes['title'] = title_match.group(1)
        else:
            attributes['title'] = title_match.group(2)  # Gem som <var_value> for resolve
    
    # Parse name="..." eller name=<var_value>
    name_match = re.search(r'name=(?:"(\w+)"|(<\w+_value>))', attrs_str)
    if name_match:
        if name_match.group(1) is not None:
            attributes['name'] = name_match.group(1)
        else:
            attributes['name'] = name_match.group(2)
    
    # Parse size="300","350" eller size=<var_value> eller size="300"
    size_match = re.search(r'size=(?:("[\d,"\s]+"|"\d+")|(<\w+_value>))', attrs_str)
    if size_match:
        if size_match.group(1) is not None:
            size_str = size_match.group(1)
            attributes['size'] = parse_stack_args(size_str)
        else:
            attributes['size'] = size_match.group(2)
    
    node = WindowNode('window', attributes)
    current.add_child(node)
    return None


def _parse_window_show(match, current, context):
    """Parse <wnd1_show>"""
    window_name = match.group(1)
    node = WindowActionNode('window_action', {
        'window_name': window_name,
        'action': 'show'
    })
    current.add_child(node)
    return None


def _parse_window_hide(match, current, context):
    """Parse <wnd1_hide>"""
    window_name = match.group(1)
    node = WindowActionNode('window_action', {
        'window_name': window_name,
        'action': 'hide'
    })
    current.add_child(node)
    return None


def _parse_window_close(match, current, context):
    """Parse <wnd1_close>"""
    window_name = match.group(1)
    node = WindowActionNode('window_action', {
        'window_name': window_name,
        'action': 'close'
    })
    current.add_child(node)
    return None


def _parse_window_title(match, current, context):
    """Parse <wnd1_title="literal">"""
    window_name = match.group(1)
    title = match.group(2)
    node = WindowActionNode('window_action', {
        'window_name': window_name,
        'action': 'title',
        'value': title
    })
    current.add_child(node)
    return None


def _parse_window_title_var(match, current, context):
    """Parse <wnd1_title ="<ent1_value>"> - nested tag i quotes"""
    window_name = match.group(1)
    title = match.group(2)  # F.eks. <ent1_value>
    node = WindowActionNode('window_action', {
        'window_name': window_name,
        'action': 'title',
        'value': title
    })
    current.add_child(node)
    return None


def _parse_window_title_ref(match, current, context):
    """Parse <wnd1_title=<var_value>> - direkte variabel reference"""
    window_name = match.group(1)
    title = match.group(2)  # F.eks. <titlevar_value>
    node = WindowActionNode('window_action', {
        'window_name': window_name,
        'action': 'title',
        'value': title
    })
    current.add_child(node)
    return None


def _parse_window_size(match, current, context):
    """Parse <wnd1_size="300","350">"""
    window_name = match.group(1)
    size_str = match.group(2)
    size_values = parse_stack_args(size_str)
    node = WindowActionNode('window_action', {
        'window_name': window_name,
        'action': 'size',
        'value': size_values
    })
    current.add_child(node)
    return None


# GUI Editor info
def get_gui_info():
    """Returner GUI editor information"""
    return {
        'type': 'container',
        'category': 'window',
        'display_name': 'Window',
        'icon': '📦',
        'default_size': (300, 200),
        'properties': ['name', 'title', 'size'],
        'syntax': '<window title="Window" size="300","200" name="wnd1">'
    }


# Marker som GUI Node type
GUI_NODE_TYPE = "container"


# Eksporter
__all__ = [
    'Window',
    'WindowStore', 
    'WindowNode',
    'WindowActionNode',
    'parse_stack_args',
    'get_line_parsers',
    'get_gui_info',
    'GUI_NODE_TYPE'
]
