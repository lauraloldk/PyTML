"""
PyTML Editor Plugin: Visual Programming Mode
=============================================
Scratch-like visual block programming interface that dynamically
loads block definitions from the libs folder.

Features:
- Drag-and-drop visual blocks
- Blocks are dynamically generated from libs
- Snap-together block connections
- Real-time code generation
- Color-coded categories (like Scratch)
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import os
import sys
import glob
import importlib.util
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum, auto


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# BLOCK CATEGORIES AND COLORS (Scratch-style)
# =============================================================================

class BlockCategory(Enum):
    """Categories for visual blocks with Scratch-like colors"""
    EVENTS = auto()      # When something happens
    CONTROL = auto()     # Control flow (if, loop, forever)
    VARIABLES = auto()   # Variable operations
    GUI = auto()         # GUI elements (window, button, label)
    OUTPUT = auto()      # Output/Print
    INPUT = auto()       # User input
    MATH = auto()        # Math operations
    RANDOM = auto()      # Random numbers


CATEGORY_COLORS = {
    BlockCategory.EVENTS: {'bg': '#FFBF00', 'fg': '#000000', 'highlight': '#FFD700'},
    BlockCategory.CONTROL: {'bg': '#FFAB19', 'fg': '#000000', 'highlight': '#FFC04D'},
    BlockCategory.VARIABLES: {'bg': '#FF8C1A', 'fg': '#FFFFFF', 'highlight': '#FFA64D'},
    BlockCategory.GUI: {'bg': '#4C97FF', 'fg': '#FFFFFF', 'highlight': '#6FA8FF'},
    BlockCategory.OUTPUT: {'bg': '#9966FF', 'fg': '#FFFFFF', 'highlight': '#B399FF'},
    BlockCategory.INPUT: {'bg': '#5CB1D6', 'fg': '#FFFFFF', 'highlight': '#7EC8E3'},
    BlockCategory.MATH: {'bg': '#59C059', 'fg': '#FFFFFF', 'highlight': '#7ED67E'},
    BlockCategory.RANDOM: {'bg': '#40BF4A', 'fg': '#FFFFFF', 'highlight': '#66CC70'},
}


# =============================================================================
# BLOCK DEFINITIONS
# =============================================================================

@dataclass
class BlockParameter:
    """A parameter/slot in a visual block"""
    name: str
    param_type: str  # 'string', 'number', 'variable', 'dropdown'
    default: Any = ""
    options: List[str] = field(default_factory=list)  # For dropdown
    placeholder: str = ""
    
    def __post_init__(self):
        if not self.placeholder:
            self.placeholder = self.name


@dataclass
class BlockDefinition:
    """Definition of a visual block"""
    name: str
    display_name: str
    category: BlockCategory
    syntax_template: str  # PyTML syntax with {param} placeholders
    parameters: List[BlockParameter] = field(default_factory=list)
    
    # Block shape
    is_hat: bool = False      # Hat block (event starter)
    is_cap: bool = False      # Cap block (cannot connect below)
    is_reporter: bool = False # Reporter block (returns value, oval shape)
    is_boolean: bool = False  # Boolean block (hexagonal shape)
    is_c_block: bool = False  # C-shaped block (contains other blocks)
    
    # Source info
    module: str = ""
    description: str = ""
    
    def generate_code(self, param_values: Dict[str, Any]) -> str:
        """Generate PyTML code from parameter values"""
        code = self.syntax_template
        for param in self.parameters:
            value = param_values.get(param.name, param.default)
            code = code.replace(f"{{{param.name}}}", str(value))
        return code


# =============================================================================
# VISUAL BLOCK WIDGET
# =============================================================================

class VisualBlock(tk.Frame):
    """A single visual programming block that can be dragged"""
    
    CONNECTOR_HEIGHT = 8
    NOTCH_WIDTH = 20
    
    def __init__(self, parent, block_def: BlockDefinition, 
                 on_drag=None, on_drop=None, on_delete=None, 
                 on_code_change=None, **kwargs):
        self.block_def = block_def
        self.on_drag = on_drag
        self.on_drop = on_drop
        self.on_delete = on_delete
        self.on_code_change = on_code_change
        
        colors = CATEGORY_COLORS.get(block_def.category, CATEGORY_COLORS[BlockCategory.CONTROL])
        self.bg_color = colors['bg']
        self.fg_color = colors['fg']
        self.highlight_color = colors['highlight']
        
        super().__init__(parent, bg=self.bg_color, **kwargs)
        
        self.param_widgets = {}  # name -> widget
        self.child_blocks = []   # For C-blocks
        self.next_block = None   # Connected block below
        self.prev_block = None   # Block above
        
        self._drag_data = {'x': 0, 'y': 0}
        
        self._create_block()
        self._setup_drag()
    
    def _create_block(self):
        """Create the visual components of the block"""
        # Main content frame
        content = tk.Frame(self, bg=self.bg_color)
        content.pack(fill=tk.X, padx=8, pady=4)
        
        # Parse display name and create widgets for each parameter
        parts = self._parse_display_template()
        
        for part in parts:
            if part['type'] == 'text':
                lbl = tk.Label(content, text=part['value'], 
                             bg=self.bg_color, fg=self.fg_color,
                             font=('Segoe UI', 10, 'bold'))
                lbl.pack(side=tk.LEFT, padx=2)
            
            elif part['type'] == 'param':
                param = part['param']
                widget = self._create_param_widget(content, param)
                self.param_widgets[param.name] = widget
        
        # Top connector (notch) unless it's a hat block
        if not self.block_def.is_hat and not self.block_def.is_reporter:
            self._draw_top_notch()
        
        # Bottom connector unless it's a cap or reporter block
        if not self.block_def.is_cap and not self.block_def.is_reporter:
            self._draw_bottom_connector()
        
        # C-block inner area
        if self.block_def.is_c_block:
            self._create_c_block_slot()
    
    def _parse_display_template(self) -> List[Dict]:
        """Parse display name into text parts and parameter slots"""
        parts = []
        display = self.block_def.display_name
        
        # Find all {param} placeholders
        pattern = r'\{(\w+)\}'
        last_end = 0
        
        for match in re.finditer(pattern, display):
            # Text before the parameter
            if match.start() > last_end:
                parts.append({'type': 'text', 'value': display[last_end:match.start()]})
            
            # The parameter
            param_name = match.group(1)
            param = next((p for p in self.block_def.parameters if p.name == param_name), None)
            if param:
                parts.append({'type': 'param', 'param': param})
            else:
                parts.append({'type': 'text', 'value': match.group(0)})
            
            last_end = match.end()
        
        # Remaining text
        if last_end < len(display):
            parts.append({'type': 'text', 'value': display[last_end:]})
        
        return parts
    
    def _create_param_widget(self, parent, param: BlockParameter) -> tk.Widget:
        """Create appropriate widget for a parameter"""
        if param.param_type == 'dropdown':
            var = tk.StringVar(value=param.default or param.options[0] if param.options else '')
            widget = ttk.Combobox(parent, textvariable=var, values=param.options, 
                                 width=12, state='readonly')
            widget.var = var
            widget.bind('<<ComboboxSelected>>', lambda e: self._on_param_change())
        
        elif param.param_type == 'number':
            var = tk.StringVar(value=str(param.default or 0))
            widget = tk.Entry(parent, textvariable=var, width=6, 
                            bg='white', fg='black',
                            relief='flat', borderwidth=2)
            widget.var = var
            widget.bind('<KeyRelease>', lambda e: self._on_param_change())
        
        else:  # string
            var = tk.StringVar(value=str(param.default or ''))
            widget = tk.Entry(parent, textvariable=var, width=15,
                            bg='white', fg='black',
                            relief='flat', borderwidth=2)
            widget.var = var
            widget.insert(0, param.placeholder if not param.default else '')
            widget.bind('<FocusIn>', lambda e: self._on_entry_focus(widget, param))
            widget.bind('<FocusOut>', lambda e: self._on_entry_blur(widget, param))
            widget.bind('<KeyRelease>', lambda e: self._on_param_change())
        
        widget.pack(side=tk.LEFT, padx=2)
        return widget
    
    def _on_entry_focus(self, entry, param):
        """Clear placeholder on focus"""
        if entry.get() == param.placeholder:
            entry.delete(0, tk.END)
    
    def _on_entry_blur(self, entry, param):
        """Restore placeholder if empty"""
        if not entry.get():
            entry.insert(0, param.placeholder)
    
    def _on_param_change(self):
        """Called when any parameter changes"""
        if self.on_code_change:
            self.on_code_change()
    
    def _draw_top_notch(self):
        """Draw the top notch (indent) for connecting to block above"""
        pass  # Simple frame doesn't need this - use canvas for complex shapes
    
    def _draw_bottom_connector(self):
        """Draw the bottom connector (bump) for connecting to block below"""
        pass  # Simple frame doesn't need this
    
    def _create_c_block_slot(self):
        """Create inner slot for C-shaped blocks"""
        self.inner_frame = tk.Frame(self, bg='#2d2d2d', height=40)
        self.inner_frame.pack(fill=tk.X, padx=15, pady=2)
        
        # Bottom bar of C-block
        bottom = tk.Frame(self, bg=self.bg_color, height=10)
        bottom.pack(fill=tk.X)
    
    def _setup_drag(self):
        """Setup drag and drop bindings"""
        self.bind('<Button-1>', self._on_press)
        self.bind('<B1-Motion>', self._on_motion)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Button-3>', self._on_right_click)
        
        # Also bind children
        for child in self.winfo_children():
            child.bind('<Button-1>', lambda e: self._on_press(e, from_child=True))
            child.bind('<B1-Motion>', self._on_motion)
            child.bind('<ButtonRelease-1>', self._on_release)
    
    def _on_press(self, event, from_child=False):
        """Start dragging"""
        # Don't start drag from entry widgets
        if isinstance(event.widget, (tk.Entry, ttk.Combobox)):
            return
        
        self._drag_data['x'] = event.x
        self._drag_data['y'] = event.y
        self.lift()  # Bring to front
        
        if self.on_drag:
            self.on_drag(self, event)
    
    def _on_motion(self, event):
        """Handle drag motion"""
        if isinstance(event.widget, (tk.Entry, ttk.Combobox)):
            return
        
        # Calculate movement
        dx = event.x - self._drag_data['x']
        dy = event.y - self._drag_data['y']
        
        # Get current position
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        
        # Move the block
        self.place(x=x, y=y)
    
    def _on_release(self, event):
        """Handle drop"""
        if isinstance(event.widget, (tk.Entry, ttk.Combobox)):
            return
        
        if self.on_drop:
            self.on_drop(self, event)
    
    def _on_right_click(self, event):
        """Show context menu"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="🗑️ Delete Block", command=self._delete)
        menu.add_command(label="📋 Duplicate", command=self._duplicate)
        menu.tk_popup(event.x_root, event.y_root)
    
    def _delete(self):
        """Delete this block"""
        if self.on_delete:
            self.on_delete(self)
        self.destroy()
    
    def _duplicate(self):
        """Duplicate this block"""
        # TODO: Implement duplication
        pass
    
    def get_code(self) -> str:
        """Generate PyTML code from current parameter values"""
        values = {}
        for name, widget in self.param_widgets.items():
            value = widget.var.get()
            # Clean up placeholder text
            param = next((p for p in self.block_def.parameters if p.name == name), None)
            if param and value == param.placeholder:
                value = param.default or ''
            values[name] = value
        
        return self.block_def.generate_code(values)
    
    def get_full_code(self) -> str:
        """Get code including connected blocks"""
        code_lines = [self.get_code()]
        
        # Add inner blocks (for C-blocks)
        for child in self.child_blocks:
            code_lines.append("    " + child.get_full_code().replace("\n", "\n    "))
        
        # Add closing tag for C-blocks
        if self.block_def.is_c_block:
            tag = self.block_def.name.lower()
            code_lines.append(f"</{tag}>")
        
        # Add next block
        if self.next_block:
            code_lines.append(self.next_block.get_full_code())
        
        return '\n'.join(code_lines)


# =============================================================================
# BLOCK LIBRARY - DYNAMIC LOADING FROM LIBS
# =============================================================================

class BlockLibrary:
    """Dynamically loads block definitions from libs folder"""
    
    def __init__(self):
        self.blocks: Dict[BlockCategory, List[BlockDefinition]] = {cat: [] for cat in BlockCategory}
        self.all_blocks: List[BlockDefinition] = []
    
    def load_from_libs(self):
        """Scan libs folder and create block definitions"""
        self.blocks = {cat: [] for cat in BlockCategory}
        self.all_blocks = []
        
        libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        
        # Load built-in blocks first
        self._add_builtin_blocks()
        
        # Scan lib files
        for lib_file in glob.glob(os.path.join(libs_path, '*.py')):
            if lib_file.endswith('__init__.py'):
                continue
            self._load_from_lib(lib_file)
    
    def _add_builtin_blocks(self):
        """Add built-in control flow blocks"""
        # Event blocks
        self._add_block(BlockDefinition(
            name='forever',
            display_name='🔄 forever interval {interval} ms',
            category=BlockCategory.EVENTS,
            syntax_template='<forever interval="{interval}">',
            parameters=[
                BlockParameter('interval', 'number', default='100')
            ],
            is_hat=True,
            is_c_block=True,
            description='Run blocks forever with interval'
        ))
        
        # Control blocks
        self._add_block(BlockDefinition(
            name='if',
            display_name='🔀 if {condition}',
            category=BlockCategory.CONTROL,
            syntax_template='<if {condition}>',
            parameters=[
                BlockParameter('condition', 'string', placeholder='event="<btn_click>"')
            ],
            is_c_block=True,
            description='Conditional block'
        ))
        
        self._add_block(BlockDefinition(
            name='loop',
            display_name='🔁 loop {count} times',
            category=BlockCategory.CONTROL,
            syntax_template='<loop count="{count}">',
            parameters=[
                BlockParameter('count', 'number', default='10')
            ],
            is_c_block=True,
            description='Loop a specific number of times'
        ))
        
        # Output blocks
        self._add_block(BlockDefinition(
            name='output',
            display_name='📝 print {text}',
            category=BlockCategory.OUTPUT,
            syntax_template='<output text="{text}">',
            parameters=[
                BlockParameter('text', 'string', placeholder='Hello!')
            ],
            description='Print text to output'
        ))
        
        # Math blocks
        self._add_block(BlockDefinition(
            name='math_add',
            display_name='➕ {var} += {value}',
            category=BlockCategory.MATH,
            syntax_template='<{var}_value += {value}>',
            parameters=[
                BlockParameter('var', 'string', placeholder='counter'),
                BlockParameter('value', 'number', default='1')
            ],
            description='Add to variable'
        ))
        
        self._add_block(BlockDefinition(
            name='math_sub',
            display_name='➖ {var} -= {value}',
            category=BlockCategory.MATH,
            syntax_template='<{var}_value -= {value}>',
            parameters=[
                BlockParameter('var', 'string', placeholder='counter'),
                BlockParameter('value', 'number', default='1')
            ],
            description='Subtract from variable'
        ))
        
        self._add_block(BlockDefinition(
            name='math_inc',
            display_name='⬆️ {var}++',
            category=BlockCategory.MATH,
            syntax_template='<{var}_value++>',
            parameters=[
                BlockParameter('var', 'string', placeholder='counter')
            ],
            description='Increment variable by 1'
        ))
    
    def _add_block(self, block_def: BlockDefinition):
        """Add a block definition to the library"""
        self.blocks[block_def.category].append(block_def)
        self.all_blocks.append(block_def)
    
    def _load_from_lib(self, filepath):
        """Load block definitions from a lib file"""
        module_name = os.path.basename(filepath)[:-3]
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check for visual block definitions
            if hasattr(module, 'get_visual_blocks'):
                for block_def in module.get_visual_blocks():
                    self._add_block(block_def)
            else:
                # Auto-generate blocks from module info
                self._auto_generate_blocks(module, module_name)
                
        except Exception as e:
            print(f"BlockLibrary: Could not load {filepath}: {e}")
    
    def _auto_generate_blocks(self, module, module_name: str):
        """Auto-generate block definitions from a lib module"""
        
        # Map module names to categories
        category_map = {
            'var': BlockCategory.VARIABLES,
            'variable': BlockCategory.VARIABLES,
            'window': BlockCategory.GUI,
            'button': BlockCategory.GUI,
            'label': BlockCategory.GUI,
            'entry': BlockCategory.GUI,
            'input': BlockCategory.INPUT,
            'output': BlockCategory.OUTPUT,
            'console_utils': BlockCategory.OUTPUT,
            'random': BlockCategory.RANDOM,
        }
        
        category = category_map.get(module_name, BlockCategory.CONTROL)
        
        # Icons per category
        icons = {
            BlockCategory.VARIABLES: '📦',
            BlockCategory.GUI: '🖼️',
            BlockCategory.INPUT: '⌨️',
            BlockCategory.OUTPUT: '📤',
            BlockCategory.RANDOM: '🎲',
            BlockCategory.CONTROL: '⚙️',
        }
        icon = icons.get(category, '🔹')
        
        # Look for docstring with syntax examples
        if module.__doc__:
            # Extract syntax examples from docstring
            syntax_matches = re.findall(r'<([^>]+)>', module.__doc__)
            
            for syntax in syntax_matches[:3]:  # Limit to 3 blocks per module
                # Parse the syntax to create a block
                block = self._parse_syntax_to_block(syntax, module_name, category, icon)
                if block:
                    self._add_block(block)
        
        # Generate blocks for main classes
        if module_name == 'var':
            self._add_block(BlockDefinition(
                name='var',
                display_name=f'{icon} set {"{name}"} = {"{value}"}',
                category=category,
                syntax_template='<var name="{name}" value="{value}">',
                parameters=[
                    BlockParameter('name', 'string', placeholder='myVar'),
                    BlockParameter('value', 'string', placeholder='0')
                ],
                module=module_name,
                description='Create a variable'
            ))
        
        elif module_name == 'window':
            self._add_block(BlockDefinition(
                name='window',
                display_name=f'{icon} window {"{name}"} title {"{title}"} size {"{width}"},{"{height}"}',
                category=category,
                syntax_template='<window title="{title}" size="{width}","{height}" name="{name}">',
                parameters=[
                    BlockParameter('name', 'string', placeholder='wnd1'),
                    BlockParameter('title', 'string', placeholder='My Window'),
                    BlockParameter('width', 'number', default='400'),
                    BlockParameter('height', 'number', default='300')
                ],
                module=module_name,
                description='Create a window'
            ))
            
            self._add_block(BlockDefinition(
                name='window_show',
                display_name=f'{icon} show window {"{name}"}',
                category=category,
                syntax_template='<{name}_show>',
                parameters=[
                    BlockParameter('name', 'string', placeholder='wnd1')
                ],
                module=module_name,
                description='Show a window'
            ))
        
        elif module_name == 'button':
            self._add_block(BlockDefinition(
                name='button',
                display_name=f'{icon} button {"{name}"} text {"{text}"} at {"{x}"},{"{y}"}',
                category=category,
                syntax_template='<button text="{text}" name="{name}" parent="{parent}" x="{x}" y="{y}">',
                parameters=[
                    BlockParameter('name', 'string', placeholder='btn1'),
                    BlockParameter('text', 'string', placeholder='Click Me'),
                    BlockParameter('parent', 'string', placeholder='wnd1'),
                    BlockParameter('x', 'number', default='10'),
                    BlockParameter('y', 'number', default='10')
                ],
                module=module_name,
                description='Create a button'
            ))
            
            self._add_block(BlockDefinition(
                name='button_click',
                display_name=f'{icon} when {"{name}"} clicked',
                category=BlockCategory.EVENTS,
                syntax_template='event="<{name}_click>"',
                parameters=[
                    BlockParameter('name', 'string', placeholder='btn1')
                ],
                is_reporter=True,
                module=module_name,
                description='Button click event'
            ))
        
        elif module_name == 'label':
            self._add_block(BlockDefinition(
                name='label',
                display_name=f'{icon} label {"{name}"} text {"{text}"} at {"{x}"},{"{y}"}',
                category=category,
                syntax_template='<label text="{text}" name="{name}" parent="{parent}" x="{x}" y="{y}">',
                parameters=[
                    BlockParameter('name', 'string', placeholder='lbl1'),
                    BlockParameter('text', 'string', placeholder='Hello'),
                    BlockParameter('parent', 'string', placeholder='wnd1'),
                    BlockParameter('x', 'number', default='10'),
                    BlockParameter('y', 'number', default='50')
                ],
                module=module_name,
                description='Create a label'
            ))
            
            self._add_block(BlockDefinition(
                name='label_set',
                display_name=f'{icon} set {"{name}"} text to {"{text}"}',
                category=category,
                syntax_template='<{name}_text="{text}">',
                parameters=[
                    BlockParameter('name', 'string', placeholder='lbl1'),
                    BlockParameter('text', 'string', placeholder='New text')
                ],
                module=module_name,
                description='Set label text'
            ))
        
        elif module_name == 'entry':
            self._add_block(BlockDefinition(
                name='entry',
                display_name=f'{icon} entry {"{name}"} at {"{x}"},{"{y}"}',
                category=category,
                syntax_template='<entry name="{name}" parent="{parent}" x="{x}" y="{y}" width="{width}">',
                parameters=[
                    BlockParameter('name', 'string', placeholder='input1'),
                    BlockParameter('parent', 'string', placeholder='wnd1'),
                    BlockParameter('x', 'number', default='10'),
                    BlockParameter('y', 'number', default='90'),
                    BlockParameter('width', 'number', default='200')
                ],
                module=module_name,
                description='Create text input'
            ))
        
        elif module_name == 'random':
            self._add_block(BlockDefinition(
                name='random',
                display_name=f'{icon} random {"{name}"} from {"{min}"} to {"{max}"}',
                category=category,
                syntax_template='<random name="{name}" from="{min}" to="{max}">',
                parameters=[
                    BlockParameter('name', 'string', placeholder='rnd'),
                    BlockParameter('min', 'number', default='1'),
                    BlockParameter('max', 'number', default='100')
                ],
                module=module_name,
                description='Create random number generator'
            ))
            
            self._add_block(BlockDefinition(
                name='random_value',
                display_name=f'{icon} get {"{name}"} random number',
                category=category,
                syntax_template='<{name}_random>',
                parameters=[
                    BlockParameter('name', 'string', placeholder='rnd')
                ],
                is_reporter=True,
                module=module_name,
                description='Get random number'
            ))
    
    def _parse_syntax_to_block(self, syntax: str, module_name: str, 
                               category: BlockCategory, icon: str) -> Optional[BlockDefinition]:
        """Parse a PyTML syntax string into a block definition"""
        # This is a simplified parser - can be extended
        # Example: 'var name="counter" value="0"'
        
        parts = syntax.split()
        if not parts:
            return None
        
        tag = parts[0]
        
        # Find attributes
        params = []
        attr_pattern = r'(\w+)="([^"]*)"'
        for match in re.finditer(attr_pattern, syntax):
            name = match.group(1)
            default = match.group(2)
            params.append(BlockParameter(name, 'string', default=default, placeholder=default or name))
        
        if not params:
            return None
        
        # Create display name
        display_parts = [f'{icon} {tag}']
        for param in params:
            display_parts.append(f'{param.name} {{{param.name}}}')
        
        return BlockDefinition(
            name=f'{module_name}_{tag}',
            display_name=' '.join(display_parts),
            category=category,
            syntax_template=f'<{syntax}>',
            parameters=params,
            module=module_name
        )
    
    def get_by_category(self, category: BlockCategory) -> List[BlockDefinition]:
        """Get all blocks in a category"""
        return self.blocks.get(category, [])
    
    def get_all(self) -> List[BlockDefinition]:
        """Get all blocks"""
        return self.all_blocks


# =============================================================================
# VISUAL PROGRAMMING PANEL
# =============================================================================

class VisualProgrammingPanel(ttk.Frame):
    """Main panel for visual block programming"""
    
    def __init__(self, parent, on_code_change: Callable[[str], None] = None):
        super().__init__(parent)
        
        self.on_code_change = on_code_change
        self.library = BlockLibrary()
        self.library.load_from_libs()
        
        self.blocks = []  # All blocks in workspace
        self.preserved_lines = []  # Lines that weren't matched to blocks (index, line)
        self.block_line_indices = set()  # Line indices that became blocks
        self._original_line_count = 0  # Track original number of lines
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI with palette and workspace"""
        # Main horizontal pane
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Block Palette (categorized like Scratch)
        self.palette_frame = ttk.Frame(self.paned)
        self.paned.add(self.palette_frame, weight=1)
        
        self._setup_palette()
        
        # Right side: Workspace (canvas for blocks)
        workspace_frame = ttk.Frame(self.paned)
        self.paned.add(workspace_frame, weight=4)
        
        self._setup_workspace(workspace_frame)
    
    def _setup_palette(self):
        """Setup the block palette with categories"""
        # Category buttons at top
        cat_frame = ttk.Frame(self.palette_frame)
        cat_frame.pack(fill=tk.X, pady=5)
        
        self.category_var = tk.StringVar(value=BlockCategory.GUI.name)
        
        # Create category tabs (2 per row)
        row_frame = None
        for i, cat in enumerate(BlockCategory):
            if i % 2 == 0:
                row_frame = ttk.Frame(cat_frame)
                row_frame.pack(fill=tk.X)
            
            colors = CATEGORY_COLORS.get(cat, CATEGORY_COLORS[BlockCategory.CONTROL])
            
            btn = tk.Button(row_frame, text=cat.name.title(),
                          bg=colors['bg'], fg=colors['fg'],
                          activebackground=colors['highlight'],
                          font=('Segoe UI', 9),
                          command=lambda c=cat: self._select_category(c))
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1, pady=1)
        
        # Separator
        ttk.Separator(self.palette_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Block list area (scrollable)
        self.palette_canvas = tk.Canvas(self.palette_frame, bg='#2d2d2d', 
                                        highlightthickness=0, width=220)
        self.palette_scrollbar = ttk.Scrollbar(self.palette_frame, orient=tk.VERTICAL,
                                               command=self.palette_canvas.yview)
        self.palette_inner = tk.Frame(self.palette_canvas, bg='#2d2d2d')
        
        self.palette_canvas.configure(yscrollcommand=self.palette_scrollbar.set)
        
        self.palette_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.palette_window = self.palette_canvas.create_window(
            (0, 0), window=self.palette_inner, anchor='nw'
        )
        
        self.palette_inner.bind('<Configure>', self._on_palette_configure)
        self.palette_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scrolling
        self.palette_canvas.bind('<MouseWheel>', self._on_palette_scroll)
        self.palette_inner.bind('<MouseWheel>', self._on_palette_scroll)
        
        # Load initial category
        self._select_category(BlockCategory.GUI)
    
    def _on_palette_configure(self, event):
        """Update scroll region when palette content changes"""
        self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        """Adjust inner frame width to canvas"""
        self.palette_canvas.itemconfig(self.palette_window, width=event.width)
    
    def _on_palette_scroll(self, event):
        """Handle mouse wheel scrolling"""
        self.palette_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def _select_category(self, category: BlockCategory):
        """Show blocks for selected category"""
        self.category_var.set(category.name)
        
        # Clear current blocks
        for child in self.palette_inner.winfo_children():
            child.destroy()
        
        # Add blocks for this category
        blocks = self.library.get_by_category(category)
        
        for block_def in blocks:
            self._add_palette_block(block_def)
    
    def _add_palette_block(self, block_def: BlockDefinition):
        """Add a block template to the palette"""
        colors = CATEGORY_COLORS.get(block_def.category, CATEGORY_COLORS[BlockCategory.CONTROL])
        
        # Create a simplified block preview
        frame = tk.Frame(self.palette_inner, bg=colors['bg'], cursor='hand2')
        frame.pack(fill=tk.X, padx=5, pady=3)
        
        # Parse display name for preview (without entry widgets)
        display = block_def.display_name
        display = re.sub(r'\{(\w+)\}', r'[\1]', display)  # Replace {param} with [param]
        
        lbl = tk.Label(frame, text=display, 
                      bg=colors['bg'], fg=colors['fg'],
                      font=('Segoe UI', 9, 'bold'),
                      anchor='w', padx=8, pady=6)
        lbl.pack(fill=tk.X)
        
        # Bind click to create block in workspace
        frame.bind('<Button-1>', lambda e, bd=block_def: self._spawn_block(bd))
        lbl.bind('<Button-1>', lambda e, bd=block_def: self._spawn_block(bd))
        
        # Bind double-click for quick add
        frame.bind('<Double-Button-1>', lambda e, bd=block_def: self._quick_add_block(bd))
        lbl.bind('<Double-Button-1>', lambda e, bd=block_def: self._quick_add_block(bd))
    
    def _setup_workspace(self, parent):
        """Setup the workspace area where blocks are placed"""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="🗑️ Clear All", command=self._clear_workspace).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📋 Insert Code", command=self._insert_code).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 Refresh Libs", command=self._refresh_libs).pack(side=tk.LEFT, padx=2)
        
        # Info label
        info = ttk.Label(toolbar, text="ℹ️ Visual is non-destructive - use 'Insert Code' to add blocks", 
                        font=('Segoe UI', 8), foreground='gray')
        info.pack(side=tk.RIGHT, padx=10)
        
        # Workspace canvas with scrolling
        ws_container = ttk.Frame(parent)
        ws_container.pack(fill=tk.BOTH, expand=True)
        
        self.workspace = tk.Canvas(ws_container, bg='#1e1e1e', 
                                   highlightthickness=0,
                                   scrollregion=(0, 0, 2000, 2000))
        
        h_scroll = ttk.Scrollbar(ws_container, orient=tk.HORIZONTAL, 
                                command=self.workspace.xview)
        v_scroll = ttk.Scrollbar(ws_container, orient=tk.VERTICAL,
                                command=self.workspace.yview)
        
        self.workspace.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.workspace.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Draw grid pattern
        self._draw_grid()
        
        # Help text
        help_text = self.workspace.create_text(
            100, 30, 
            text="Click blocks in the palette to add them here\nDrag blocks to arrange • Right-click to delete",
            fill='#666666', font=('Segoe UI', 10), anchor='nw'
        )
    
    def _draw_grid(self):
        """Draw grid pattern on workspace"""
        for x in range(0, 2000, 20):
            self.workspace.create_line(x, 0, x, 2000, fill='#2a2a2a', tags='grid')
        for y in range(0, 2000, 20):
            self.workspace.create_line(0, y, 2000, y, fill='#2a2a2a', tags='grid')
    
    def _spawn_block(self, block_def: BlockDefinition):
        """Create a new block in the workspace"""
        # Calculate position (stagger new blocks)
        x = 50 + (len(self.blocks) % 5) * 20
        y = 80 + (len(self.blocks) % 10) * 50
        
        # Create the block widget
        block = VisualBlock(
            self.workspace, 
            block_def,
            on_drag=self._on_block_drag,
            on_drop=self._on_block_drop,
            on_delete=self._on_block_delete,
            on_code_change=self._on_code_update
        )
        
        # Place on workspace
        self.workspace.create_window(x, y, window=block, anchor='nw', tags='block')
        self.blocks.append(block)
        
        # Update code
        self._on_code_update()
    
    def _quick_add_block(self, block_def: BlockDefinition):
        """Quick add block at end of script"""
        # Find the last block and place below it
        y = 80
        if self.blocks:
            last_block = self.blocks[-1]
            y = last_block.winfo_y() + last_block.winfo_height() + 10
        
        block = VisualBlock(
            self.workspace,
            block_def,
            on_drag=self._on_block_drag,
            on_drop=self._on_block_drop,
            on_delete=self._on_block_delete,
            on_code_change=self._on_code_update
        )
        
        self.workspace.create_window(50, y, window=block, anchor='nw', tags='block')
        self.blocks.append(block)
        
        self._on_code_update()
    
    def _on_block_drag(self, block, event):
        """Handle block dragging"""
        pass  # Block handles its own dragging
    
    def _on_block_drop(self, block, event):
        """Handle block drop - check for snapping"""
        # Don't auto-sync to code - let user manually insert/generate
        pass
    
    def _on_block_delete(self, block):
        """Handle block deletion"""
        if block in self.blocks:
            self.blocks.remove(block)
        # Don't auto-sync to code - visual is non-destructive
    
    def _on_code_update(self):
        """Called when blocks change - internal update only, no sync to code"""
        # Visual editor is now non-destructive
        # Use "Insert Code" button to manually add code
        pass
    
    def _generate_code_string(self) -> str:
        """Generate PyTML code from all blocks, preserving unmatched lines"""
        # If no blocks, just return preserved lines
        if not self.blocks:
            return '\n'.join(line for _, line in sorted(self.preserved_lines))
        
        # If no block line indices tracked yet (new blocks added from palette), 
        # append blocks after all preserved lines
        if not self.block_line_indices:
            result_lines = [line for _, line in sorted(self.preserved_lines)]
            sorted_blocks = sorted(self.blocks, key=lambda b: b.winfo_y())
            for block in sorted_blocks:
                result_lines.append(block.get_code())
            return '\n'.join(result_lines)
        
        # Build output preserving the structure:
        # 1. Preserved lines BEFORE first block
        # 2. Preserved lines BETWEEN first and last block (interleaved with blocks)
        # 3. Block code (sorted by Y position)
        # 4. Preserved lines AFTER last block
        
        result_lines = []
        
        # Find the boundary indices
        min_block_idx = min(self.block_line_indices)
        max_block_idx = max(self.block_line_indices)
        
        # 1. Add preserved lines that come BEFORE any blocks
        pre_block_lines = [(idx, line) for idx, line in self.preserved_lines if idx < min_block_idx]
        for _, line in sorted(pre_block_lines):
            result_lines.append(line)
        
        # 2. Add preserved lines that are IN BETWEEN blocks (these are important! e.g. <gui> tags)
        mid_block_lines = [(idx, line) for idx, line in self.preserved_lines 
                          if idx >= min_block_idx and idx <= max_block_idx]
        for _, line in sorted(mid_block_lines):
            result_lines.append(line)
        
        # 3. Sort blocks by Y position (top to bottom) and add their code
        sorted_blocks = sorted(self.blocks, key=lambda b: b.winfo_y())
        for block in sorted_blocks:
            result_lines.append(block.get_code())
        
        # 4. Add preserved lines that come AFTER all blocks
        post_block_lines = [(idx, line) for idx, line in self.preserved_lines if idx > max_block_idx]
        for _, line in sorted(post_block_lines):
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _insert_code(self):
        """Insert generated block code (non-destructive)"""
        if not self.blocks:
            return
        
        # Generate code from blocks only (not preserved lines)
        sorted_blocks = sorted(self.blocks, key=lambda b: b.winfo_y())
        block_code = '\n'.join(block.get_code() for block in sorted_blocks)
        
        # Call callback with block code only, with special prefix to indicate insert mode
        if self.on_code_change:
            self.on_code_change(('__INSERT__', block_code))
    
    def _generate_code(self):
        """Generate and display code (legacy - now uses _insert_code)"""
        self._insert_code()
    
    def _clear_workspace(self, trigger_update=True):
        """Clear all blocks from workspace"""
        for block in self.blocks[:]:
            block.destroy()
        self.blocks.clear()
        self.block_line_indices.clear()
        # Note: Don't clear preserved_lines here - they should persist
        if trigger_update:
            self._on_code_update()
    
    def _refresh_libs(self):
        """Reload block definitions from libs"""
        self.library.load_from_libs()
        # Refresh current category view
        current_cat = BlockCategory[self.category_var.get()]
        self._select_category(current_cat)
    
    def load_from_code(self, code: str):
        """Parse PyTML code and create blocks, preserving unmatched lines"""
        # Clear existing without triggering code update
        self._clear_workspace(trigger_update=False)
        self.preserved_lines = []
        self.block_line_indices = set()
        
        if not code or not code.strip():
            return
        
        lines = code.split('\n')  # Keep original line structure
        self._original_line_count = len(lines)
        y_pos = 80
        
        for i, line in enumerate(lines):
            original_line = line  # Keep original with whitespace
            stripped = line.strip()
            
            # Preserve empty lines, comments, and lines we don't understand
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                self.preserved_lines.append((i, original_line))
                continue
            
            # Try to match against known block patterns
            result = self._find_matching_block(stripped)
            if result:
                block_def, param_values = result
                self._spawn_block_with_values(block_def, param_values, y_pos)
                self.block_line_indices.add(i)
                y_pos += 50
            else:
                # Line not recognized - preserve it
                self.preserved_lines.append((i, original_line))
    
    def _find_matching_block(self, line: str) -> Optional[Tuple[BlockDefinition, Dict[str, str]]]:
        """Find a block definition that matches a PyTML line and extract parameter values"""
        
        # Skip closing tags
        if line.startswith('</'):
            return None
        
        # Extract tag name from line like <tagname ...> or <name_action>
        tag_match = re.match(r'<(\w+)', line)
        if not tag_match:
            return None
        
        tag_name = tag_match.group(1).lower()
        
        # Try to find matching block
        for block_def in self.library.all_blocks:
            param_values = self._try_match_block(block_def, line, tag_name)
            if param_values is not None:
                return (block_def, param_values)
        
        return None
    
    def _try_match_block(self, block_def: BlockDefinition, line: str, tag_name: str) -> Optional[Dict[str, str]]:
        """Try to match a line against a block definition and extract parameter values"""
        
        block_name = block_def.name.lower()
        
        # Direct tag match (e.g., 'var', 'window', 'button')
        if block_name == tag_name:
            return self._extract_params(block_def, line)
        
        # Check for action patterns like <name_show>, <name_click>, etc.
        # e.g., block 'window_show' matches <wnd1_show>
        if '_' in block_name:
            base, action = block_name.rsplit('_', 1)
            action_pattern = rf'<(\w+)_{action}>'
            match = re.match(action_pattern, line, re.IGNORECASE)
            if match:
                params = {'name': match.group(1)}
                return params
        
        # Check for property set patterns like <name_text="value">
        # e.g., block 'label_set' matches <lbl1_text="Hello">
        if block_name.endswith('_set'):
            prop_pattern = rf'<(\w+)_(\w+)="([^"]*)">'
            match = re.match(prop_pattern, line)
            if match:
                name, prop, value = match.groups()
                if prop in ('text', 'title', 'value'):
                    return {'name': name, 'text': value}
        
        # Check for math operations like <counter_value += 1>
        if block_name == 'math_add':
            math_pattern = r'<(\w+)_value\s*\+=\s*(\d+)>'
            match = re.match(math_pattern, line)
            if match:
                return {'var': match.group(1), 'value': match.group(2)}
        
        if block_name == 'math_sub':
            math_pattern = r'<(\w+)_value\s*-=\s*(\d+)>'
            match = re.match(math_pattern, line)
            if match:
                return {'var': match.group(1), 'value': match.group(2)}
        
        if block_name == 'math_inc':
            inc_pattern = r'<(\w+)_value\+\+>'
            match = re.match(inc_pattern, line)
            if match:
                return {'var': match.group(1)}
        
        return None
    
    def _extract_params(self, block_def: BlockDefinition, line: str) -> Dict[str, str]:
        """Extract parameter values from a PyTML line"""
        params = {}
        
        # Extract all key="value" pairs
        attr_pattern = r'(\w+)="([^"]*)"'
        for match in re.finditer(attr_pattern, line):
            params[match.group(1)] = match.group(2)
        
        # Handle comma-separated values like size="300","200"
        size_pattern = r'size="(\d+)"\s*,\s*"(\d+)"'
        size_match = re.search(size_pattern, line)
        if size_match:
            params['width'] = size_match.group(1)
            params['height'] = size_match.group(2)
        
        return params
    
    def _spawn_block_with_values(self, block_def: BlockDefinition, param_values: Dict[str, str], y_pos: int):
        """Create a new block in the workspace with pre-filled parameter values"""
        x = 50
        
        # Create the block widget
        block = VisualBlock(
            self.workspace, 
            block_def,
            on_drag=self._on_block_drag,
            on_drop=self._on_block_drop,
            on_delete=self._on_block_delete,
            on_code_change=self._on_code_update
        )
        
        # Fill in parameter values
        for name, widget in block.param_widgets.items():
            if name in param_values:
                widget.var.set(param_values[name])
        
        # Place on workspace
        self.workspace.create_window(x, y_pos, window=block, anchor='nw', tags='block')
        self.blocks.append(block)


# Alias for backward compatibility
VisualPanel = VisualProgrammingPanel


# =============================================================================
# HELPER FUNCTION FOR EDITOR INTEGRATION
# =============================================================================

def create_visual_panel(parent, on_code_change=None) -> VisualProgrammingPanel:
    """Factory function to create a visual programming panel"""
    return VisualProgrammingPanel(parent, on_code_change)
