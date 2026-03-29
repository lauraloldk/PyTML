"""
PyTML Plugin: Library Editor (Read-Only)
A comprehensive Python module browser showing all installed packages,
their classes, methods, properties, and any PyTML references.

This is a read-only viewer for lib developers to explore possibilities.
To modify anything, edit lib files manually or create new ones.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
import pkgutil
import importlib
import inspect
import re
from typing import Dict, List, Any, Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ModuleInfo:
    """Information about a Python module"""
    def __init__(self, name: str, module=None):
        self.name = name
        self.module = module
        self.docstring = ""
        self.classes: List['ClassInfo'] = []
        self.functions: List['FunctionInfo'] = []
        self.constants: List['ConstantInfo'] = []
        self.submodules: List[str] = []
        self.pytml_syntax: List[str] = []  # PyTML syntax if available
        self.is_pytml_lib = False
        
    def analyze(self):
        """Analyze the module contents"""
        if not self.module:
            return
            
        self.docstring = inspect.getdoc(self.module) or ""
        
        # Check if PyTML lib
        module_file = getattr(self.module, '__file__', '')
        if module_file and 'libs' in module_file:
            self.is_pytml_lib = True
            self._extract_pytml_syntax()
        
        # Get classes
        for name, obj in inspect.getmembers(self.module, inspect.isclass):
            if obj.__module__ == self.module.__name__:
                class_info = ClassInfo(name, obj)
                class_info.analyze()
                self.classes.append(class_info)
        
        # Get functions
        for name, obj in inspect.getmembers(self.module, inspect.isfunction):
            if obj.__module__ == self.module.__name__:
                func_info = FunctionInfo(name, obj)
                func_info.analyze()
                self.functions.append(func_info)
        
        # Get constants (module-level variables that are not private)
        for name, obj in inspect.getmembers(self.module):
            if not name.startswith('_') and not inspect.ismodule(obj) and \
               not inspect.isclass(obj) and not inspect.isfunction(obj) and \
               not inspect.isbuiltin(obj):
                const_info = ConstantInfo(name, obj)
                self.constants.append(const_info)
    
    def _extract_pytml_syntax(self):
        """Extract PyTML Syntax: block from module docstring"""
        if not self.docstring:
            return
        
        syntax_match = re.search(r'Syntax:\s*\n((?:[ \t]+[^\n]+\n?)+)', self.docstring)
        if syntax_match:
            block = syntax_match.group(1)
            for line in block.split('\n'):
                line = line.strip()
                if line and '<' in line:
                    self.pytml_syntax.append(line)


class ClassInfo:
    """Information about a Python class"""
    def __init__(self, name: str, cls):
        self.name = name
        self.cls = cls
        self.docstring = ""
        self.bases: List[str] = []
        self.methods: List['FunctionInfo'] = []
        self.properties: List['PropertyInfo'] = []
        self.class_methods: List['FunctionInfo'] = []
        self.static_methods: List['FunctionInfo'] = []
        
    def analyze(self):
        """Analyze the class contents"""
        self.docstring = inspect.getdoc(self.cls) or ""
        self.bases = [b.__name__ for b in self.cls.__bases__ if b.__name__ != 'object']
        
        # Get methods
        for name, obj in inspect.getmembers(self.cls):
            if name.startswith('_') and not name.startswith('__'):
                continue  # Skip private methods
                
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                func_info = FunctionInfo(name, obj)
                func_info.analyze()
                self.methods.append(func_info)
            elif isinstance(obj, property):
                prop_info = PropertyInfo(name, obj)
                self.properties.append(prop_info)
            elif isinstance(obj, classmethod):
                func_info = FunctionInfo(name, obj.__func__)
                func_info.analyze()
                self.class_methods.append(func_info)
            elif isinstance(obj, staticmethod):
                func_info = FunctionInfo(name, obj.__func__)
                func_info.analyze()
                self.static_methods.append(func_info)


class FunctionInfo:
    """Information about a Python function/method"""
    def __init__(self, name: str, func):
        self.name = name
        self.func = func
        self.docstring = ""
        self.signature = ""
        self.parameters: List['ParameterInfo'] = []
        self.return_type = ""
        
    def analyze(self):
        """Analyze the function"""
        self.docstring = inspect.getdoc(self.func) or ""
        
        try:
            sig = inspect.signature(self.func)
            self.signature = str(sig)
            
            for param_name, param in sig.parameters.items():
                param_info = ParameterInfo(param_name, param)
                self.parameters.append(param_info)
                
            if sig.return_annotation != inspect.Parameter.empty:
                self.return_type = str(sig.return_annotation)
        except (ValueError, TypeError):
            self.signature = "(...)"


class ParameterInfo:
    """Information about a function parameter"""
    def __init__(self, name: str, param):
        self.name = name
        self.param = param
        self.annotation = ""
        self.default = None
        self.has_default = False
        
        if param.annotation != inspect.Parameter.empty:
            self.annotation = str(param.annotation)
        if param.default != inspect.Parameter.empty:
            self.default = param.default
            self.has_default = True


class PropertyInfo:
    """Information about a class property"""
    def __init__(self, name: str, prop):
        self.name = name
        self.prop = prop
        self.docstring = inspect.getdoc(prop) or ""
        self.readable = prop.fget is not None
        self.writable = prop.fset is not None


class ConstantInfo:
    """Information about a module constant"""
    def __init__(self, name: str, value):
        self.name = name
        self.value = value
        self.type_name = type(value).__name__
        
    def get_display_value(self) -> str:
        """Get a displayable representation of the value"""
        val_str = repr(self.value)
        if len(val_str) > 100:
            return val_str[:97] + "..."
        return val_str


class LibraryBrowser:
    """Main library browser class that manages module discovery and analysis"""
    
    def __init__(self):
        self.modules: Dict[str, ModuleInfo] = {}
        self.pytml_libs: Dict[str, ModuleInfo] = {}
        self.stdlib_modules: List[str] = []
        self.installed_packages: List[str] = []
        
    def discover_all(self):
        """Discover all available modules"""
        self._discover_pytml_libs()
        self._discover_stdlib()
        self._discover_installed()
        
    def _discover_pytml_libs(self):
        """Discover PyTML libs"""
        libs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        if os.path.exists(libs_dir):
            for filename in os.listdir(libs_dir):
                if filename.endswith('.py') and not filename.startswith('_'):
                    module_name = filename[:-3]
                    try:
                        spec = importlib.util.spec_from_file_location(
                            module_name,
                            os.path.join(libs_dir, filename)
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            
                            info = ModuleInfo(f"libs.{module_name}", module)
                            info.is_pytml_lib = True
                            info.analyze()
                            self.pytml_libs[module_name] = info
                    except Exception as e:
                        # Skip modules that fail to load
                        pass
    
    def _discover_stdlib(self):
        """Discover standard library modules"""
        stdlib_names = [
            'os', 'sys', 'io', 're', 'math', 'random', 'datetime', 'time',
            'json', 'csv', 'collections', 'itertools', 'functools', 
            'threading', 'multiprocessing', 'subprocess', 'shutil',
            'pathlib', 'glob', 'fnmatch', 'tempfile', 'pickle', 'shelve',
            'sqlite3', 'hashlib', 'hmac', 'secrets', 'base64',
            'html', 'xml', 'urllib', 'http', 'email', 'mimetypes',
            'string', 'textwrap', 'unicodedata', 'codecs',
            'struct', 'array', 'copy', 'pprint', 'enum', 'typing',
            'abc', 'contextlib', 'dataclasses', 'decimal', 'fractions',
            'statistics', 'socket', 'ssl', 'select', 'asyncio',
            'concurrent', 'queue', 'sched', 'logging', 'warnings',
            'unittest', 'doctest', 'argparse', 'configparser',
            'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma', 'zlib',
            'platform', 'locale', 'gettext', 'calendar', 'heapq', 'bisect'
        ]
        self.stdlib_modules = sorted(stdlib_names)
    
    def _discover_installed(self):
        """Discover installed third-party packages"""
        try:
            installed = []
            for importer, modname, ispkg in pkgutil.iter_modules():
                if modname not in self.stdlib_modules and not modname.startswith('_'):
                    installed.append(modname)
            self.installed_packages = sorted(set(installed))[:200]  # Limit to 200
        except Exception:
            pass
    
    def load_module(self, name: str) -> Optional[ModuleInfo]:
        """Load and analyze a specific module"""
        if name in self.modules:
            return self.modules[name]
            
        try:
            module = importlib.import_module(name)
            info = ModuleInfo(name, module)
            info.analyze()
            self.modules[name] = info
            return info
        except Exception as e:
            return None


class LibEditorWindow:
    """The Library Editor window UI"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.browser = LibraryBrowser()
        self.current_module: Optional[ModuleInfo] = None
        
        self._create_window()
        self._setup_ui()
        self._load_initial()
        
    def _create_window(self):
        """Create the main window"""
        if self.parent:
            self.window = tk.Toplevel(self.parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("PyTML Library Editor - Python Module Browser")
        self.window.geometry("1200x800")
        self.window.minsize(900, 600)
        
        # Configure style
        style = ttk.Style()
        style.configure('Heading.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Code.TLabel', font=('Consolas', 10))
        style.configure('PyTML.TLabel', font=('Consolas', 10), foreground='#0066cc')
        
    def _setup_ui(self):
        """Setup the UI components"""
        # Main paned window
        self.paned = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Module tree
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)
        
        # Search
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Module tree
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_frame, show='tree')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        
        # Right panel - Details
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        # Module header
        self.header_frame = ttk.Frame(right_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.module_label = ttk.Label(self.header_frame, text="Select a module", 
                                       style='Heading.TLabel')
        self.module_label.pack(anchor=tk.W)
        
        self.module_type_label = ttk.Label(self.header_frame, text="")
        self.module_type_label.pack(anchor=tk.W)
        
        # Notebook for different views
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Overview tab
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Overview")
        
        self.overview_text = tk.Text(self.overview_frame, wrap=tk.WORD, 
                                     font=('Consolas', 10), state=tk.DISABLED)
        self.overview_text.pack(fill=tk.BOTH, expand=True)
        
        # Classes tab
        self.classes_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.classes_frame, text="Classes")
        
        self.classes_tree = ttk.Treeview(self.classes_frame, columns=('type', 'signature'),
                                          show='tree headings')
        self.classes_tree.heading('type', text='Type')
        self.classes_tree.heading('signature', text='Signature')
        self.classes_tree.column('type', width=100)
        self.classes_tree.column('signature', width=400)
        self.classes_tree.pack(fill=tk.BOTH, expand=True)
        
        self.classes_tree.bind('<<TreeviewSelect>>', self._on_class_select)
        
        # Functions tab
        self.functions_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.functions_frame, text="Functions")
        
        self.functions_tree = ttk.Treeview(self.functions_frame, 
                                           columns=('signature', 'return'),
                                           show='tree headings')
        self.functions_tree.heading('signature', text='Signature')
        self.functions_tree.heading('return', text='Returns')
        self.functions_tree.column('signature', width=400)
        self.functions_tree.column('return', width=150)
        self.functions_tree.pack(fill=tk.BOTH, expand=True)
        
        self.functions_tree.bind('<<TreeviewSelect>>', self._on_function_select)
        
        # PyTML Syntax tab
        self.pytml_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.pytml_frame, text="PyTML Syntax")
        
        self.pytml_text = tk.Text(self.pytml_frame, wrap=tk.WORD,
                                  font=('Consolas', 11), state=tk.DISABLED,
                                  bg='#f5f5f5')
        self.pytml_text.pack(fill=tk.BOTH, expand=True)
        
        # Constants tab
        self.constants_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.constants_frame, text="Constants")
        
        self.constants_tree = ttk.Treeview(self.constants_frame,
                                           columns=('type', 'value'),
                                           show='tree headings')
        self.constants_tree.heading('type', text='Type')
        self.constants_tree.heading('value', text='Value')
        self.constants_tree.column('type', width=100)
        self.constants_tree.column('value', width=400)
        self.constants_tree.pack(fill=tk.BOTH, expand=True)
        
        # Detail panel
        self.detail_frame = ttk.LabelFrame(right_frame, text="Details")
        self.detail_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.detail_text = tk.Text(self.detail_frame, wrap=tk.WORD, height=6,
                                   font=('Consolas', 10), state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.window, textvariable=self.status_var, 
                                    relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def _load_initial(self):
        """Load initial module list"""
        self.status_var.set("Discovering modules...")
        self.window.update()
        
        self.browser.discover_all()
        
        # Populate tree
        # PyTML Libs
        pytml_node = self.tree.insert('', 'end', 'pytml', text='📦 PyTML Libraries', open=True)
        for name in sorted(self.browser.pytml_libs.keys()):
            self.tree.insert(pytml_node, 'end', f'pytml.{name}', text=f'  {name}')
        
        # Standard Library
        stdlib_node = self.tree.insert('', 'end', 'stdlib', text='📚 Python Standard Library')
        for name in self.browser.stdlib_modules:
            self.tree.insert(stdlib_node, 'end', f'stdlib.{name}', text=f'  {name}')
        
        # Installed Packages
        installed_node = self.tree.insert('', 'end', 'installed', text='📥 Installed Packages')
        for name in self.browser.installed_packages:
            self.tree.insert(installed_node, 'end', f'installed.{name}', text=f'  {name}')
        
        total = len(self.browser.pytml_libs) + len(self.browser.stdlib_modules) + len(self.browser.installed_packages)
        self.status_var.set(f"Found {total} modules ({len(self.browser.pytml_libs)} PyTML, "
                           f"{len(self.browser.stdlib_modules)} stdlib, "
                           f"{len(self.browser.installed_packages)} installed)")
        
    def _on_search(self, *args):
        """Filter modules based on search"""
        query = self.search_var.get().lower()
        
        # Show/hide items based on search
        for category in ['pytml', 'stdlib', 'installed']:
            for item in self.tree.get_children(category):
                item_text = self.tree.item(item, 'text').strip().lower()
                if query in item_text or not query:
                    # Show item (treeview doesn't have show/hide, so we manage visibility via children)
                    pass
                    
    def _on_tree_select(self, event):
        """Handle tree selection"""
        selection = self.tree.selection()
        if not selection:
            return
            
        item_id = selection[0]
        
        # Check if it's a module (not a category)
        if item_id in ['pytml', 'stdlib', 'installed']:
            return
            
        # Parse module name
        parts = item_id.split('.', 1)
        if len(parts) < 2:
            return
            
        category, module_name = parts
        
        self.status_var.set(f"Loading {module_name}...")
        self.window.update()
        
        # Load module
        if category == 'pytml' and module_name in self.browser.pytml_libs:
            self.current_module = self.browser.pytml_libs[module_name]
        else:
            self.current_module = self.browser.load_module(module_name)
        
        if self.current_module:
            self._display_module(self.current_module)
            self.status_var.set(f"Loaded {module_name}")
        else:
            self.status_var.set(f"Failed to load {module_name}")
            
    def _display_module(self, info: ModuleInfo):
        """Display module information"""
        # Header
        self.module_label.config(text=info.name)
        
        type_text = "PyTML Library" if info.is_pytml_lib else "Python Module"
        if info.classes:
            type_text += f" • {len(info.classes)} classes"
        if info.functions:
            type_text += f" • {len(info.functions)} functions"
        self.module_type_label.config(text=type_text)
        
        # Overview
        self._update_text(self.overview_text, info.docstring or "(No documentation)")
        
        # Classes
        self.classes_tree.delete(*self.classes_tree.get_children())
        for cls in info.classes:
            bases = f" ({', '.join(cls.bases)})" if cls.bases else ""
            cls_node = self.classes_tree.insert('', 'end', text=f"class {cls.name}{bases}",
                                                values=('class', ''))
            
            # Properties
            for prop in cls.properties:
                rw = "r/w" if prop.writable else "r"
                self.classes_tree.insert(cls_node, 'end', text=f"    {prop.name}",
                                        values=('property', f"[{rw}]"))
            
            # Methods
            for method in cls.methods:
                if not method.name.startswith('__') or method.name in ['__init__', '__call__', '__getitem__', '__setitem__']:
                    self.classes_tree.insert(cls_node, 'end', text=f"    {method.name}",
                                            values=('method', method.signature))
        
        # Functions
        self.functions_tree.delete(*self.functions_tree.get_children())
        for func in info.functions:
            self.functions_tree.insert('', 'end', text=func.name,
                                      values=(func.signature, func.return_type or ''))
        
        # PyTML Syntax
        pytml_content = ""
        if info.is_pytml_lib and info.pytml_syntax:
            pytml_content = "PyTML Syntax for this library:\n\n"
            for syntax in info.pytml_syntax:
                pytml_content += f"  {syntax}\n"
        elif info.is_pytml_lib:
            pytml_content = "No PyTML syntax defined.\n\nTo add syntax, include a Syntax: block in the module docstring."
        else:
            pytml_content = "This is not a PyTML library.\n\nPyTML syntax is only available for modules in the libs/ folder."
        self._update_text(self.pytml_text, pytml_content)
        
        # Constants
        self.constants_tree.delete(*self.constants_tree.get_children())
        for const in info.constants:
            self.constants_tree.insert('', 'end', text=const.name,
                                      values=(const.type_name, const.get_display_value()))
        
    def _on_class_select(self, event):
        """Handle class tree selection"""
        selection = self.classes_tree.selection()
        if not selection:
            return
            
        item = self.classes_tree.item(selection[0])
        item_text = item['text'].strip()
        values = item['values']
        
        if not self.current_module:
            return
            
        # Find the item
        detail = ""
        if values and values[0] == 'class':
            # It's a class
            class_name = item_text.replace('class ', '').split('(')[0]
            for cls in self.current_module.classes:
                if cls.name == class_name:
                    detail = f"class {cls.name}\n"
                    if cls.bases:
                        detail += f"Inherits: {', '.join(cls.bases)}\n"
                    detail += f"\n{cls.docstring or '(No documentation)'}"
                    break
        elif values and values[0] == 'method':
            method_name = item_text.strip()
            # Find parent class
            parent = self.classes_tree.parent(selection[0])
            if parent:
                parent_text = self.classes_tree.item(parent, 'text')
                class_name = parent_text.replace('class ', '').split('(')[0].strip()
                for cls in self.current_module.classes:
                    if cls.name == class_name:
                        for method in cls.methods:
                            if method.name == method_name:
                                detail = f"{method.name}{method.signature}\n\n{method.docstring or '(No documentation)'}"
                                break
                        break
        elif values and values[0] == 'property':
            prop_name = item_text.strip()
            parent = self.classes_tree.parent(selection[0])
            if parent:
                parent_text = self.classes_tree.item(parent, 'text')
                class_name = parent_text.replace('class ', '').split('(')[0].strip()
                for cls in self.current_module.classes:
                    if cls.name == class_name:
                        for prop in cls.properties:
                            if prop.name == prop_name:
                                detail = f"Property: {prop.name}\n"
                                detail += f"Readable: {'Yes' if prop.readable else 'No'}\n"
                                detail += f"Writable: {'Yes' if prop.writable else 'No'}\n\n"
                                detail += prop.docstring or "(No documentation)"
                                break
                        break
        
        self._update_text(self.detail_text, detail)
        
    def _on_function_select(self, event):
        """Handle function tree selection"""
        selection = self.functions_tree.selection()
        if not selection:
            return
            
        item = self.functions_tree.item(selection[0])
        func_name = item['text']
        
        if not self.current_module:
            return
            
        for func in self.current_module.functions:
            if func.name == func_name:
                detail = f"def {func.name}{func.signature}\n\n"
                
                if func.parameters:
                    detail += "Parameters:\n"
                    for param in func.parameters:
                        param_str = f"  • {param.name}"
                        if param.annotation:
                            param_str += f": {param.annotation}"
                        if param.has_default:
                            param_str += f" = {param.default}"
                        detail += param_str + "\n"
                    detail += "\n"
                
                if func.return_type:
                    detail += f"Returns: {func.return_type}\n\n"
                    
                detail += func.docstring or "(No documentation)"
                self._update_text(self.detail_text, detail)
                break
                
    def _update_text(self, text_widget, content):
        """Update a text widget"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete('1.0', tk.END)
        text_widget.insert('1.0', content)
        text_widget.config(state=tk.DISABLED)
        
    def run(self):
        """Run the window"""
        if not self.parent:
            self.window.mainloop()
        else:
            self.window.grab_set()


def open_lib_editor(parent=None):
    """Open the library editor window"""
    editor = LibEditorWindow(parent)
    return editor


def get_plugin_info():
    """Plugin registration for auto-discovery"""
    return {
        'name': 'LibEditor',
        'panel_type': 'tool_window',  # Not a panel, but a tool window
        'panel_class': None,
        'panel_icon': '🔧',
        'panel_name': 'Library Editor',
        'priority': 100,
        'callbacks': {
            'open': open_lib_editor
        },
        'menu_items': [
            {'menu': 'Tools', 'label': 'Library Editor...', 'command': 'open'}
        ]
    }


if __name__ == '__main__':
    editor = LibEditorWindow()
    editor.run()
