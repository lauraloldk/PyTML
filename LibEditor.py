"""
PyTML Lib Editor
Scans the entire Python codebase and lets you add support for anything
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
import inspect
import pkgutil
import importlib


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
        
        ttk.Label(parent, text="💡 Double-click to add to PyTML | Right-click for type info", foreground='gray').pack()
    
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
        self.status_var.set(f"Scanning {module_name}...")
        self.root.update()
        
        classes = self.scanner.get_module_classes(module_name)
        
        self.class_list.delete(0, tk.END)
        for name, cls in classes:
            self.class_list.insert(tk.END, name)
        
        self.classes_data = {name: cls for name, cls in classes}
        self.status_var.set(f"Found {len(classes)} classes in {module_name}")
    
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
        
        configs = [m for m in self.selected_members if m['type'] == 'config']
        methods = [m for m in self.selected_members if m['type'] == 'method']
        
        config_map = "\n".join([f"    '{c['pytml']}': '{c['python']}'," for c in configs])
        props_code = "\n".join([f"        '{c['pytml']}': PropertyDescriptor('{c['pytml']}', str, default='')," for c in configs])
        
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
'''
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    editor = LibEditor()
    editor.run()
