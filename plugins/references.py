"""
PyTML Editor Plugin: References Browser
Viser alle tilladte referencer, tags, metoder, variabler og properties
Hjælper udviklere med at se alle kombinationer og muligheder
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import glob
import importlib.util
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TagInfo:
    """Information om et tag"""
    
    def __init__(self, name, tag_type, module, syntax, description=""):
        self.name = name
        self.tag_type = tag_type  # 'element', 'action', 'control', 'variable'
        self.module = module
        self.syntax = syntax
        self.description = description
        self.attributes = []  # Liste af AttributeInfo
        self.methods = []     # Liste af MethodInfo
        self.accepts_refs = []  # Hvilke ref typer kan bruges i dette tag
        self.can_be_ref_in = []  # Hvor kan dette tag refereres


class AttributeInfo:
    """Information om en attribut"""
    
    def __init__(self, name, attr_type, required=False, default=None, description=""):
        self.name = name
        self.attr_type = attr_type  # 'string', 'number', 'variable', 'element_ref'
        self.required = required
        self.default = default
        self.description = description
        self.accepts_variable = True  # Kan bruge <var_value> eller $var


class MethodInfo:
    """Information om en metode/action"""
    
    def __init__(self, name, syntax, description=""):
        self.name = name
        self.syntax = syntax
        self.description = description
        self.parameters = []


class ReferencesRegistry:
    """Registry over alle tags, metoder og deres relationer"""
    
    def __init__(self):
        self.tags = {}
        self.methods = {}
        self.variable_patterns = []
        self._load_all()
    
    def _load_all(self):
        """Load alle tags og metoder fra libs"""
        self._load_builtin_tags()
        self._load_from_libs()
        self._analyze_relationships()
    
    def _load_builtin_tags(self):
        """Load indbyggede tags (var, output, control flow)"""
        # Variable tags
        var_tag = TagInfo('var', 'variable', 'var', '<var name="x" value="...">')
        var_tag.description = "Definer en variabel"
        var_tag.attributes = [
            AttributeInfo('name', 'string', required=True, description="Variablens navn"),
            AttributeInfo('value', 'any', required=False, description="Startværdi")
        ]
        self.tags['var'] = var_tag
        
        # Variable value reference
        var_value = TagInfo('_value', 'reference', 'var', '<varname_value>')
        var_value.description = "Hent værdien af en variabel"
        self.tags['_value'] = var_value
        
        # Output tag
        output_tag = TagInfo('output', 'action', 'output', '<output <var_value>> eller <output "tekst">')
        output_tag.description = "Print output til konsol"
        output_tag.attributes = [
            AttributeInfo('value', 'any', required=True, description="Værdi eller variabel reference")
        ]
        output_tag.accepts_refs = ['variable']
        self.tags['output'] = output_tag
        
        # Control flow tags
        if_tag = TagInfo('if', 'control', 'builtin', '<if condition="...">')
        if_tag.description = "Betinget udførelse"
        if_tag.attributes = [
            AttributeInfo('condition', 'expression', required=True, description="Betingelse der evalueres")
        ]
        if_tag.accepts_refs = ['variable']
        self.tags['if'] = if_tag
        
        loop_tag = TagInfo('loop', 'control', 'builtin', '<loop count="n"> eller <loop from="x" to="y">')
        loop_tag.description = "Gentag kode"
        loop_tag.attributes = [
            AttributeInfo('count', 'number', description="Antal gentagelser"),
            AttributeInfo('from', 'number', description="Start værdi"),
            AttributeInfo('to', 'number', description="Slut værdi"),
            AttributeInfo('var', 'string', default='i', description="Loop variabel navn")
        ]
        loop_tag.accepts_refs = ['variable']
        self.tags['loop'] = loop_tag
        
        block_tag = TagInfo('block', 'control', 'builtin', '<block name="...">')
        block_tag.description = "Gruppér kode i en navngivet blok"
        block_tag.attributes = [
            AttributeInfo('name', 'string', description="Blok navn")
        ]
        self.tags['block'] = block_tag
        
        # GUI block
        gui_tag = TagInfo('gui', 'container', 'builtin', '<gui>...</gui>')
        gui_tag.description = "Container for GUI elementer"
        self.tags['gui'] = gui_tag
        
        # Console utils
        noterminate = TagInfo('noterminate', 'control', 'console_utils', '<noterminate>')
        noterminate.description = "Forhindrer programmet i at lukke automatisk"
        self.tags['noterminate'] = noterminate
    
    def _load_from_libs(self):
        """Load tags fra lib filer"""
        libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        
        for lib_file in glob.glob(os.path.join(libs_path, '*.py')):
            if lib_file.endswith('__init__.py'):
                continue
            self._analyze_lib_file(lib_file)
    
    def _analyze_lib_file(self, filepath):
        """Analyser en lib fil for tags og metoder"""
        module_name = os.path.basename(filepath)[:-3]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find syntax fra docstring
            syntax_matches = re.findall(r'Syntax:\s*\n((?:\s+<[^>]+>\s*\n?)+)', content)
            
            # Find get_line_parsers patterns
            parser_patterns = re.findall(r"\(r'(<[^']+>)'", content)
            
            # Find GUI info
            if 'get_gui_info' in content:
                self._load_gui_info(filepath, module_name)
            
            # Analyser baseret på module navn
            if module_name == 'window':
                self._add_window_tags()
            elif module_name == 'button':
                self._add_button_tags()
            elif module_name == 'label':
                self._add_label_tags()
            elif module_name == 'entry':
                self._add_entry_tags()
                
        except Exception as e:
            print(f"ReferencesRegistry: Fejl ved analyse af {filepath}: {e}")
    
    def _load_gui_info(self, filepath, module_name):
        """Load GUI info fra et modul"""
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'get_gui_info'):
                info = module.get_gui_info()
                # GUI info er allerede håndteret via _add_*_tags metoderne
        except:
            pass
    
    def _add_window_tags(self):
        """Tilføj window tags"""
        window = TagInfo('window', 'element', 'window', '<window title="..." name="wnd1" size="300","200">')
        window.description = "Opret et GUI vindue"
        window.attributes = [
            AttributeInfo('title', 'string', required=True, description="Vinduets titel"),
            AttributeInfo('name', 'string', required=True, description="Unikt navn til reference"),
            AttributeInfo('size', 'stack', description="Bredde,højde i pixels")
        ]
        window.accepts_refs = ['variable']
        window.methods = [
            MethodInfo('show', '<name_show>', "Vis vinduet"),
            MethodInfo('hide', '<name_hide>', "Skjul vinduet"),
            MethodInfo('close', '<name_close>', "Luk vinduet"),
            MethodInfo('title', '<name_title="...">', "Ændr titel"),
            MethodInfo('size', '<name_size="w","h">', "Ændr størrelse")
        ]
        self.tags['window'] = window
    
    def _add_button_tags(self):
        """Tilføj button tags"""
        button = TagInfo('button', 'element', 'button', '<button text="..." name="btn1" parent="wnd1">')
        button.description = "Opret en knap i et vindue"
        button.attributes = [
            AttributeInfo('text', 'string', required=True, description="Knappens tekst"),
            AttributeInfo('name', 'string', required=True, description="Unikt navn til reference"),
            AttributeInfo('parent', 'element_ref', required=True, description="Parent vindue navn"),
            AttributeInfo('x', 'number', default='0', description="X position"),
            AttributeInfo('y', 'number', default='0', description="Y position"),
            AttributeInfo('width', 'number', default='100', description="Bredde"),
            AttributeInfo('height', 'number', default='30', description="Højde")
        ]
        button.accepts_refs = ['variable', 'window']
        button.methods = [
            MethodInfo('text', '<name_text="...">', "Ændr tekst"),
            MethodInfo('enabled', '<name_enabled="true/false">', "Aktiver/deaktiver")
        ]
        self.tags['button'] = button
    
    def _add_label_tags(self):
        """Tilføj label tags"""
        label = TagInfo('label', 'element', 'label', '<label text="..." name="lbl1" parent="wnd1">')
        label.description = "Opret et tekst label i et vindue"
        label.attributes = [
            AttributeInfo('text', 'string', required=True, description="Label tekst"),
            AttributeInfo('name', 'string', required=True, description="Unikt navn til reference"),
            AttributeInfo('parent', 'element_ref', required=True, description="Parent vindue navn"),
            AttributeInfo('x', 'number', default='0', description="X position"),
            AttributeInfo('y', 'number', default='0', description="Y position")
        ]
        label.accepts_refs = ['variable', 'window']
        label.methods = [
            MethodInfo('text', '<name_text="...">', "Ændr tekst")
        ]
        self.tags['label'] = label
    
    def _add_entry_tags(self):
        """Tilføj entry tags"""
        entry = TagInfo('entry', 'element', 'entry', '<entry name="txt1" parent="wnd1">')
        entry.description = "Opret et tekstfelt i et vindue"
        entry.attributes = [
            AttributeInfo('name', 'string', required=True, description="Unikt navn til reference"),
            AttributeInfo('parent', 'element_ref', required=True, description="Parent vindue navn"),
            AttributeInfo('placeholder', 'string', description="Placeholder tekst"),
            AttributeInfo('x', 'number', default='0', description="X position"),
            AttributeInfo('y', 'number', default='0', description="Y position"),
            AttributeInfo('width', 'number', default='150', description="Bredde")
        ]
        entry.accepts_refs = ['variable', 'window']
        entry.methods = [
            MethodInfo('value', '<name_value="...">', "Sæt/hent værdi"),
            MethodInfo('placeholder', '<name_placeholder="...">', "Ændr placeholder"),
            MethodInfo('readonly', '<name_readonly="true/false">', "Sæt readonly")
        ]
        self.tags['entry'] = entry
    
    def _analyze_relationships(self):
        """Analyser relationer mellem tags"""
        # Hvilke tags kan refereres fra hvilke
        for tag_name, tag in self.tags.items():
            if tag.tag_type == 'element':
                # GUI elementer kan refereres fra andre GUI elementer
                tag.can_be_ref_in = ['button', 'label', 'entry', 'output']
            elif tag.tag_type == 'variable':
                # Variabler kan refereres fra næsten alt
                tag.can_be_ref_in = list(self.tags.keys())
    
    def get_all_tags(self):
        """Hent alle tags"""
        return self.tags
    
    def get_tags_by_type(self, tag_type):
        """Hent tags af en bestemt type"""
        return {k: v for k, v in self.tags.items() if v.tag_type == tag_type}
    
    def get_allowed_refs_for(self, tag_name):
        """Hent tilladte referencer for et tag"""
        tag = self.tags.get(tag_name)
        if tag:
            return tag.accepts_refs
        return []
    
    def get_reference_syntax(self):
        """Hent alle reference syntaxer"""
        return [
            {
                'pattern': '<varname_value>',
                'description': 'Reference til variabel værdi',
                'example': '<title_value>',
                'can_use_in': 'Alle attributter der accepterer variable'
            },
            {
                'pattern': '$varname',
                'description': 'Alternativ variabel reference',
                'example': '$title',
                'can_use_in': 'Conditions, output, string interpolation'
            },
            {
                'pattern': '<elementname_method>',
                'description': 'Kald metode på element',
                'example': '<wnd1_show>',
                'can_use_in': 'Top-level actions'
            }
        ]


class ReferencesPanel(ttk.Frame):
    """Panel til at vise og udforske alle referencer"""
    
    def __init__(self, parent, editor_callback=None):
        super().__init__(parent)
        self.editor_callback = editor_callback
        self.registry = ReferencesRegistry()
        
        self._setup_ui()
        self._populate_tree()
    
    def _setup_ui(self):
        """Opsæt UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(header, text="📚 Show All Allowed References", 
                 font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT)
        
        # Search
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Filter buttons
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.filter_var = tk.StringVar(value='all')
        filters = [
            ('Alle', 'all'),
            ('Elements', 'element'),
            ('Actions', 'action'),
            ('Variables', 'variable'),
            ('Control', 'control')
        ]
        for text, value in filters:
            ttk.Radiobutton(filter_frame, text=text, value=value, 
                          variable=self.filter_var, 
                          command=self._on_filter).pack(side=tk.LEFT, padx=2)
        
        # Main paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Tree view
        tree_frame = ttk.Frame(paned)
        paned.add(tree_frame, weight=1)
        
        self.tree = ttk.Treeview(tree_frame, show='tree headings', columns=('Type', 'Module'))
        self.tree.heading('#0', text='Tag/Reference')
        self.tree.heading('Type', text='Type')
        self.tree.heading('Module', text='Modul')
        self.tree.column('#0', width=180)
        self.tree.column('Type', width=80)
        self.tree.column('Module', width=80)
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click)
        
        # Right: Details panel
        details_frame = ttk.LabelFrame(paned, text="📋 Detaljer")
        paned.add(details_frame, weight=2)
        
        self.details_text = tk.Text(details_frame, wrap=tk.WORD, 
                                    font=('Consolas', 10),
                                    bg='#1e1e1e', fg='#d4d4d4',
                                    padx=10, pady=10)
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for syntax highlighting
        self.details_text.tag_configure('header', font=('Segoe UI', 12, 'bold'), foreground='#569cd6')
        self.details_text.tag_configure('subheader', font=('Segoe UI', 10, 'bold'), foreground='#4ec9b0')
        self.details_text.tag_configure('syntax', font=('Consolas', 11), foreground='#ce9178')
        self.details_text.tag_configure('attr', foreground='#9cdcfe')
        self.details_text.tag_configure('type', foreground='#4ec9b0')
        self.details_text.tag_configure('desc', foreground='#d4d4d4')
        self.details_text.tag_configure('required', foreground='#f14c4c')
        self.details_text.tag_configure('example', font=('Consolas', 10), foreground='#dcdcaa')
        
        # Bottom: Insert button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="📋 Kopier Syntax", 
                  command=self._copy_syntax).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="➕ Indsæt i Editor", 
                  command=self._insert_syntax).pack(side=tk.LEFT, padx=2)
        
        # Reference syntax info
        ttk.Button(btn_frame, text="ℹ️ Reference Syntax", 
                  command=self._show_ref_syntax).pack(side=tk.RIGHT, padx=2)
    
    def _populate_tree(self, filter_type='all', search=''):
        """Fyld tree med tags"""
        self.tree.delete(*self.tree.get_children())
        
        # Kategorier
        categories = {
            'element': ('🪟 GUI Elements', []),
            'action': ('⚡ Actions', []),
            'variable': ('📊 Variables', []),
            'control': ('🔄 Control Flow', []),
            'reference': ('🔗 References', []),
            'container': ('📦 Containers', [])
        }
        
        search_lower = search.lower()
        
        for tag_name, tag in self.registry.get_all_tags().items():
            # Filter
            if filter_type != 'all' and tag.tag_type != filter_type:
                continue
            
            # Search
            if search and search_lower not in tag_name.lower() and search_lower not in tag.description.lower():
                continue
            
            if tag.tag_type in categories:
                categories[tag.tag_type][1].append((tag_name, tag))
        
        # Tilføj til tree
        for cat_type, (cat_label, tags) in categories.items():
            if not tags:
                continue
            
            cat_id = self.tree.insert('', 'end', text=cat_label, open=True)
            
            for tag_name, tag in sorted(tags, key=lambda x: x[0]):
                tag_id = self.tree.insert(cat_id, 'end', text=f"<{tag_name}>",
                                         values=(tag.tag_type, tag.module),
                                         tags=('tag',))
                
                # Tilføj attributter
                if tag.attributes:
                    attr_id = self.tree.insert(tag_id, 'end', text="📝 Attributter")
                    for attr in tag.attributes:
                        req = "★" if attr.required else ""
                        self.tree.insert(attr_id, 'end', 
                                        text=f"{req}{attr.name}",
                                        values=(attr.attr_type, ''),
                                        tags=('attr',))
                
                # Tilføj metoder
                if tag.methods:
                    meth_id = self.tree.insert(tag_id, 'end', text="⚙️ Metoder")
                    for method in tag.methods:
                        self.tree.insert(meth_id, 'end',
                                        text=method.name,
                                        values=('method', ''),
                                        tags=('method',))
    
    def _on_search(self, *args):
        """Håndter søgning"""
        self._populate_tree(self.filter_var.get(), self.search_var.get())
    
    def _on_filter(self):
        """Håndter filter ændring"""
        self._populate_tree(self.filter_var.get(), self.search_var.get())
    
    def _on_select(self, event):
        """Håndter selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.tree.item(item, 'text')
        
        # Ryd detaljer
        self.details_text.config(state='normal')
        self.details_text.delete('1.0', tk.END)
        
        # Find tag
        if item_text.startswith('<') and item_text.endswith('>'):
            tag_name = item_text[1:-1]
            tag = self.registry.tags.get(tag_name)
            if tag:
                self._show_tag_details(tag)
        elif item_text.startswith('📝') or item_text.startswith('⚙️'):
            # Kategori header - vis parent tag
            parent = self.tree.parent(item)
            if parent:
                parent_text = self.tree.item(parent, 'text')
                if parent_text.startswith('<'):
                    tag_name = parent_text[1:-1]
                    tag = self.registry.tags.get(tag_name)
                    if tag:
                        self._show_tag_details(tag)
        
        self.details_text.config(state='disabled')
    
    def _show_tag_details(self, tag):
        """Vis detaljer for et tag"""
        t = self.details_text
        
        # Header
        t.insert('end', f"<{tag.name}>\n", 'header')
        t.insert('end', f"{tag.description}\n\n", 'desc')
        
        # Syntax
        t.insert('end', "Syntax:\n", 'subheader')
        t.insert('end', f"  {tag.syntax}\n\n", 'syntax')
        
        # Attributter
        if tag.attributes:
            t.insert('end', "Attributter:\n", 'subheader')
            for attr in tag.attributes:
                req = " (påkrævet)" if attr.required else ""
                default = f" = {attr.default}" if attr.default else ""
                t.insert('end', f"  • {attr.name}", 'attr')
                t.insert('end', f" : {attr.attr_type}", 'type')
                t.insert('end', f"{req}{default}\n", 'required' if attr.required else 'desc')
                if attr.description:
                    t.insert('end', f"      {attr.description}\n", 'desc')
                if attr.accepts_variable:
                    t.insert('end', f"      ✓ Kan bruge variabel: ", 'desc')
                    t.insert('end', f"{attr.name}=<var_value>\n", 'example')
            t.insert('end', '\n')
        
        # Metoder
        if tag.methods:
            t.insert('end', "Metoder:\n", 'subheader')
            for method in tag.methods:
                t.insert('end', f"  • {method.name}\n", 'attr')
                t.insert('end', f"      {method.syntax}\n", 'syntax')
                if method.description:
                    t.insert('end', f"      {method.description}\n", 'desc')
            t.insert('end', '\n')
        
        # Accepts references
        if tag.accepts_refs:
            t.insert('end', "Accepterer referencer fra:\n", 'subheader')
            for ref in tag.accepts_refs:
                t.insert('end', f"  • {ref}\n", 'desc')
            t.insert('end', '\n')
        
        # Eksempler
        t.insert('end', "Eksempler:\n", 'subheader')
        if tag.tag_type == 'element':
            t.insert('end', f"  # Opret {tag.name}\n", 'desc')
            t.insert('end', f"  {tag.syntax}\n", 'example')
            if tag.methods:
                t.insert('end', f"\n  # Brug metoder\n", 'desc')
                t.insert('end', f"  <myname_{tag.methods[0].name.split('_')[-1]}>\n", 'example')
        elif tag.tag_type == 'variable':
            t.insert('end', "  # Definer variabel\n", 'desc')
            t.insert('end', '  <var name="title" value="Hello">\n', 'example')
            t.insert('end', "\n  # Brug variabel\n", 'desc')
            t.insert('end', '  <window title=<title_value>>\n', 'example')
    
    def _on_double_click(self, event):
        """Håndter dobbeltklik - indsæt syntax"""
        self._insert_syntax()
    
    def _copy_syntax(self):
        """Kopier syntax til clipboard"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_text = self.tree.item(selection[0], 'text')
        if item_text.startswith('<') and item_text.endswith('>'):
            tag_name = item_text[1:-1]
            tag = self.registry.tags.get(tag_name)
            if tag:
                self.clipboard_clear()
                self.clipboard_append(tag.syntax)
    
    def _insert_syntax(self):
        """Indsæt syntax i editor"""
        if not self.editor_callback:
            return
        
        selection = self.tree.selection()
        if not selection:
            return
        
        item_text = self.tree.item(selection[0], 'text')
        if item_text.startswith('<') and item_text.endswith('>'):
            tag_name = item_text[1:-1]
            tag = self.registry.tags.get(tag_name)
            if tag:
                self.editor_callback(tag.syntax)
    
    def _show_ref_syntax(self):
        """Vis reference syntax info"""
        self.details_text.config(state='normal')
        self.details_text.delete('1.0', tk.END)
        
        t = self.details_text
        
        t.insert('end', "Reference Syntax Guide\n", 'header')
        t.insert('end', "Sådan bruger du referencer i PyTML\n\n", 'desc')
        
        for ref in self.registry.get_reference_syntax():
            t.insert('end', f"{ref['pattern']}\n", 'syntax')
            t.insert('end', f"  {ref['description']}\n", 'desc')
            t.insert('end', f"  Eksempel: ", 'desc')
            t.insert('end', f"{ref['example']}\n", 'example')
            t.insert('end', f"  Bruges i: {ref['can_use_in']}\n\n", 'desc')
        
        t.insert('end', "\nKombinationer:\n", 'subheader')
        t.insert('end', "  # Variabel i window title\n", 'desc')
        t.insert('end', '  <var name="title" value="Min App">\n', 'example')
        t.insert('end', '  <window title=<title_value> name="wnd1">\n\n', 'example')
        
        t.insert('end', "  # Variabel i button text\n", 'desc')
        t.insert('end', '  <var name="btn_label" value="Klik!">\n', 'example')
        t.insert('end', '  <button text=<btn_label_value> parent="wnd1">\n\n', 'example')
        
        t.insert('end', "  # Dynamisk position\n", 'desc')
        t.insert('end', '  <var name="xpos" value="100">\n', 'example')
        t.insert('end', '  <button x=<xpos_value> y="50">\n\n', 'example')
        
        self.details_text.config(state='disabled')


# Eksporter
__all__ = ['ReferencesPanel', 'ReferencesRegistry', 'TagInfo', 'AttributeInfo', 'MethodInfo']
