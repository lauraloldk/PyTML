"""
PyTML Editor Plugin: References Browser
Displays all allowed references, tags, methods, variables and properties
Helps developers see all combinations and possibilities
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
    """Information about a tag"""
    
    def __init__(self, name, tag_type, module, syntax, description=""):
        self.name = name
        self.tag_type = tag_type  # 'element', 'action', 'control', 'variable'
        self.module = module
        self.syntax = syntax
        self.description = description
        self.attributes = []  # List of AttributeInfo
        self.methods = []     # List of MethodInfo
        self.accepts_refs = []  # Which ref types can be used in this tag
        self.can_be_ref_in = []  # Where can this tag be referenced


class AttributeInfo:
    """Information about an attribute"""
    
    def __init__(self, name, attr_type, required=False, default=None, description=""):
        self.name = name
        self.attr_type = attr_type  # 'string', 'number', 'variable', 'element_ref'
        self.required = required
        self.default = default
        self.description = description
        self.accepts_variable = True  # Can use <var_value> or $var


class MethodInfo:
    """Information about a method/action"""
    
    def __init__(self, name, syntax, description=""):
        self.name = name
        self.syntax = syntax
        self.description = description
        self.parameters = []


class ReferencesRegistry:
    """Registry of all tags, methods and their relationships"""
    
    def __init__(self):
        self.tags = {}
        self.methods = {}
        self.variable_patterns = []
        self._load_all()
    
    def _load_all(self):
        """Load all tags and methods from libs"""
        self._load_builtin_tags()
        self._load_from_libs()
        self._analyze_relationships()
    
    def _load_builtin_tags(self):
        """Load built-in tags (var, output, control flow)"""
        # Variable tags
        var_tag = TagInfo('var', 'variable', 'var', '<var name="x" value="...">')
        var_tag.description = "Define a variable"
        var_tag.attributes = [
            AttributeInfo('name', 'string', required=True, description="Variable name"),
            AttributeInfo('value', 'any', required=False, description="Initial value")
        ]
        self.tags['var'] = var_tag
        
        # Variable value reference
        var_value = TagInfo('_value', 'reference', 'var', '<varname_value>')
        var_value.description = "Get the value of a variable"
        self.tags['_value'] = var_value
        
        # Output tag
        output_tag = TagInfo('output', 'action', 'output', '<output <var_value>> or <output "text">')
        output_tag.description = "Print output to console"
        output_tag.attributes = [
            AttributeInfo('value', 'any', required=True, description="Value or variable reference")
        ]
        output_tag.accepts_refs = ['variable']
        self.tags['output'] = output_tag
        
        # Control flow tags
        if_tag = TagInfo('if', 'control', 'builtin', '<if condition="...">')
        if_tag.description = "Conditional execution"
        if_tag.attributes = [
            AttributeInfo('condition', 'expression', required=True, description="Condition to evaluate")
        ]
        if_tag.accepts_refs = ['variable']
        self.tags['if'] = if_tag
        
        loop_tag = TagInfo('loop', 'control', 'builtin', '<loop count="n"> or <loop from="x" to="y">')
        loop_tag.description = "Repeat code"
        loop_tag.attributes = [
            AttributeInfo('count', 'number', description="Number of repetitions"),
            AttributeInfo('from', 'number', description="Start value"),
            AttributeInfo('to', 'number', description="End value"),
            AttributeInfo('var', 'string', default='i', description="Loop variable name")
        ]
        loop_tag.accepts_refs = ['variable']
        self.tags['loop'] = loop_tag
        
        block_tag = TagInfo('block', 'control', 'builtin', '<block name="...">')
        block_tag.description = "Group code in a named block"
        block_tag.attributes = [
            AttributeInfo('name', 'string', description="Block name")
        ]
        self.tags['block'] = block_tag
        
        # GUI block
        gui_tag = TagInfo('gui', 'container', 'builtin', '<gui>...</gui>')
        gui_tag.description = "Container for GUI elements"
        self.tags['gui'] = gui_tag
        
        # Console utils
        noterminate = TagInfo('noterminate', 'control', 'console_utils', '<noterminate>')
        noterminate.description = "Prevents the program from closing automatically"
        self.tags['noterminate'] = noterminate
    
    def _load_from_libs(self):
        """Load tags from lib files"""
        libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        
        for lib_file in glob.glob(os.path.join(libs_path, '*.py')):
            if lib_file.endswith('__init__.py'):
                continue
            self._analyze_lib_file(lib_file)
    
    def _analyze_lib_file(self, filepath):
        """Analyze a lib file for tags and methods"""
        module_name = os.path.basename(filepath)[:-3]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find syntax from docstring
            syntax_matches = re.findall(r'Syntax:\s*\n((?:\s+<[^>]+>\s*\n?)+)', content)
            
            # Find get_line_parsers patterns
            parser_patterns = re.findall(r"\(r'(<[^']+>)'", content)
            
            # Find GUI info
            if 'get_gui_info' in content:
                self._load_gui_info(filepath, module_name)
            
            # Analyze based on module name
            if module_name == 'window':
                self._add_window_tags()
            elif module_name == 'button':
                self._add_button_tags()
            elif module_name == 'label':
                self._add_label_tags()
            elif module_name == 'entry':
                self._add_entry_tags()
                
        except Exception as e:
            print(f"ReferencesRegistry: Error analyzing {filepath}: {e}")
    
    def _load_gui_info(self, filepath, module_name):
        """Load GUI info from a module"""
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'get_gui_info'):
                info = module.get_gui_info()
                # GUI info is already handled via _add_*_tags methods
        except:
            pass
    
    def _add_window_tags(self):
        """Add window tags"""
        window = TagInfo('window', 'element', 'window', '<window title="..." name="wnd1" size="300","200">')
        window.description = "Create a GUI window"
        window.attributes = [
            AttributeInfo('title', 'string', required=True, description="Window title"),
            AttributeInfo('name', 'string', required=True, description="Unique name for reference"),
            AttributeInfo('size', 'stack', description="Width,height in pixels")
        ]
        window.accepts_refs = ['variable']
        window.methods = [
            MethodInfo('show', '<name_show>', "Show the window"),
            MethodInfo('hide', '<name_hide>', "Hide the window"),
            MethodInfo('close', '<name_close>', "Close the window"),
            MethodInfo('title', '<name_title="...">', "Change title"),
            MethodInfo('size', '<name_size="w","h">', "Change size")
        ]
        self.tags['window'] = window
    
    def _add_button_tags(self):
        """Add button tags"""
        button = TagInfo('button', 'element', 'button', '<button text="..." name="btn1" parent="wnd1">')
        button.description = "Create a button in a window"
        button.attributes = [
            AttributeInfo('text', 'string', required=True, description="Button text"),
            AttributeInfo('name', 'string', required=True, description="Unique name for reference"),
            AttributeInfo('parent', 'element_ref', required=True, description="Parent window name"),
            AttributeInfo('x', 'number', default='0', description="X position"),
            AttributeInfo('y', 'number', default='0', description="Y position"),
            AttributeInfo('width', 'number', default='100', description="Width"),
            AttributeInfo('height', 'number', default='30', description="Height")
        ]
        button.accepts_refs = ['variable', 'window']
        button.methods = [
            MethodInfo('text', '<name_text="...">', "Change text"),
            MethodInfo('enabled', '<name_enabled="true/false">', "Enable/disable")
        ]
        self.tags['button'] = button
    
    def _add_label_tags(self):
        """Add label tags"""
        label = TagInfo('label', 'element', 'label', '<label text="..." name="lbl1" parent="wnd1">')
        label.description = "Create a text label in a window"
        label.attributes = [
            AttributeInfo('text', 'string', required=True, description="Label text"),
            AttributeInfo('name', 'string', required=True, description="Unique name for reference"),
            AttributeInfo('parent', 'element_ref', required=True, description="Parent window name"),
            AttributeInfo('x', 'number', default='0', description="X position"),
            AttributeInfo('y', 'number', default='0', description="Y position")
        ]
        label.accepts_refs = ['variable', 'window']
        label.methods = [
            MethodInfo('text', '<name_text="...">', "Change text")
        ]
        self.tags['label'] = label
    
    def _add_entry_tags(self):
        """Add entry tags"""
        entry = TagInfo('entry', 'element', 'entry', '<entry name="txt1" parent="wnd1">')
        entry.description = "Create a text field in a window"
        entry.attributes = [
            AttributeInfo('name', 'string', required=True, description="Unique name for reference"),
            AttributeInfo('parent', 'element_ref', required=True, description="Parent window name"),
            AttributeInfo('placeholder', 'string', description="Placeholder text"),
            AttributeInfo('x', 'number', default='0', description="X position"),
            AttributeInfo('y', 'number', default='0', description="Y position"),
            AttributeInfo('width', 'number', default='150', description="Width")
        ]
        entry.accepts_refs = ['variable', 'window']
        entry.methods = [
            MethodInfo('value', '<name_value="...">', "Set/get value"),
            MethodInfo('placeholder', '<name_placeholder="...">', "Change placeholder"),
            MethodInfo('readonly', '<name_readonly="true/false">', "Set readonly")
        ]
        self.tags['entry'] = entry
    
    def _analyze_relationships(self):
        """Analyze relationships between tags"""
        # Which tags can be referenced from which
        for tag_name, tag in self.tags.items():
            if tag.tag_type == 'element':
                # GUI elements can be referenced from other GUI elements
                tag.can_be_ref_in = ['button', 'label', 'entry', 'output']
            elif tag.tag_type == 'variable':
                # Variables can be referenced from almost anything
                tag.can_be_ref_in = list(self.tags.keys())
    
    def get_all_tags(self):
        """Get all tags"""
        return self.tags
    
    def get_tags_by_type(self, tag_type):
        """Get tags of a specific type"""
        return {k: v for k, v in self.tags.items() if v.tag_type == tag_type}
    
    def get_allowed_refs_for(self, tag_name):
        """Get allowed references for a tag"""
        tag = self.tags.get(tag_name)
        if tag:
            return tag.accepts_refs
        return []
    
    def get_reference_syntax(self):
        """Get all reference syntaxes"""
        return [
            {
                'pattern': '<varname_value>',
                'description': 'Reference to variable value',
                'example': '<title_value>',
                'can_use_in': 'All attributes that accept variables'
            },
            {
                'pattern': '$varname',
                'description': 'Alternative variable reference',
                'example': '$title',
                'can_use_in': 'Conditions, output, string interpolation'
            },
            {
                'pattern': '<elementname_method>',
                'description': 'Call method on element',
                'example': '<wnd1_show>',
                'can_use_in': 'Top-level actions'
            }
        ]


class ReferencesPanel(ttk.Frame):
    """Panel to display and explore all references"""
    
    def __init__(self, parent, editor_callback=None):
        super().__init__(parent)
        self.editor_callback = editor_callback
        self.registry = ReferencesRegistry()
        
        self._setup_ui()
        self._populate_tree()
    
    def _setup_ui(self):
        """Set up UI"""
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
            ('All', 'all'),
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
        self.tree.heading('Module', text='Module')
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
        details_frame = ttk.LabelFrame(paned, text="📋 Details")
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
        
        ttk.Button(btn_frame, text="📋 Copy Syntax", 
                  command=self._copy_syntax).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="➕ Insert in Editor", 
                  command=self._insert_syntax).pack(side=tk.LEFT, padx=2)
        
        # Reference syntax info
        ttk.Button(btn_frame, text="ℹ️ Reference Syntax", 
                  command=self._show_ref_syntax).pack(side=tk.RIGHT, padx=2)
    
    def _populate_tree(self, filter_type='all', search=''):
        """Fill tree with tags"""
        self.tree.delete(*self.tree.get_children())
        
        # Categories
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
        
        # Add to tree
        for cat_type, (cat_label, tags) in categories.items():
            if not tags:
                continue
            
            cat_id = self.tree.insert('', 'end', text=cat_label, open=True)
            
            for tag_name, tag in sorted(tags, key=lambda x: x[0]):
                tag_id = self.tree.insert(cat_id, 'end', text=f"<{tag_name}>",
                                         values=(tag.tag_type, tag.module),
                                         tags=('tag',))
                
                # Add attributes
                if tag.attributes:
                    attr_id = self.tree.insert(tag_id, 'end', text="📝 Attributes")
                    for attr in tag.attributes:
                        req = "★" if attr.required else ""
                        self.tree.insert(attr_id, 'end', 
                                        text=f"{req}{attr.name}",
                                        values=(attr.attr_type, ''),
                                        tags=('attr',))
                
                # Add methods
                if tag.methods:
                    meth_id = self.tree.insert(tag_id, 'end', text="⚙️ Methods")
                    for method in tag.methods:
                        self.tree.insert(meth_id, 'end',
                                        text=method.name,
                                        values=('method', ''),
                                        tags=('method',))
    
    def _on_search(self, *args):
        """Handle search"""
        self._populate_tree(self.filter_var.get(), self.search_var.get())
    
    def _on_filter(self):
        """Handle filter change"""
        self._populate_tree(self.filter_var.get(), self.search_var.get())
    
    def _on_select(self, event):
        """Handle selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.tree.item(item, 'text')
        
        # Clear details
        self.details_text.config(state='normal')
        self.details_text.delete('1.0', tk.END)
        
        # Find tag
        if item_text.startswith('<') and item_text.endswith('>'):
            tag_name = item_text[1:-1]
            tag = self.registry.tags.get(tag_name)
            if tag:
                self._show_tag_details(tag)
        elif item_text.startswith('📝') or item_text.startswith('⚙️'):
            # Category header - show parent tag
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
        """Show details for a tag"""
        t = self.details_text
        
        # Header
        t.insert('end', f"<{tag.name}>\n", 'header')
        t.insert('end', f"{tag.description}\n\n", 'desc')
        
        # Syntax
        t.insert('end', "Syntax:\n", 'subheader')
        t.insert('end', f"  {tag.syntax}\n\n", 'syntax')
        
        # Attributes
        if tag.attributes:
            t.insert('end', "Attributes:\n", 'subheader')
            for attr in tag.attributes:
                req = " (required)" if attr.required else ""
                default = f" = {attr.default}" if attr.default else ""
                t.insert('end', f"  • {attr.name}", 'attr')
                t.insert('end', f" : {attr.attr_type}", 'type')
                t.insert('end', f"{req}{default}\n", 'required' if attr.required else 'desc')
                if attr.description:
                    t.insert('end', f"      {attr.description}\n", 'desc')
                if attr.accepts_variable:
                    t.insert('end', f"      ✓ Can use variable: ", 'desc')
                    t.insert('end', f"{attr.name}=<var_value>\n", 'example')
            t.insert('end', '\n')
        
        # Methods
        if tag.methods:
            t.insert('end', "Methods:\n", 'subheader')
            for method in tag.methods:
                t.insert('end', f"  • {method.name}\n", 'attr')
                t.insert('end', f"      {method.syntax}\n", 'syntax')
                if method.description:
                    t.insert('end', f"      {method.description}\n", 'desc')
            t.insert('end', '\n')
        
        # Accepts references
        if tag.accepts_refs:
            t.insert('end', "Accepts references from:\n", 'subheader')
            for ref in tag.accepts_refs:
                t.insert('end', f"  • {ref}\n", 'desc')
            t.insert('end', '\n')
        
        # Examples
        t.insert('end', "Examples:\n", 'subheader')
        if tag.tag_type == 'element':
            t.insert('end', f"  # Create {tag.name}\n", 'desc')
            t.insert('end', f"  {tag.syntax}\n", 'example')
            if tag.methods:
                t.insert('end', f"\n  # Use methods\n", 'desc')
                t.insert('end', f"  <myname_{tag.methods[0].name.split('_')[-1]}>\n", 'example')
        elif tag.tag_type == 'variable':
            t.insert('end', "  # Define variable\n", 'desc')
            t.insert('end', '  <var name="title" value="Hello">\n', 'example')
            t.insert('end', "\n  # Use variable\n", 'desc')
            t.insert('end', '  <window title=<title_value>>\n', 'example')
    
    def _on_double_click(self, event):
        """Handle double-click - insert syntax"""
        self._insert_syntax()
    
    def _copy_syntax(self):
        """Copy syntax to clipboard"""
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
        """Insert syntax in editor"""
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
        """Show reference syntax info"""
        self.details_text.config(state='normal')
        self.details_text.delete('1.0', tk.END)
        
        t = self.details_text
        
        t.insert('end', "Reference Syntax Guide\n", 'header')
        t.insert('end', "How to use references in PyTML\n\n", 'desc')
        
        for ref in self.registry.get_reference_syntax():
            t.insert('end', f"{ref['pattern']}\n", 'syntax')
            t.insert('end', f"  {ref['description']}\n", 'desc')
            t.insert('end', f"  Example: ", 'desc')
            t.insert('end', f"{ref['example']}\n", 'example')
            t.insert('end', f"  Used in: {ref['can_use_in']}\n\n", 'desc')
        
        t.insert('end', "\nCombinations:\n", 'subheader')
        t.insert('end', "  # Variable in window title\n", 'desc')
        t.insert('end', '  <var name="title" value="My App">\n', 'example')
        t.insert('end', '  <window title=<title_value> name="wnd1">\n\n', 'example')
        
        t.insert('end', "  # Variable in button text\n", 'desc')
        t.insert('end', '  <var name="btn_label" value="Click!">\n', 'example')
        t.insert('end', '  <button text=<btn_label_value> parent="wnd1">\n\n', 'example')
        
        t.insert('end', "  # Dynamic position\n", 'desc')
        t.insert('end', '  <var name="xpos" value="100">\n', 'example')
        t.insert('end', '  <button x=<xpos_value> y="50">\n\n', 'example')
        
        self.details_text.config(state='disabled')


# Export
__all__ = ['ReferencesPanel', 'ReferencesRegistry', 'TagInfo', 'AttributeInfo', 'MethodInfo']
