"""
PyTML Lib Editor
Scans the entire Python codebase and lets you add support for anything
Uses gui_detector module for intelligent graphical package detection
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
import inspect
import pkgutil
import importlib

# Import GUI detector
from gui_detector import (
    GUIDetector, GRAPHICAL_PACKAGES, GUI_ELEMENT_TYPES,
    GRAPHICAL_PROPERTY_INDICATORS, is_graphical_module, is_graphical_class
)


# Datatype definitions for PyTML
PYTML_DATATYPES = {
    'Color': {'icon': '🎨', 'description': 'Color (hex, name or RGB)', 'examples': ['red', '#FF0000', 'rgb(255,0,0)']},
    'Text': {'icon': '📝', 'description': 'Text string', 'examples': ['Hello', 'Button text']},
    'Number': {'icon': '🔢', 'description': 'Integer or decimal', 'examples': ['10', '3.14', '100']},
    'Bool': {'icon': '✓', 'description': 'True/False', 'examples': ['true', 'false', '1', '0']},
    'Font': {'icon': '🔤', 'description': 'Font family', 'examples': ['Arial', 'Helvetica 12 bold']},
    'Image': {'icon': '🖼️', 'description': 'Image file', 'examples': ['icon.png', 'photo.gif']},
    'File': {'icon': '📁', 'description': 'File path', 'examples': ['data.txt', 'config.json']},
    'Cursor': {'icon': '👆', 'description': 'Cursor type', 'examples': ['hand2', 'arrow', 'crosshair']},
    'Anchor': {'icon': '⚓', 'description': 'Position anchor', 'examples': ['n', 'se', 'center', 'nw']},
    'Relief': {'icon': '🔲', 'description': 'Border style', 'examples': ['flat', 'raised', 'sunken', 'groove']},
    'Justify': {'icon': '📐', 'description': 'Text alignment', 'examples': ['left', 'center', 'right']},
    'State': {'icon': '⚡', 'description': 'Widget state', 'examples': ['normal', 'disabled', 'active']},
    'Pixels': {'icon': '📏', 'description': 'Pixel size', 'examples': ['10', '100', '5p']},
    'Time': {'icon': '⏱️', 'description': 'Time in milliseconds', 'examples': ['100', '1000', '500']},
    'Callback': {'icon': '📞', 'description': 'Function/event', 'examples': ['on_click', 'handler']},
    'List': {'icon': '📋', 'description': 'List of values', 'examples': ['[1,2,3]', 'a,b,c']},
    'Unknown': {'icon': '❓', 'description': 'Unknown type', 'examples': []},
}

# Mapping from tkinter option names to datatypes
OPTION_TYPE_MAP = {
    # Colors
    'background': 'Color', 'bg': 'Color', 'foreground': 'Color', 'fg': 'Color',
    'activebackground': 'Color', 'activeforeground': 'Color',
    'disabledforeground': 'Color', 'disabledbackground': 'Color',
    'highlightbackground': 'Color', 'highlightcolor': 'Color',
    'insertbackground': 'Color', 'selectbackground': 'Color',
    'selectforeground': 'Color', 'troughcolor': 'Color',
    'readonlybackground': 'Color', 'selectcolor': 'Color',
    
    # Text
    'text': 'Text', 'label': 'Text', 'title': 'Text', 'textvariable': 'Text',
    'placeholder': 'Text', 'show': 'Text',
    
    # Numbers
    'width': 'Pixels', 'height': 'Pixels', 'borderwidth': 'Pixels', 'bd': 'Pixels',
    'padx': 'Pixels', 'pady': 'Pixels', 'highlightthickness': 'Pixels',
    'insertwidth': 'Pixels', 'selectborderwidth': 'Pixels', 'wraplength': 'Pixels',
    'underline': 'Number', 'takefocus': 'Number', 'exportselection': 'Number',
    
    # Font
    'font': 'Font',
    
    # Images
    'image': 'Image', 'bitmap': 'Image', 'selectimage': 'Image',
    
    # Cursor
    'cursor': 'Cursor',
    
    # Anchor/Position
    'anchor': 'Anchor', 'justify': 'Justify', 'compound': 'Anchor',
    'sticky': 'Anchor',
    
    # Relief/Style
    'relief': 'Relief',
    
    # State
    'state': 'State', 'default': 'State',
    
    # Bool
    'overrelief': 'Relief', 'indicatoron': 'Bool', 'offrelief': 'Relief',
    
    # Callback
    'command': 'Callback', 'xscrollcommand': 'Callback', 'yscrollcommand': 'Callback',
    'validatecommand': 'Callback', 'invalidcommand': 'Callback',
    
    # Time
    'repeatdelay': 'Time', 'repeatinterval': 'Time', 'insertofftime': 'Time',
    'insertontime': 'Time',
}


def guess_datatype(option_name, current_value=''):
    """Guess datatype based on option name and value"""
    # First check known mappings
    if option_name in OPTION_TYPE_MAP:
        return OPTION_TYPE_MAP[option_name]
    
    # Guess based on name
    name_lower = option_name.lower()
    
    if any(c in name_lower for c in ['color', 'colour', 'background', 'foreground', 'bg', 'fg']):
        return 'Color'
    if any(t in name_lower for t in ['text', 'label', 'title', 'caption', 'message']):
        return 'Text'
    if any(n in name_lower for n in ['width', 'height', 'size', 'thickness', 'pad', 'margin', 'border']):
        return 'Pixels'
    if any(f in name_lower for f in ['font', 'family']):
        return 'Font'
    if any(i in name_lower for i in ['image', 'icon', 'bitmap', 'photo', 'picture']):
        return 'Image'
    if any(c in name_lower for c in ['cursor', 'pointer']):
        return 'Cursor'
    if any(s in name_lower for s in ['state', 'enabled', 'disabled', 'active']):
        return 'State'
    if any(b in name_lower for b in ['visible', 'show', 'hide', 'enabled', 'checked', 'selected']):
        return 'Bool'
    if any(t in name_lower for t in ['time', 'delay', 'interval', 'duration', 'timeout']):
        return 'Time'
    if any(c in name_lower for c in ['command', 'callback', 'handler', 'action', 'onclick', 'on_']):
        return 'Callback'
    if any(f in name_lower for f in ['file', 'path', 'directory', 'folder']):
        return 'File'
    if any(a in name_lower for a in ['anchor', 'align', 'justify', 'position']):
        return 'Anchor'
    if any(r in name_lower for r in ['relief', 'style', 'border']):
        return 'Relief'
    
    # Guess based on value
    if current_value:
        val = str(current_value).lower()
        if val in ['true', 'false', '0', '1', 'yes', 'no']:
            return 'Bool'
        if val.startswith('#') or val in ['red', 'green', 'blue', 'white', 'black', 'yellow', 'gray', 'grey']:
            return 'Color'
        if val.replace('.', '').replace('-', '').isdigit():
            return 'Number'
    
    return 'Unknown'


class PythonScanner:
    """Scans the entire Python codebase"""
    
    def __init__(self):
        self.modules_cache = {}
        self.classes_cache = {}
    
    def get_all_modules(self):
        """Get list of all installed modules"""
        modules = []
        
        # Standard library
        stdlib = ['tkinter', 'os', 'sys', 'json', 'datetime', 'collections', 
                  'pathlib', 'subprocess', 'threading', 'socket', 'http',
                  'urllib', 'email', 'html', 'xml', 'sqlite3', 'csv']
        modules.extend(stdlib)
        
        # All installed packages
        for importer, modname, ispkg in pkgutil.iter_modules():
            if not modname.startswith('_'):
                modules.append(modname)
        
        return sorted(set(modules))
    
    def get_module_classes(self, module_name):
        """Get all classes from a module"""
        try:
            if module_name in self.modules_cache:
                return self.modules_cache[module_name]
            
            module = importlib.import_module(module_name)
            classes = []
            
            for name in dir(module):
                if not name.startswith('_'):
                    obj = getattr(module, name, None)
                    if inspect.isclass(obj):
                        classes.append((name, obj))
            
            # Also check submodules
            if hasattr(module, '__path__'):
                for importer, subname, ispkg in pkgutil.iter_modules(module.__path__):
                    if not subname.startswith('_'):
                        try:
                            submod = importlib.import_module(f"{module_name}.{subname}")
                            for name in dir(submod):
                                if not name.startswith('_'):
                                    obj = getattr(submod, name, None)
                                    if inspect.isclass(obj):
                                        classes.append((f"{subname}.{name}", obj))
                        except:
                            pass
            
            self.modules_cache[module_name] = classes
            return classes
        except Exception as e:
            return []
    
    def get_class_members(self, cls):
        """Get all properties and methods from a class"""
        members = {
            'properties': [],
            'methods': [],
            'config_options': [],  # Special for tkinter
        }
        
        # Get methods and properties
        for name in dir(cls):
            if name.startswith('_'):
                continue
            
            try:
                attr = getattr(cls, name, None)
                
                if callable(attr):
                    try:
                        sig = inspect.signature(attr)
                        params = list(sig.parameters.keys())
                        members['methods'].append({
                            'name': name,
                            'params': params,
                            'signature': str(sig),
                            'doc': inspect.getdoc(attr) or ''
                        })
                    except:
                        members['methods'].append({
                            'name': name,
                            'params': [],
                            'signature': '(...)',
                            'doc': ''
                        })
                elif isinstance(attr, property):
                    members['properties'].append({
                        'name': name,
                        'type': 'property',
                        'doc': inspect.getdoc(attr) or ''
                    })
            except:
                pass
        
        # Special for tkinter: get config options
        if hasattr(cls, 'configure') or hasattr(cls, 'config'):
            try:
                root = tk.Tk()
                root.withdraw()
                
                if cls in [tk.Tk, tk.Toplevel]:
                    instance = cls()
                else:
                    instance = cls(root)
                
                if hasattr(instance, 'keys'):
                    for key in instance.keys():
                        current_val = str(instance.cget(key))[:50]
                        datatype = guess_datatype(key, current_val)
                        members['config_options'].append({
                            'name': key,
                            'type': 'config',
                            'datatype': datatype,
                            'current': current_val
                        })
                
                instance.destroy()
                root.destroy()
            except:
                pass
        
        return members


class LibEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PyTML Lib Editor - Full Python Scanner")
        self.root.geometry("1200x800")
        
        self.scanner = PythonScanner()
        self.gui_detector = GUIDetector()  # Use external GUI detector
        self.current_class = None
        self.selected_members = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup main window"""
        # Status bar first so other methods can use it
        self.status_var = tk.StringVar(value="Ready - select a module to scan")
        
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="PyTML Lib Editor", font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Save Lib", command=self._save_lib).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="Edit Existing", command=self._edit_existing).pack(side=tk.RIGHT, padx=5)
        
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        self._setup_browser(left_frame)
        
        middle_frame = ttk.Frame(paned)
        paned.add(middle_frame, weight=2)
        self._setup_members(middle_frame)
        
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        self._setup_selected(right_frame)
        
        ttk.Label(self.root, textvariable=self.status_var).pack(fill=tk.X, padx=5, pady=2)
    
    def _setup_browser(self, parent):
        """Module and class browser"""
        ttk.Label(parent, text="Python Modules", font=('Arial', 11, 'bold')).pack()
        
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=2, pady=2)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.module_search = ttk.Entry(search_frame)
        self.module_search.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.module_search.bind('<KeyRelease>', self._filter_modules)
        
        ttk.Label(parent, text="Modules:").pack(anchor=tk.W)
        
        mod_frame = ttk.Frame(parent)
        mod_frame.pack(fill=tk.BOTH, expand=True)
        
        self.module_list = tk.Listbox(mod_frame, exportselection=False)
        mod_scroll = ttk.Scrollbar(mod_frame, command=self.module_list.yview)
        self.module_list.configure(yscrollcommand=mod_scroll.set)
        self.module_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mod_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.module_list.bind('<<ListboxSelect>>', self._on_module_select)
        
        ttk.Label(parent, text="Classes:").pack(anchor=tk.W, pady=(10,0))
        
        cls_frame = ttk.Frame(parent)
        cls_frame.pack(fill=tk.BOTH, expand=True)
        
        self.class_list = tk.Listbox(cls_frame, exportselection=False)
        cls_scroll = ttk.Scrollbar(cls_frame, command=self.class_list.yview)
        self.class_list.configure(yscrollcommand=cls_scroll.set)
        self.class_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cls_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.class_list.bind('<<ListboxSelect>>', self._on_class_select)
        
        self._load_modules()
    
    def _setup_members(self, parent):
        """Show all members of selected class"""
        ttk.Label(parent, text="Class Members", font=('Arial', 11, 'bold')).pack()
        
        self.members_notebook = ttk.Notebook(parent)
        self.members_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Config Options tab
        config_frame = ttk.Frame(self.members_notebook)
        self.members_notebook.add(config_frame, text="Config Options")
        
        self.config_tree = ttk.Treeview(config_frame, columns=('datatype', 'value', 'pytml_name'), show='tree headings')
        self.config_tree.heading('#0', text='Option')
        self.config_tree.heading('datatype', text='Type')
        self.config_tree.heading('value', text='Default')
        self.config_tree.heading('pytml_name', text='PyTML Name')
        self.config_tree.column('#0', width=150)
        self.config_tree.column('datatype', width=80)
        self.config_tree.column('value', width=120)
        self.config_tree.column('pytml_name', width=100)
        config_scroll = ttk.Scrollbar(config_frame, command=self.config_tree.yview)
        self.config_tree.configure(yscrollcommand=config_scroll.set)
        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        config_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_tree.bind('<Double-1>', self._add_config_to_pytml)
        self.config_tree.bind('<Button-3>', self._show_datatype_info)  # Right-click for info
        
        # Methods tab
        method_frame = ttk.Frame(self.members_notebook)
        self.members_notebook.add(method_frame, text="Methods")
        
        self.method_tree = ttk.Treeview(method_frame, columns=('signature', 'pytml_name'), show='tree headings')
        self.method_tree.heading('#0', text='Method')
        self.method_tree.heading('signature', text='Signature')
        self.method_tree.heading('pytml_name', text='PyTML Name')
        method_scroll = ttk.Scrollbar(method_frame, command=self.method_tree.yview)
        self.method_tree.configure(yscrollcommand=method_scroll.set)
        self.method_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        method_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.method_tree.bind('<Double-1>', self._add_method_to_pytml)
        
        # Properties tab
        prop_frame = ttk.Frame(self.members_notebook)
        self.members_notebook.add(prop_frame, text="Properties")
        
        self.prop_tree = ttk.Treeview(prop_frame, columns=('type', 'pytml_name'), show='tree headings')
        self.prop_tree.heading('#0', text='Property')
        self.prop_tree.heading('type', text='Type')
        self.prop_tree.heading('pytml_name', text='PyTML Name')
        prop_scroll = ttk.Scrollbar(prop_frame, command=self.prop_tree.yview)
        self.prop_tree.configure(yscrollcommand=prop_scroll.set)
        self.prop_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        prop_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.prop_tree.bind('<Double-1>', self._add_prop_to_pytml)
        
        # GUI Editor Info tab - for graphical packages
        gui_frame = ttk.Frame(self.members_notebook)
        self.members_notebook.add(gui_frame, text="🎨 GUI Editor")
        self._setup_gui_editor_tab(gui_frame)
        
        ttk.Label(parent, text="💡 Double-click to add to PyTML | Right-click for type info", foreground='gray').pack()
    
    def _setup_gui_editor_tab(self, parent):
        """Setup the GUI Editor configuration tab"""
        # Graphics detection info
        info_frame = ttk.LabelFrame(parent, text="📊 Graphics Detection")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.graphics_info_text = tk.Text(info_frame, height=4, bg='#1e1e1e', fg='#d4d4d4', 
                                          font=('Consolas', 9))
        self.graphics_info_text.pack(fill=tk.X, padx=5, pady=5)
        self.graphics_info_text.insert('1.0', "Select a module to analyze graphical capabilities...")
        self.graphics_info_text.config(state='disabled')
        
        # GUI Element Type selector
        type_frame = ttk.LabelFrame(parent, text="🔧 GUI Element Configuration")
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Element type
        row1 = ttk.Frame(type_frame)
        row1.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row1, text="Element Type:", width=15).pack(side=tk.LEFT)
        self.gui_type_var = tk.StringVar(value='widget')
        type_combo = ttk.Combobox(row1, textvariable=self.gui_type_var, 
                                   values=['container', 'widget', 'graphic', 'surface', 'console'],
                                   state='readonly', width=20)
        type_combo.pack(side=tk.LEFT, padx=5)
        type_combo.bind('<<ComboboxSelected>>', self._on_gui_type_change)
        
        self.gui_type_desc = ttk.Label(row1, text="", foreground='gray')
        self.gui_type_desc.pack(side=tk.LEFT, padx=10)
        
        # Framework
        row2 = ttk.Frame(type_frame)
        row2.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row2, text="Framework:", width=15).pack(side=tk.LEFT)
        self.gui_framework_var = tk.StringVar(value='tkinter')
        framework_combo = ttk.Combobox(row2, textvariable=self.gui_framework_var,
                                        values=['tkinter', 'matplotlib', 'pygame', 'pillow', 
                                                'turtle', 'canvas', 'opencv', 'opengl', 
                                                'curses', 'rich', 'qt', 'kivy', 'custom'],
                                        width=20)
        framework_combo.pack(side=tk.LEFT, padx=5)
        
        # Display name
        row3 = ttk.Frame(type_frame)
        row3.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row3, text="Display Name:", width=15).pack(side=tk.LEFT)
        self.gui_display_name = ttk.Entry(row3, width=25)
        self.gui_display_name.pack(side=tk.LEFT, padx=5)
        self.gui_display_name.insert(0, "My Widget")
        
        # Icon
        ttk.Label(row3, text="Icon:").pack(side=tk.LEFT, padx=(10, 5))
        self.gui_icon_var = tk.StringVar(value='🔘')
        icon_combo = ttk.Combobox(row3, textvariable=self.gui_icon_var,
                                   values=['🪟', '📦', '🔘', '📝', '✏️', '🎨', '📊', '📈', 
                                           '🖼️', '🎮', '👾', '🐢', '📷', '💻', '🎲', '🎬'],
                                   width=5)
        icon_combo.pack(side=tk.LEFT)
        
        # Default size
        row4 = ttk.Frame(type_frame)
        row4.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row4, text="Default Size:", width=15).pack(side=tk.LEFT)
        self.gui_width_var = tk.StringVar(value='100')
        ttk.Entry(row4, textvariable=self.gui_width_var, width=8).pack(side=tk.LEFT)
        ttk.Label(row4, text=" x ").pack(side=tk.LEFT)
        self.gui_height_var = tk.StringVar(value='30')
        ttk.Entry(row4, textvariable=self.gui_height_var, width=8).pack(side=tk.LEFT)
        ttk.Label(row4, text=" pixels").pack(side=tk.LEFT, padx=5)
        
        # Embed method
        row5 = ttk.Frame(type_frame)
        row5.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row5, text="Embed Method:", width=15).pack(side=tk.LEFT)
        self.gui_embed_var = tk.StringVar(value='native')
        embed_combo = ttk.Combobox(row5, textvariable=self.gui_embed_var,
                                    values=['native', 'canvas', 'embed', 'webview', 'console', 'separate'],
                                    state='readonly', width=20)
        embed_combo.pack(side=tk.LEFT, padx=5)
        
        embed_help = ttk.Label(row5, text="", foreground='gray')
        embed_help.pack(side=tk.LEFT, padx=5)
        self.embed_help_label = embed_help
        
        # Display target
        row6 = ttk.Frame(type_frame)
        row6.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row6, text="Display:", width=15).pack(side=tk.LEFT)
        self.gui_display_var = tk.StringVar(value='window')
        display_combo = ttk.Combobox(row6, textvariable=self.gui_display_var,
                                      values=['window', 'console', 'browser', 'separate'],
                                      state='readonly', width=20)
        display_combo.pack(side=tk.LEFT, padx=5)
        
        # Installed graphical packages info
        packages_frame = ttk.LabelFrame(parent, text="📦 Installed Graphical Packages")
        packages_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.packages_tree = ttk.Treeview(packages_frame, 
                                           columns=('framework', 'type', 'description'),
                                           show='tree headings', height=6)
        self.packages_tree.heading('#0', text='Package')
        self.packages_tree.heading('framework', text='Framework')
        self.packages_tree.heading('type', text='Type')
        self.packages_tree.heading('description', text='Description')
        self.packages_tree.column('#0', width=100)
        self.packages_tree.column('framework', width=80)
        self.packages_tree.column('type', width=60)
        self.packages_tree.column('description', width=200)
        
        pkg_scroll = ttk.Scrollbar(packages_frame, command=self.packages_tree.yview)
        self.packages_tree.configure(yscrollcommand=pkg_scroll.set)
        self.packages_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pkg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load installed packages
        self._load_installed_packages()
        
        # Update type description
        self._on_gui_type_change()
    
    def _load_installed_packages(self):
        """Load list of installed graphical packages using GUIDetector"""
        self.packages_tree.delete(*self.packages_tree.get_children())
        
        installed = self.gui_detector.get_installed_graphical_packages()
        for pkg in installed:
            icon = pkg.get('icon', '📦')
            self.packages_tree.insert('', tk.END, 
                                      text=f"{icon} {pkg['name']}",
                                      values=(pkg['framework'], pkg['type'], pkg['description']))
    
    def _on_gui_type_change(self, event=None):
        """Update description when GUI type changes"""
        gtype = self.gui_type_var.get()
        type_info = GUI_ELEMENT_TYPES.get(gtype, {})
        
        icon = type_info.get('icon', '❓')
        desc = type_info.get('description', '')
        self.gui_type_desc.config(text=f"{icon} {desc}")
        
        # Auto-set embed method based on type
        if gtype == 'container':
            self.gui_embed_var.set('native')
            self.gui_width_var.set('300')
            self.gui_height_var.set('200')
        elif gtype == 'widget':
            self.gui_embed_var.set('native')
            self.gui_width_var.set('100')
            self.gui_height_var.set('30')
        elif gtype == 'graphic':
            self.gui_embed_var.set('canvas')
            self.gui_width_var.set('400')
            self.gui_height_var.set('300')
        elif gtype == 'surface':
            self.gui_embed_var.set('embed')
            self.gui_width_var.set('640')
            self.gui_height_var.set('480')
        elif gtype == 'console':
            self.gui_embed_var.set('console')
            self.gui_display_var.set('console')
    
    def _update_graphics_detection(self, module_name, class_name=None):
        """Update graphics detection info for current module/class using GUIDetector"""
        # Use the new GUIDetector for analysis
        if class_name and hasattr(self, 'classes_data') and class_name in self.classes_data:
            cls = self.classes_data[class_name]
            info = self.gui_detector.detect_class(cls)
            # Also get module-level info for framework detection
            module_info = self.gui_detector.quick_check(module_name)
        else:
            # Just module-level detection
            module_info = self.gui_detector.detect_module(module_name)
            info = {
                'is_graphical': module_info.get('is_graphical_package', False) or module_info.get('total_graphical', 0) > 0,
                'confidence': 1000 if module_info.get('is_graphical_package') else module_info.get('total_graphical', 0) * 100,
                'element_type': module_info.get('package_info', {}).get('type', 'widget'),
                'property_types_found': list(module_info.get('property_types_summary', {}).keys())
            }
            module_info = module_info.get('package_info', {})
        
        self.graphics_info_text.config(state='normal')
        self.graphics_info_text.delete('1.0', tk.END)
        
        if info.get('is_graphical', False):
            icon = module_info.get('icon', '🎨')
            text = f"{icon} GRAPHICAL ELEMENT DETECTED\n"
            text += f"Framework: {module_info.get('framework', 'unknown')}  |  "
            text += f"Type: {info.get('element_type', 'unknown')}  |  "
            text += f"Embed: {module_info.get('embed_method', 'native')}\n"
            text += f"Confidence: {info.get('confidence', 0)}%  |  "
            text += f"Display: {module_info.get('display', 'window')}\n"
            
            # Show property types detected
            prop_types = info.get('property_types_found', [])
            if prop_types:
                text += f"Property Types: {', '.join(prop_types)}"
            
            self.graphics_info_text.insert('1.0', text)
            
            # Auto-fill GUI config
            if info.get('element_type'):
                self.gui_type_var.set(info['element_type'])
            if module_info.get('framework'):
                self.gui_framework_var.set(module_info['framework'])
            if module_info.get('icon'):
                self.gui_icon_var.set(module_info['icon'])
            if module_info.get('embed_method'):
                self.gui_embed_var.set(module_info['embed_method'])
            if module_info.get('display'):
                self.gui_display_var.set(module_info['display'])
        else:
            self.graphics_info_text.insert('1.0', "❓ Not detected as graphical\n")
            self.graphics_info_text.insert(tk.END, "This module/class may not have visual elements,\n")
            self.graphics_info_text.insert(tk.END, "or it uses an unknown graphics framework.\n\n")
            self.graphics_info_text.insert(tk.END, "Hint: Elements with Color properties are usually graphical.")
        
        self.graphics_info_text.config(state='disabled')

    def _setup_selected(self, parent):
        """Panel with selected PyTML members"""
        ttk.Label(parent, text="PyTML Mapping", font=('Arial', 11, 'bold')).pack()
        
        name_frame = ttk.Frame(parent)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Tag:").pack(side=tk.LEFT)
        self.tag_name_entry = ttk.Entry(name_frame)
        self.tag_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.tag_name_entry.insert(0, "mytag")
        
        ttk.Label(parent, text="Selected Properties/Methods:").pack(anchor=tk.W)
        
        sel_frame = ttk.Frame(parent)
        sel_frame.pack(fill=tk.BOTH, expand=True)
        
        self.selected_tree = ttk.Treeview(sel_frame, columns=('python', 'datatype', 'kind'), show='tree headings')
        self.selected_tree.heading('#0', text='PyTML Name')
        self.selected_tree.heading('python', text='Python')
        self.selected_tree.heading('datatype', text='DataType')
        self.selected_tree.heading('kind', text='Kind')
        self.selected_tree.column('#0', width=100)
        self.selected_tree.column('python', width=100)
        self.selected_tree.column('datatype', width=80)
        self.selected_tree.column('kind', width=60)
        sel_scroll = ttk.Scrollbar(sel_frame, command=self.selected_tree.yview)
        self.selected_tree.configure(yscrollcommand=sel_scroll.set)
        self.selected_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sel_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Remove", command=self._remove_selected).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Clear all", command=self._clear_selected).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(parent, text="Preview:").pack(anchor=tk.W, pady=(10,0))
        self.preview_text = tk.Text(parent, height=10, bg='#f5f5f5')
        self.preview_text.pack(fill=tk.BOTH, expand=True)
    
    def _load_modules(self):
        self.all_modules = self.scanner.get_all_modules()
        self._update_module_list(self.all_modules)
        self.status_var.set(f"Found {len(self.all_modules)} modules")
    
    def _update_module_list(self, modules):
        self.module_list.delete(0, tk.END)
        for mod in modules:
            self.module_list.insert(tk.END, mod)
    
    def _filter_modules(self, event=None):
        query = self.module_search.get().lower()
        filtered = [m for m in self.all_modules if query in m.lower()] if query else self.all_modules
        self._update_module_list(filtered)
    
    def _on_module_select(self, event):
        sel = self.module_list.curselection()
        if not sel:
            return
        
        module_name = self.module_list.get(sel[0])
        self.current_module_name = module_name  # Store for later use
        self.status_var.set(f"Scanning {module_name}...")
        self.root.update()
        
        classes = self.scanner.get_module_classes(module_name)
        
        self.class_list.delete(0, tk.END)
        for name, cls in classes:
            self.class_list.insert(tk.END, name)
        
        self.classes_data = {name: cls for name, cls in classes}
        self.status_var.set(f"Found {len(classes)} classes in {module_name}")
        
        # Update graphics detection for this module
        self._update_graphics_detection(module_name)
    
    def _on_class_select(self, event):
        sel = self.class_list.curselection()
        if not sel:
            return
        
        class_name = self.class_list.get(sel[0])
        if class_name not in self.classes_data:
            return
        
        cls = self.classes_data[class_name]
        self.current_class = cls
        self.current_class_name = class_name
        
        self.status_var.set(f"Scanning {class_name}...")
        self.root.update()
        
        members = self.scanner.get_class_members(cls)
        
        # Store config data for later use
        self.config_data = {}
        
        self.config_tree.delete(*self.config_tree.get_children())
        for opt in members['config_options']:
            datatype = opt.get('datatype', 'Unknown')
            icon = PYTML_DATATYPES.get(datatype, {}).get('icon', '❓')
            type_display = f"{icon} {datatype}"
            self.config_tree.insert('', tk.END, text=opt['name'], 
                                   values=(type_display, opt['current'], ''))
            self.config_data[opt['name']] = opt
        
        self.method_tree.delete(*self.method_tree.get_children())
        for m in members['methods']:
            self.method_tree.insert('', tk.END, text=m['name'], values=(m['signature'], ''))
        
        self.prop_tree.delete(*self.prop_tree.get_children())
        for p in members['properties']:
            self.prop_tree.insert('', tk.END, text=p['name'], values=(p['type'], ''))
        
        self.tag_name_entry.delete(0, tk.END)
        self.tag_name_entry.insert(0, class_name.lower())
        
        self.status_var.set(f"{class_name}: {len(members['config_options'])} config, {len(members['methods'])} methods")
        
        # Update graphics detection for this specific class
        module_name = getattr(self, 'current_module_name', None)
        if module_name:
            self._update_graphics_detection(module_name, class_name)
    
    def _show_datatype_info(self, event):
        """Show datatype info on right-click"""
        item = self.config_tree.identify_row(event.y)
        if not item:
            return
        
        option_name = self.config_tree.item(item, 'text')
        opt = self.config_data.get(option_name, {})
        datatype = opt.get('datatype', 'Unknown')
        type_info = PYTML_DATATYPES.get(datatype, PYTML_DATATYPES['Unknown'])
        
        # Create popup menu
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"{type_info['icon']} {datatype}", state='disabled')
        menu.add_separator()
        menu.add_command(label=type_info['description'], state='disabled')
        if type_info['examples']:
            menu.add_separator()
            menu.add_command(label="Examples:", state='disabled')
            for ex in type_info['examples'][:3]:
                menu.add_command(label=f"  • {ex}", state='disabled')
        
        menu.tk_popup(event.x_root, event.y_root)
    
    def _add_config_to_pytml(self, event):
        item = self.config_tree.selection()
        if not item:
            return
        
        python_name = self.config_tree.item(item[0], 'text')
        opt = self.config_data.get(python_name, {})
        datatype = opt.get('datatype', 'Unknown')
        
        pytml_name = simpledialog.askstring("PyTML Name", 
            f"Enter PyTML name for '{python_name}' ({datatype}):", initialvalue=python_name)
        
        if pytml_name:
            self._add_to_selected(pytml_name, python_name, 'config', datatype)
            self.config_tree.set(item[0], 'pytml_name', pytml_name)
    
    def _add_method_to_pytml(self, event):
        item = self.method_tree.selection()
        if not item:
            return
        
        python_name = self.method_tree.item(item[0], 'text')
        pytml_name = simpledialog.askstring("PyTML Name",
            f"Enter PyTML name for '{python_name}':", initialvalue=python_name)
        
        if pytml_name:
            self._add_to_selected(pytml_name, python_name, 'method', 'Callback')
            self.method_tree.set(item[0], 'pytml_name', pytml_name)
    
    def _add_prop_to_pytml(self, event):
        item = self.prop_tree.selection()
        if not item:
            return
        
        python_name = self.prop_tree.item(item[0], 'text')
        pytml_name = simpledialog.askstring("PyTML Name",
            f"Enter PyTML name for '{python_name}':", initialvalue=python_name)
        
        if pytml_name:
            self._add_to_selected(pytml_name, python_name, 'property', 'Unknown')
            self.prop_tree.set(item[0], 'pytml_name', pytml_name)
    
    def _add_to_selected(self, pytml_name, python_name, member_type, datatype='Unknown'):
        for item in self.selected_tree.get_children():
            if self.selected_tree.item(item, 'text') == pytml_name:
                return
        
        icon = PYTML_DATATYPES.get(datatype, {}).get('icon', '❓')
        type_display = f"{icon} {datatype}"
        
        self.selected_tree.insert('', tk.END, text=pytml_name, values=(python_name, type_display, member_type))
        self.selected_members.append({
            'pytml': pytml_name, 
            'python': python_name, 
            'type': member_type,
            'datatype': datatype
        })
        self._update_preview()
    
    def _remove_selected(self):
        item = self.selected_tree.selection()
        if item:
            pytml_name = self.selected_tree.item(item[0], 'text')
            self.selected_tree.delete(item[0])
            self.selected_members = [m for m in self.selected_members if m['pytml'] != pytml_name]
            self._update_preview()
    
    def _clear_selected(self):
        self.selected_tree.delete(*self.selected_tree.get_children())
        self.selected_members = []
        self._update_preview()
    
    def _update_preview(self):
        tag = self.tag_name_entry.get() or "mytag"
        configs = [m for m in self.selected_members if m['type'] == 'config']
        methods = [m for m in self.selected_members if m['type'] == 'method']
        
        preview = f"<!-- Create {tag} -->\n<{tag} name=\"{tag}1\""
        for c in configs[:3]:
            # Show example based on datatype
            datatype = c.get('datatype', 'Unknown')
            examples = PYTML_DATATYPES.get(datatype, {}).get('examples', ['...'])
            example = examples[0] if examples else '...'
            preview += f' {c["pytml"]}="{example}"'
        preview += ">\n\n<!-- Actions -->\n"
        for m in methods[:3]:
            preview += f"<{tag}1_{m['pytml']}>\n"
        preview += f"\n<!-- Set property -->\n"
        for c in configs[:2]:
            datatype = c.get('datatype', 'Unknown')
            examples = PYTML_DATATYPES.get(datatype, {}).get('examples', ['value'])
            example = examples[0] if examples else 'value'
            preview += f'<{tag}1_{c["pytml"]}="{example}">\n'
        
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', preview)
    
    def _edit_existing(self):
        libs_dir = os.path.join(os.path.dirname(__file__), 'libs')
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Lib to Edit")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Existing Libs:", font=('Arial', 11, 'bold')).pack(pady=5)
        
        # List of libs
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        lib_list = tk.Listbox(list_frame, font=('Consolas', 10))
        lib_scroll = ttk.Scrollbar(list_frame, command=lib_list.yview)
        lib_list.configure(yscrollcommand=lib_scroll.set)
        lib_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lib_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Info panel
        info_frame = ttk.LabelFrame(dialog, text="Lib Info")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        info_text = tk.Text(info_frame, height=8, bg='#f5f5f5', font=('Consolas', 9))
        info_text.pack(fill=tk.X, padx=5, pady=5)
        
        libs_info = {}
        
        for f in os.listdir(libs_dir):
            if f.endswith('.py') and not f.startswith('_'):
                lib_name = f[:-3]
                lib_list.insert(tk.END, lib_name)
                # Parse lib info
                libs_info[lib_name] = self._parse_lib_file(os.path.join(libs_dir, f))
        
        def on_select(event):
            sel = lib_list.curselection()
            if not sel:
                return
            lib_name = lib_list.get(sel[0])
            info = libs_info.get(lib_name, {})
            
            info_text.delete('1.0', tk.END)
            info_text.insert(tk.END, f"Lib: {lib_name}\n")
            info_text.insert(tk.END, f"Base class: {info.get('base_class', 'unknown')}\n")
            info_text.insert(tk.END, f"\nExisting properties ({len(info.get('properties', []))}):\n")
            for prop in info.get('properties', [])[:10]:
                info_text.insert(tk.END, f"  • {prop}\n")
            if len(info.get('properties', [])) > 10:
                info_text.insert(tk.END, f"  ... and {len(info.get('properties', [])) - 10} more\n")
        
        lib_list.bind('<<ListboxSelect>>', on_select)
        
        def select():
            sel = lib_list.curselection()
            if sel:
                lib_name = lib_list.get(sel[0])
                dialog.destroy()
                self._load_lib(lib_name, libs_info.get(lib_name, {}))
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Open and Edit", command=select).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _parse_lib_file(self, filepath):
        """Parse an existing lib file to find properties and base class"""
        info = {
            'properties': [],
            'methods': [],
            'base_class': None,
            'tk_widget_type': None,
            'existing_code': ''
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                info['existing_code'] = content
            
            import re
            
            # Find base class (tkinter widget type)
            # Look for patterns like: tk.Button, ttk.Button, tk.Label etc.
            tk_match = re.search(r'(?:tk|ttk)\.(\w+)\s*\(', content)
            if tk_match:
                info['tk_widget_type'] = tk_match.group(1)
                info['base_class'] = tk_match.group(1)
            
            # Find properties from __init__ parameters
            init_match = re.search(r'def __init__\s*\([^)]+\):', content)
            if init_match:
                params = re.findall(r'self\.(\w+)\s*=', content[:content.find('def create') if 'def create' in content else len(content)])
                info['properties'].extend(params)
            
            # Find properties from _properties dict
            props_match = re.search(r'_properties\s*=\s*\{([^}]+)\}', content, re.DOTALL)
            if props_match:
                prop_names = re.findall(r"'(\w+)':", props_match.group(1))
                for name in prop_names:
                    if name not in info['properties']:
                        info['properties'].append(name)
            
            # Find set_ methods
            set_methods = re.findall(r'def (set_\w+)\s*\(', content)
            info['methods'].extend(set_methods)
            
            # Find CONFIG_MAP if it exists
            config_match = re.search(r'CONFIG_MAP\s*=\s*\{([^}]+)\}', content, re.DOTALL)
            if config_match:
                config_items = re.findall(r"'(\w+)':\s*'(\w+)'", config_match.group(1))
                info['config_map'] = {pytml: python for pytml, python in config_items}
            
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
        
        return info
    
    def _load_lib(self, lib_name, lib_info=None):
        """Load an existing lib and show its properties"""
        self.tag_name_entry.delete(0, tk.END)
        self.tag_name_entry.insert(0, lib_name)
        
        # Clear existing selected
        self._clear_selected()
        
        if lib_info:
            # Show existing properties as already selected
            for prop in lib_info.get('properties', []):
                if prop not in ['name', 'parent', '_tk_button', '_tk_label', '_tk_widget', 
                               '_ready', '_context', '_click_handler', 'parent_window']:
                    self._add_to_selected(prop, prop, 'config')
            
            # Set base class
            base = lib_info.get('tk_widget_type', 'Button')
            self.current_class_name = base
            
            # Try to load tkinter class
            try:
                if hasattr(tk, base):
                    self.current_class = getattr(tk, base)
                elif hasattr(ttk, base):
                    self.current_class = getattr(ttk, base)
                else:
                    self.current_class = tk.Button
                
                # Show all tkinter options so you can add new ones
                members = self.scanner.get_class_members(self.current_class)
                
                self.config_tree.delete(*self.config_tree.get_children())
                existing_props = set(lib_info.get('properties', []))
                config_map = lib_info.get('config_map', {})
                
                for opt in members['config_options']:
                    # Mark if already added
                    pytml_name = ''
                    for pytml, python in config_map.items():
                        if python == opt['name']:
                            pytml_name = pytml
                            break
                    
                    tag = '✓ ' if opt['name'] in existing_props or pytml_name else ''
                    self.config_tree.insert('', tk.END, text=tag + opt['name'], 
                                          values=(opt['current'], pytml_name))
                
                self.method_tree.delete(*self.method_tree.get_children())
                for m in members['methods']:
                    self.method_tree.insert('', tk.END, text=m['name'], values=(m['signature'], ''))
                
                self.status_var.set(f"Editing: {lib_name} (based on tk.{base}) - {len(existing_props)} properties")
                
            except Exception as e:
                self.status_var.set(f"Editing: {lib_name} - could not load tkinter class: {e}")
        else:
            self.status_var.set(f"Editing: {lib_name}")
    
    def _save_lib(self):
        tag_name = self.tag_name_entry.get()
        if not tag_name:
            messagebox.showerror("Error", "Please enter a tag name")
            return
        
        libs_dir = os.path.join(os.path.dirname(__file__), 'libs')
        filepath = os.path.join(libs_dir, f"{tag_name}.py")
        
        if os.path.exists(filepath):
            # Existing lib - offer to add new properties
            choice = messagebox.askyesnocancel(
                "Existing Lib",
                f"{tag_name}.py already exists.\n\n"
                "Yes = Add only NEW properties\n"
                "No = Overwrite entire file\n"
                "Cancel = Abort"
            )
            
            if choice is None:  # Cancel
                return
            elif choice:  # Yes - add new
                self._add_properties_to_existing(filepath, tag_name)
                return
            # No - continue with overwrite
        
        if not self.current_class:
            messagebox.showerror("Error", "Please select a class first")
            return
        
        code = self._generate_lib_code(tag_name)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        messagebox.showinfo("Saved", f"Lib saved: {filepath}")
    
    def _add_properties_to_existing(self, filepath, tag_name):
        """Add new properties and methods to an existing lib file"""
        import re
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find existing properties and methods
        lib_info = self._parse_lib_file(filepath)
        existing_props = set(lib_info.get('properties', []))
        existing_config_map = lib_info.get('config_map', {})
        existing_methods = set(lib_info.get('methods', []))
        
        # Find new configs (not already in file)
        new_configs = []
        for m in self.selected_members:
            if m['type'] == 'config':
                if m['pytml'] not in existing_props and m['pytml'] not in existing_config_map:
                    new_configs.append(m)
        
        # Find new methods (not already in file)
        new_methods_list = []
        for m in self.selected_members:
            if m['type'] == 'method':
                method_name = f"set_{m['pytml']}" if not m['pytml'].startswith('set_') else m['pytml']
                if method_name not in existing_methods and m['pytml'] not in existing_methods:
                    new_methods_list.append(m)
        
        if not new_configs and not new_methods_list:
            messagebox.showinfo("Info", "No new properties or methods to add!")
            return
        
        # Create backup
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        try:
            # Add to CONFIG_MAP if it exists
            if 'CONFIG_MAP' in content:
                config_map_match = re.search(r'(CONFIG_MAP\s*=\s*\{)([^}]*)(})', content, re.DOTALL)
                if config_map_match:
                    existing_map = config_map_match.group(2)
                    new_map_entries = '\n'.join([f"    '{c['pytml']}': '{c['python']}'," for c in new_configs])
                    new_map = config_map_match.group(1) + existing_map.rstrip() + '\n' + new_map_entries + '\n' + config_map_match.group(3)
                    content = content[:config_map_match.start()] + new_map + content[config_map_match.end():]
            
            # Add to __init__ kwargs
            init_match = re.search(r'(def __init__\s*\(self,\s*name[^)]*\):)', content)
            if init_match:
                # Find where kwargs are used
                kwargs_section = re.search(r'(self\.x\s*=\s*kwargs\.get.*?\n)', content)
                if kwargs_section:
                    new_init_lines = '\n'.join([f"        self.{c['pytml']} = kwargs.get('{c['pytml']}', '')" for c in new_configs])
                    insert_pos = kwargs_section.end()
                    content = content[:insert_pos] + new_init_lines + '\n' + content[insert_pos:]
            
            # Add set_ methods for new properties
            # Find last method in class
            class_end = content.rfind('\nclass ')
            if class_end == -1:
                class_end = len(content)
            
            # Find a good place to insert (after last set_ method or before class)
            last_set_method = -1
            for match in re.finditer(r'def set_\w+\([^)]+\):[^}]+?return self', content):
                last_set_method = match.end()
            
            if last_set_method > 0:
                new_methods_code = '\n'
                # Add set_ methods for new config properties
                for c in new_configs:
                    widget_var = f"_tk_{tag_name}" if tag_name in ['button', 'label', 'entry', 'window'] else '_tk_widget'
                    tk_prop = c['python']
                    new_methods_code += f'''
    def set_{c['pytml']}(self, value):
        """Set {c['pytml']}"""
        self.{c['pytml']} = value
        if self.{widget_var}:
            self.{widget_var}.configure({tk_prop}=value)
        return self
'''
                # Add wrapper methods for new methods (e.g. exit -> destroy)
                for m in new_methods_list:
                    widget_var = f"_tk_{tag_name}" if tag_name in ['button', 'label', 'entry', 'window'] else '_tk_widget'
                    python_method = m['python']
                    new_methods_code += f'''
    def {m['pytml']}(self):
        """Call {m['python']}"""
        if self.{widget_var}:
            self.{widget_var}.{python_method}()
        return self
'''
                content = content[:last_set_method] + new_methods_code + content[last_set_method:]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Remove backup
            os.remove(backup_path)
            
            # Build message
            msg_parts = []
            if new_configs:
                msg_parts.append(f"{len(new_configs)} properties:\n" + 
                    '\n'.join([f"  • {c['pytml']} → {c['python']}" for c in new_configs]))
            if new_methods_list:
                msg_parts.append(f"{len(new_methods_list)} methods:\n" + 
                    '\n'.join([f"  • {m['pytml']}() → {m['python']}()" for m in new_methods_list]))
            
            messagebox.showinfo("Saved", 
                f"Added to {tag_name}.py:\n\n" + '\n\n'.join(msg_parts))
            
        except Exception as e:
            # Restore backup on error
            if os.path.exists(backup_path):
                with open(backup_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(original)
                os.remove(backup_path)
            messagebox.showerror("Error", f"Could not update lib: {e}")
    
    def _generate_lib_code(self, tag_name):
        class_name = tag_name.capitalize()
        base_class = self.current_class_name if self.current_class_name else 'Frame'
        module_name = getattr(self, 'current_module_name', 'tkinter')
        
        configs = [m for m in self.selected_members if m['type'] == 'config']
        methods = [m for m in self.selected_members if m['type'] == 'method']
        
        config_map = "\n".join([f"    '{c['pytml']}': '{c['python']}'," for c in configs])
        props_code = "\n".join([f"        '{c['pytml']}': PropertyDescriptor('{c['pytml']}', str, default='')," for c in configs])
        
        # Get GUI info from the GUI Editor tab
        gui_type = self.gui_type_var.get() if hasattr(self, 'gui_type_var') else 'widget'
        gui_framework = self.gui_framework_var.get() if hasattr(self, 'gui_framework_var') else 'tkinter'
        gui_icon = self.gui_icon_var.get() if hasattr(self, 'gui_icon_var') else '🔲'
        gui_display = self.gui_display_name.get() if hasattr(self, 'gui_display_name') else class_name
        gui_embed = self.gui_embed_var.get() if hasattr(self, 'gui_embed_var') else 'native'
        gui_width = self.gui_width_var.get() if hasattr(self, 'gui_width_var') else '100'
        gui_height = self.gui_height_var.get() if hasattr(self, 'gui_height_var') else '30'
        
        # Build the get_gui_info function
        gui_info_code = f'''
def get_gui_info():
    """Return GUI metadata for the PyTML GUI Editor"""
    return {{
        'type': '{gui_type}',
        'framework': '{gui_framework}',
        'icon': '{gui_icon}',
        'display_name': '{gui_display}',
        'embed_method': '{gui_embed}',
        'default_size': ({gui_width}, {gui_height}),
        'is_graphical': True,
        'properties': [
{chr(10).join([f"            {{'name': '{c['pytml']}', 'type': 'str', 'default': ''}}," for c in configs])}
        ]
    }}
'''
        
        # Generate code based on framework type
        if gui_framework == 'turtle' or module_name == 'turtle':
            return self._generate_turtle_code(tag_name, class_name, base_class, configs, methods, gui_info_code)
        elif gui_framework == 'matplotlib' or 'matplotlib' in module_name:
            return self._generate_matplotlib_code(tag_name, class_name, base_class, configs, methods, gui_info_code)
        elif gui_framework == 'pygame' or module_name == 'pygame':
            return self._generate_pygame_code(tag_name, class_name, base_class, configs, methods, gui_info_code)
        else:
            # Default tkinter template
            return self._generate_tkinter_code(tag_name, class_name, base_class, config_map, props_code, gui_info_code)
    
    def _generate_tkinter_code(self, tag_name, class_name, base_class, config_map, props_code, gui_info_code):
        """Generate code for tkinter widgets"""
        return f'''"""
PyTML {class_name} Module - Auto-generated by LibEditor
Based on: tkinter.{base_class}
"""

import tkinter as tk
from tkinter import ttk
from libs.core import ActionNode, WidgetNode, PropertyDescriptor, resolve_attributes

CONFIG_MAP = {{
{config_map}
}}

class {class_name}:
    def __init__(self, name, **kwargs):
        self.name = name
        self._tk_widget = None
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self._config = kwargs
    
    def create(self, parent_window, context=None):
        tk_win = parent_window.get_tk_window()
        if tk_win:
            tk_config = {{CONFIG_MAP.get(k, k): v for k, v in self._config.items() if k in CONFIG_MAP}}
            self._tk_widget = tk.{base_class}(tk_win, **tk_config)
            self._tk_widget.place(x=self.x, y=self.y)
        return self
    
    def configure(self, **kwargs):
        if self._tk_widget:
            tk_config = {{CONFIG_MAP.get(k, k): v for k, v in kwargs.items()}}
            self._tk_widget.configure(**tk_config)

class {class_name}Node(WidgetNode):
    tag_name = '{tag_name}'
    _properties = {{
        'name': PropertyDescriptor('name', str, required=True),
        'parent': PropertyDescriptor('parent', str),
        'x': PropertyDescriptor('x', int, default=0),
        'y': PropertyDescriptor('y', int, default=0),
{props_code}
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        name = resolved.get('name')
        if name:
            if '{tag_name}s' not in context:
                context['{tag_name}s'] = {{}}
            widget = {class_name}(name, **resolved)
            context['{tag_name}s'][name] = widget
            parent_name = resolved.get('parent')
            if parent_name and 'windows' in context:
                parent = context['windows'].get(parent_name)
                if parent:
                    widget.create(parent, context)
        self._ready = True

def get_line_parsers():
    import re
    def parse_{tag_name}(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child({class_name}Node('{tag_name}', attrs))
        return None
    return [(r'<{tag_name}\\s+(.+)>$', parse_{tag_name})]
{gui_info_code}'''
    
    def _generate_turtle_code(self, tag_name, class_name, base_class, configs, methods, gui_info_code):
        """Generate code for turtle graphics"""
        props_code = "\n".join([f"        '{c['pytml']}': PropertyDescriptor('{c['pytml']}', str, default='')," for c in configs])
        
        # Extract method names for turtle commands
        method_names = [m['python'] for m in methods]
        method_map = "\n".join([f"    '{m['pytml']}': '{m['python']}'," for m in methods])
        
        return f'''"""
PyTML {class_name} Module - Auto-generated by LibEditor
Turtle Graphics Canvas for PyTML
Based on: turtle.{base_class}
"""

import tkinter as tk
import turtle
from libs.core import ActionNode, WidgetNode, PropertyDescriptor, resolve_attributes

class {class_name}:
    """Turtle graphics canvas that can be embedded in a PyTML window"""
    
    def __init__(self, name, **kwargs):
        self.name = name
        self._canvas = None
        self._screen = None
        self._turtle = None
        self.width = int(kwargs.get('width', 400))
        self.height = int(kwargs.get('height', 300))
        self.x = int(kwargs.get('x', 0))
        self.y = int(kwargs.get('y', 0))
        self.bgcolor = kwargs.get('bgcolor', 'white')
        self._config = kwargs
    
    def create(self, parent_window, context=None):
        """Create turtle canvas embedded in parent window"""
        tk_win = parent_window.get_tk_window()
        if tk_win:
            # Create a canvas widget for turtle
            self._canvas = tk.Canvas(tk_win, width=self.width, height=self.height, 
                                     bg=self.bgcolor, highlightthickness=0)
            self._canvas.place(x=self.x, y=self.y)
            
            # Create turtle screen on this canvas
            self._screen = turtle.TurtleScreen(self._canvas)
            self._screen.bgcolor(self.bgcolor)
            
            # Create default turtle
            self._turtle = turtle.RawTurtle(self._screen)
            self._turtle.speed(0)  # Fastest
            
        return self
    
    def get_turtle(self):
        """Get the turtle for drawing commands"""
        return self._turtle
    
    def get_screen(self):
        """Get the turtle screen"""
        return self._screen
    
    def get_canvas(self):
        """Get the underlying tk canvas"""
        return self._canvas
    
    # Turtle drawing methods
    def forward(self, distance):
        if self._turtle:
            self._turtle.forward(float(distance))
    
    def backward(self, distance):
        if self._turtle:
            self._turtle.backward(float(distance))
    
    def right(self, angle):
        if self._turtle:
            self._turtle.right(float(angle))
    
    def left(self, angle):
        if self._turtle:
            self._turtle.left(float(angle))
    
    def goto(self, x, y):
        if self._turtle:
            self._turtle.goto(float(x), float(y))
    
    def penup(self):
        if self._turtle:
            self._turtle.penup()
    
    def pendown(self):
        if self._turtle:
            self._turtle.pendown()
    
    def pencolor(self, color):
        if self._turtle:
            self._turtle.pencolor(color)
    
    def fillcolor(self, color):
        if self._turtle:
            self._turtle.fillcolor(color)
    
    def begin_fill(self):
        if self._turtle:
            self._turtle.begin_fill()
    
    def end_fill(self):
        if self._turtle:
            self._turtle.end_fill()
    
    def circle(self, radius):
        if self._turtle:
            self._turtle.circle(float(radius))
    
    def clear(self):
        if self._turtle:
            self._turtle.clear()
    
    def reset(self):
        if self._turtle:
            self._turtle.reset()
    
    def home(self):
        if self._turtle:
            self._turtle.home()
    
    def hideturtle(self):
        if self._turtle:
            self._turtle.hideturtle()
    
    def showturtle(self):
        if self._turtle:
            self._turtle.showturtle()
    
    def pensize(self, width):
        if self._turtle:
            self._turtle.pensize(float(width))
    
    def speed(self, speed):
        if self._turtle:
            self._turtle.speed(int(speed))


class {class_name}Node(WidgetNode):
    tag_name = '{tag_name}'
    _properties = {{
        'name': PropertyDescriptor('name', str, required=True),
        'parent': PropertyDescriptor('parent', str),
        'x': PropertyDescriptor('x', int, default=0),
        'y': PropertyDescriptor('y', int, default=0),
        'width': PropertyDescriptor('width', int, default=400),
        'height': PropertyDescriptor('height', int, default=300),
        'bgcolor': PropertyDescriptor('bgcolor', str, default='white'),
{props_code}
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        name = resolved.get('name')
        if name:
            if '{tag_name}s' not in context:
                context['{tag_name}s'] = {{}}
            canvas = {class_name}(name, **resolved)
            context['{tag_name}s'][name] = canvas
            parent_name = resolved.get('parent')
            if parent_name and 'windows' in context:
                parent = context['windows'].get(parent_name)
                if parent:
                    canvas.create(parent, context)
        self._ready = True


# Turtle command nodes for drawing
class TurtleCommandNode(ActionNode):
    """Base class for turtle drawing commands"""
    _properties = {{
        'target': PropertyDescriptor('target', str, required=True),
    }}
    
    def get_turtle_canvas(self, context):
        target = self.attributes.get('target')
        if target and '{tag_name}s' in context:
            return context['{tag_name}s'].get(target)
        return None


class ForwardNode(TurtleCommandNode):
    tag_name = 'forward'
    _properties = {{
        **TurtleCommandNode._properties,
        'distance': PropertyDescriptor('distance', float, required=True),
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        canvas = self.get_turtle_canvas(context)
        if canvas:
            canvas.forward(resolved.get('distance', 100))
        self._ready = True


class RightNode(TurtleCommandNode):
    tag_name = 'right'
    _properties = {{
        **TurtleCommandNode._properties,
        'angle': PropertyDescriptor('angle', float, required=True),
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        canvas = self.get_turtle_canvas(context)
        if canvas:
            canvas.right(resolved.get('angle', 90))
        self._ready = True


class LeftNode(TurtleCommandNode):
    tag_name = 'left'
    _properties = {{
        **TurtleCommandNode._properties,
        'angle': PropertyDescriptor('angle', float, required=True),
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        canvas = self.get_turtle_canvas(context)
        if canvas:
            canvas.left(resolved.get('angle', 90))
        self._ready = True


class PenColorNode(TurtleCommandNode):
    tag_name = 'pencolor'
    _properties = {{
        **TurtleCommandNode._properties,
        'color': PropertyDescriptor('color', str, required=True),
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        canvas = self.get_turtle_canvas(context)
        if canvas:
            canvas.pencolor(resolved.get('color', 'black'))
        self._ready = True


class CircleNode(TurtleCommandNode):
    tag_name = 'circle'
    _properties = {{
        **TurtleCommandNode._properties,
        'radius': PropertyDescriptor('radius', float, required=True),
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        canvas = self.get_turtle_canvas(context)
        if canvas:
            canvas.circle(resolved.get('radius', 50))
        self._ready = True


def get_line_parsers():
    import re
    
    def parse_{tag_name}(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child({class_name}Node('{tag_name}', attrs))
        return None
    
    def parse_forward(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child(ForwardNode('forward', attrs))
        return None
    
    def parse_right(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child(RightNode('right', attrs))
        return None
    
    def parse_left(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child(LeftNode('left', attrs))
        return None
    
    def parse_pencolor(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child(PenColorNode('pencolor', attrs))
        return None
    
    def parse_circle(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child(CircleNode('circle', attrs))
        return None
    
    return [
        (r'<{tag_name}\\s+(.+?)\\s*/?>$', parse_{tag_name}),
        (r'<forward\\s+(.+?)\\s*/?>$', parse_forward),
        (r'<right\\s+(.+?)\\s*/?>$', parse_right),
        (r'<left\\s+(.+?)\\s*/?>$', parse_left),
        (r'<pencolor\\s+(.+?)\\s*/?>$', parse_pencolor),
        (r'<circle\\s+(.+?)\\s*/?>$', parse_circle),
    ]
{gui_info_code}'''

    def _generate_matplotlib_code(self, tag_name, class_name, base_class, configs, methods, gui_info_code):
        """Generate code for matplotlib plots"""
        props_code = "\n".join([f"        '{c['pytml']}': PropertyDescriptor('{c['pytml']}', str, default='')," for c in configs])
        
        return f'''"""
PyTML {class_name} Module - Auto-generated by LibEditor
Matplotlib Plot Canvas for PyTML
Based on: matplotlib
"""

import tkinter as tk
from libs.core import ActionNode, WidgetNode, PropertyDescriptor, resolve_attributes

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

class {class_name}:
    """Matplotlib plot canvas that can be embedded in a PyTML window"""
    
    def __init__(self, name, **kwargs):
        self.name = name
        self._figure = None
        self._canvas = None
        self._ax = None
        self.width = int(kwargs.get('width', 400))
        self.height = int(kwargs.get('height', 300))
        self.x = int(kwargs.get('x', 0))
        self.y = int(kwargs.get('y', 0))
        self.title = kwargs.get('title', '')
        self._config = kwargs
    
    def create(self, parent_window, context=None):
        """Create matplotlib canvas embedded in parent window"""
        if not HAS_MATPLOTLIB:
            print("Warning: matplotlib not installed")
            return self
            
        tk_win = parent_window.get_tk_window()
        if tk_win:
            # Create figure with size in inches (assuming 100 dpi)
            fig_width = self.width / 100
            fig_height = self.height / 100
            self._figure = Figure(figsize=(fig_width, fig_height), dpi=100)
            self._ax = self._figure.add_subplot(111)
            
            if self.title:
                self._ax.set_title(self.title)
            
            # Create canvas and embed in tkinter
            self._canvas = FigureCanvasTkAgg(self._figure, master=tk_win)
            self._canvas.draw()
            self._canvas.get_tk_widget().place(x=self.x, y=self.y)
            
        return self
    
    def get_figure(self):
        return self._figure
    
    def get_axes(self):
        return self._ax
    
    def plot(self, x_data, y_data, **kwargs):
        if self._ax:
            self._ax.plot(x_data, y_data, **kwargs)
            self._canvas.draw()
    
    def bar(self, x_data, heights, **kwargs):
        if self._ax:
            self._ax.bar(x_data, heights, **kwargs)
            self._canvas.draw()
    
    def scatter(self, x_data, y_data, **kwargs):
        if self._ax:
            self._ax.scatter(x_data, y_data, **kwargs)
            self._canvas.draw()
    
    def clear(self):
        if self._ax:
            self._ax.clear()
            self._canvas.draw()
    
    def set_title(self, title):
        if self._ax:
            self._ax.set_title(title)
            self._canvas.draw()
    
    def set_xlabel(self, label):
        if self._ax:
            self._ax.set_xlabel(label)
            self._canvas.draw()
    
    def set_ylabel(self, label):
        if self._ax:
            self._ax.set_ylabel(label)
            self._canvas.draw()
    
    def refresh(self):
        if self._canvas:
            self._canvas.draw()


class {class_name}Node(WidgetNode):
    tag_name = '{tag_name}'
    _properties = {{
        'name': PropertyDescriptor('name', str, required=True),
        'parent': PropertyDescriptor('parent', str),
        'x': PropertyDescriptor('x', int, default=0),
        'y': PropertyDescriptor('y', int, default=0),
        'width': PropertyDescriptor('width', int, default=400),
        'height': PropertyDescriptor('height', int, default=300),
        'title': PropertyDescriptor('title', str, default=''),
{props_code}
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        name = resolved.get('name')
        if name:
            if '{tag_name}s' not in context:
                context['{tag_name}s'] = {{}}
            plot = {class_name}(name, **resolved)
            context['{tag_name}s'][name] = plot
            parent_name = resolved.get('parent')
            if parent_name and 'windows' in context:
                parent = context['windows'].get(parent_name)
                if parent:
                    plot.create(parent, context)
        self._ready = True


def get_line_parsers():
    import re
    def parse_{tag_name}(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child({class_name}Node('{tag_name}', attrs))
        return None
    return [(r'<{tag_name}\\s+(.+?)\\s*/?>$', parse_{tag_name})]
{gui_info_code}'''

    def _generate_pygame_code(self, tag_name, class_name, base_class, configs, methods, gui_info_code):
        """Generate code for pygame surfaces"""
        props_code = "\n".join([f"        '{c['pytml']}': PropertyDescriptor('{c['pytml']}', str, default='')," for c in configs])
        
        return f'''"""
PyTML {class_name} Module - Auto-generated by LibEditor
Pygame Surface for PyTML
Based on: pygame
"""

import tkinter as tk
import os
from libs.core import ActionNode, WidgetNode, PropertyDescriptor, resolve_attributes

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

class {class_name}:
    """Pygame surface that can be embedded in a PyTML window"""
    
    def __init__(self, name, **kwargs):
        self.name = name
        self._frame = None
        self._surface = None
        self.width = int(kwargs.get('width', 640))
        self.height = int(kwargs.get('height', 480))
        self.x = int(kwargs.get('x', 0))
        self.y = int(kwargs.get('y', 0))
        self.bgcolor = kwargs.get('bgcolor', 'black')
        self._config = kwargs
        self._running = False
    
    def create(self, parent_window, context=None):
        """Create pygame surface embedded in parent window"""
        if not HAS_PYGAME:
            print("Warning: pygame not installed")
            return self
            
        tk_win = parent_window.get_tk_window()
        if tk_win:
            # Create a frame to embed pygame
            self._frame = tk.Frame(tk_win, width=self.width, height=self.height)
            self._frame.place(x=self.x, y=self.y)
            self._frame.update()
            
            # Set SDL to use this window
            os.environ['SDL_WINDOWID'] = str(self._frame.winfo_id())
            
            # Initialize pygame
            pygame.init()
            self._surface = pygame.display.set_mode((self.width, self.height))
            
            # Set background color
            self._surface.fill(pygame.Color(self.bgcolor))
            pygame.display.flip()
            
        return self
    
    def get_surface(self):
        return self._surface
    
    def fill(self, color):
        if self._surface:
            self._surface.fill(pygame.Color(color))
    
    def draw_rect(self, color, rect, width=0):
        if self._surface:
            pygame.draw.rect(self._surface, pygame.Color(color), rect, width)
    
    def draw_circle(self, color, center, radius, width=0):
        if self._surface:
            pygame.draw.circle(self._surface, pygame.Color(color), center, radius, width)
    
    def draw_line(self, color, start, end, width=1):
        if self._surface:
            pygame.draw.line(self._surface, pygame.Color(color), start, end, width)
    
    def flip(self):
        if self._surface:
            pygame.display.flip()
    
    def update(self):
        if self._surface:
            pygame.display.update()


class {class_name}Node(WidgetNode):
    tag_name = '{tag_name}'
    _properties = {{
        'name': PropertyDescriptor('name', str, required=True),
        'parent': PropertyDescriptor('parent', str),
        'x': PropertyDescriptor('x', int, default=0),
        'y': PropertyDescriptor('y', int, default=0),
        'width': PropertyDescriptor('width', int, default=640),
        'height': PropertyDescriptor('height', int, default=480),
        'bgcolor': PropertyDescriptor('bgcolor', str, default='black'),
{props_code}
    }}
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        name = resolved.get('name')
        if name:
            if '{tag_name}s' not in context:
                context['{tag_name}s'] = {{}}
            surface = {class_name}(name, **resolved)
            context['{tag_name}s'][name] = surface
            parent_name = resolved.get('parent')
            if parent_name and 'windows' in context:
                parent = context['windows'].get(parent_name)
                if parent:
                    surface.create(parent, context)
        self._ready = True


def get_line_parsers():
    import re
    def parse_{tag_name}(match, current, context):
        attrs = {{m.group(1): m.group(2) for m in re.finditer(r'(\\w+)="([^"]*)"', match.group(1))}}
        current.add_child({class_name}Node('{tag_name}', attrs))
        return None
    return [(r'<{tag_name}\\s+(.+?)\\s*/?>$', parse_{tag_name})]
{gui_info_code}'''
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    editor = LibEditor()
    editor.run()
