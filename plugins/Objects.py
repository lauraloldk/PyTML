"""
PyTML Editor Plugin: Objects Panel
Dynamisk indlæsning af objekter fra lib filer og compiler nodes
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import inspect
import re
import importlib.util
import glob

# Tilføj parent directory til path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ObjectInfo:
    """Information om et PyTML objekt"""
    
    def __init__(self, name, obj_type, module, description=""):
        self.name = name
        self.obj_type = obj_type  # 'node', 'class', 'function', 'parser'
        self.module = module
        self.description = description
        self.syntax = ""
        self.properties = []
        self.methods = []
        self.signature = ""
    
    def add_property(self, name, prop_type, description=""):
        """Tilføj en property"""
        self.properties.append({
            'name': name,
            'type': prop_type,
            'description': description
        })
    
    def add_method(self, name, signature, description=""):
        """Tilføj en metode"""
        self.methods.append({
            'name': name,
            'signature': signature,
            'description': description
        })


class ObjectLibrary:
    """Dynamisk samling af alle PyTML objekter fra libs"""
    
    def __init__(self):
        self.objects = {}
        self.categories = {}
        self.parsers = []  # Liste af (pattern, syntax_example)
    
    def load_from_libs(self):
        """Load alle objekter dynamisk fra lib filer"""
        self.objects = {}
        self.categories = {}
        self.parsers = []
        
        libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        
        # Find alle python filer i libs mappen
        for lib_file in glob.glob(os.path.join(libs_path, '*.py')):
            if lib_file.endswith('__init__.py'):
                continue
            self._load_lib_file(lib_file)
        
        # Load fra Compiler.py
        self._load_compiler_objects()
    
    def _load_lib_file(self, filepath):
        """Load objekter fra en enkelt lib fil"""
        module_name = os.path.basename(filepath)[:-3]  # Fjern .py
        category = module_name.replace('_', ' ').title()
        
        if category not in self.categories:
            self.categories[category] = []
        
        try:
            # Dynamisk import
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find alle klasser
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.startswith('_'):
                    continue
                
                # Spring ActionNode base klassen over (den er duplikeret i hver fil)
                if name == 'ActionNode' and module_name != 'compiler':
                    continue
                
                info = self._extract_class_info(name, obj, module_name, filepath)
                if info:
                    self.objects[f"{module_name}.{name}"] = info
                    self.categories[category].append(info)
            
            # Find line parsers hvis de findes
            if hasattr(module, 'get_line_parsers'):
                parsers = module.get_line_parsers()
                for pattern, handler in parsers:
                    syntax = self._pattern_to_syntax(pattern)
                    parser_info = ObjectInfo(
                        name=syntax,
                        obj_type='syntax',
                        module=module_name,
                        description=handler.__doc__ or f"Parser fra {module_name}"
                    )
                    parser_info.syntax = syntax
                    self.parsers.append((pattern, syntax))
                    
                    # Tilføj som objekt
                    key = f"{module_name}.parser.{len(self.parsers)}"
                    self.objects[key] = parser_info
                    self.categories[category].append(parser_info)
                    
        except Exception as e:
            print(f"Kunne ikke loade {filepath}: {e}")
    
    def _load_compiler_objects(self):
        """Load objekter fra Compiler.py"""
        compiler_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Compiler.py')
        
        if 'Control Flow' not in self.categories:
            self.categories['Control Flow'] = []
        
        try:
            spec = importlib.util.spec_from_file_location('Compiler', compiler_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find node klasser
            for name in ['ActionNode', 'BlockNode', 'IfNode', 'LoopNode']:
                if hasattr(module, name):
                    obj = getattr(module, name)
                    info = self._extract_class_info(name, obj, 'Compiler', compiler_path)
                    if info:
                        self.objects[f"Compiler.{name}"] = info
                        self.categories['Control Flow'].append(info)
                        
        except Exception as e:
            print(f"Kunne ikke loade Compiler.py: {e}")
    
    def _extract_class_info(self, name, cls, module_name, filepath):
        """Udtræk information fra en klasse"""
        info = ObjectInfo(
            name=name,
            obj_type='node' if 'Node' in name else 'class',
            module=module_name,
            description=cls.__doc__ or f"Klasse fra {module_name}"
        )
        
        # Udtræk properties fra __init__
        try:
            init_sig = inspect.signature(cls.__init__)
            params = []
            for param_name, param in init_sig.parameters.items():
                if param_name == 'self':
                    continue
                param_type = 'any'
                if param.annotation != inspect.Parameter.empty:
                    param_type = str(param.annotation)
                info.add_property(param_name, param_type)
                params.append(param_name)
            info.signature = f"({', '.join(params)})"
        except:
            pass
        
        # Udtræk metoder
        for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if method_name.startswith('_'):
                continue
            try:
                sig = str(inspect.signature(method))
                doc = method.__doc__ or ""
                info.add_method(method_name, sig, doc.split('\n')[0] if doc else "")
            except:
                info.add_method(method_name, "()", "")
        
        # Generer syntax eksempel baseret på klasse navn
        info.syntax = self._generate_syntax_example(name, info.properties)
        
        return info
    
    def _pattern_to_syntax(self, pattern):
        """Konverter regex pattern til læsbar syntax"""
        # Erstat regex grupper med placeholders
        syntax = pattern
        syntax = re.sub(r'\(\?:([^)]+)\)', r'\1', syntax)  # Non-capturing groups
        syntax = re.sub(r'\(\\w\+\)', 'name', syntax)
        syntax = re.sub(r'\(\\d\+\)', 'number', syntax)
        syntax = re.sub(r'\(\[\^"\]\*\)', 'value', syntax)
        syntax = re.sub(r'\(\.\+\?\)', '...', syntax)
        syntax = re.sub(r'\\s\+', ' ', syntax)
        syntax = re.sub(r'\\s\*', '', syntax)
        syntax = re.sub(r'\?', '', syntax)
        return syntax
    
    def _generate_syntax_example(self, class_name, properties):
        """Generer syntax eksempel baseret på klasse"""
        name_lower = class_name.lower().replace('node', '').replace('action', '')
        
        if not name_lower:
            return ""
        
        # Byg attributter
        attrs = []
        for prop in properties:
            if prop['name'] in ('tag_name', 'attributes', 'children', 'parent'):
                continue
            attrs.append(f'{prop["name"]}="..."')
        
        if attrs:
            return f'<{name_lower} {" ".join(attrs)}>'
        return f'<{name_lower}>'
    
    def get_by_category(self, category):
        """Hent objekter i en kategori"""
        return self.categories.get(category, [])
    
    def get_all(self):
        """Hent alle objekter"""
        return list(self.objects.values())
    
    def get_all_syntax(self):
        """Hent alle syntax eksempler"""
        syntax_list = []
        for obj in self.objects.values():
            if obj.syntax:
                syntax_list.append({
                    'syntax': obj.syntax,
                    'name': obj.name,
                    'module': obj.module,
                    'description': obj.description
                })
        return syntax_list
    
    def search(self, query):
        """Søg efter objekter"""
        query = query.lower()
        results = []
        for obj in self.objects.values():
            if (query in obj.name.lower() or 
                query in obj.description.lower() or
                query in obj.syntax.lower()):
                results.append(obj)
        return results


class ObjectsPanel(ttk.Frame):
    """Panel der viser tilgængelige PyTML objekter"""
    
    def __init__(self, parent, editor_callback=None):
        super().__init__(parent)
        self.editor_callback = editor_callback  # Callback til at indsætte kode i editor
        
        self.library = ObjectLibrary()
        self.library.load_from_libs()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Opsæt UI"""
        # Søgefelt
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Refresh knap
        ttk.Button(search_frame, text="🔄", width=3, command=self._refresh).pack(side=tk.RIGHT)
        
        # Treeview med objekter
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=('Type', 'Syntax'), show='tree headings')
        self.tree.heading('#0', text='Objekt')
        self.tree.heading('Type', text='Type')
        self.tree.heading('Syntax', text='Syntax')
        self.tree.column('#0', width=120)
        self.tree.column('Type', width=60)
        self.tree.column('Syntax', width=200)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Double-click to insert
        self.tree.bind('<Double-1>', self._on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        
        # Info panel
        self.info_text = tk.Text(self, height=4, wrap=tk.WORD, bg='#2d2d2d', fg='#d4d4d4')
        self.info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Insert knap
        ttk.Button(self, text="📥 Indsæt i Editor", command=self._insert_selected).pack(pady=5)
        
        # Load objekter
        self._populate_tree()
    
    def _refresh(self):
        """Genindlæs objekter fra libs"""
        self.library.load_from_libs()
        self._populate_tree()
    
    def _populate_tree(self, objects=None):
        """Fyld tree med objekter"""
        # Ryd eksisterende
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if objects is None:
            # Vis efter kategori
            for category, objs in sorted(self.library.categories.items()):
                if objs:
                    cat_id = self.tree.insert('', 'end', text=f"📁 {category}", open=False)
                    for obj in objs:
                        syntax_short = obj.syntax[:40] + '...' if len(obj.syntax) > 40 else obj.syntax
                        self.tree.insert(cat_id, 'end', text=obj.name, 
                                        values=(obj.obj_type, syntax_short),
                                        tags=(obj.name,))
        else:
            # Vis søgeresultater
            for obj in objects:
                syntax_short = obj.syntax[:40] + '...' if len(obj.syntax) > 40 else obj.syntax
                self.tree.insert('', 'end', text=obj.name,
                                values=(obj.obj_type, syntax_short),
                                tags=(obj.name,))
    
    def _on_search(self, *args):
        """Håndter søgning"""
        query = self.search_var.get()
        if query:
            results = self.library.search(query)
            self._populate_tree(results)
        else:
            self._populate_tree()
    
    def _on_select(self, event):
        """Vis info om valgt objekt"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.tree.item(item, 'text')
        
        # Find objektet
        for obj in self.library.objects.values():
            if obj.name == item_text:
                self._show_info(obj)
                break
    
    def _show_info(self, obj):
        """Vis information om et objekt"""
        self.info_text.delete('1.0', tk.END)
        
        info = f"📦 {obj.name} ({obj.obj_type})\n"
        info += f"📁 Module: {obj.module}\n"
        if obj.description:
            info += f"📝 {obj.description}\n"
        if obj.syntax:
            info += f"💻 Syntax: {obj.syntax}"
        
        self.info_text.insert('1.0', info)
    
    def _on_double_click(self, event):
        """Håndter double-click"""
        self._insert_selected()
    
    def _insert_selected(self):
        """Indsæt valgt objekt i editor"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.tree.item(item, 'text')
        
        # Find objektet
        for obj in self.library.objects.values():
            if obj.name == item_text and obj.syntax:
                if self.editor_callback:
                    self.editor_callback(obj.syntax)
                break


# Eksporter
__all__ = ['ObjectInfo', 'ObjectLibrary', 'ObjectsPanel']
