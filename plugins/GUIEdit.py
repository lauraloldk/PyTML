"""
PyTML Editor Plugin: GUI Edit Mode
Dynamic visual editing of GUI elements from libs
Container-based with REALTIME synchronization to code

Supports multiple graphics frameworks:
- tkinter widgets (native)
- Canvas-based graphics (turtle, matplotlib, etc.)
- Embedded surfaces (pygame, etc.)
"""

import tkinter as tk
from tkinter import ttk, colorchooser
import re
import sys
import os
import glob
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Framework types that can be hosted in PyTML windows
FRAMEWORK_TYPES = {
    'tkinter': {
        'name': 'Tkinter Widgets',
        'description': 'Native tkinter widgets (Button, Label, Entry, etc.)',
        'embed_method': 'native'
    },
    'canvas': {
        'name': 'Canvas Graphics', 
        'description': 'Canvas-based drawing (turtle, matplotlib plots)',
        'embed_method': 'canvas'
    },
    'surface': {
        'name': 'External Surface',
        'description': 'External graphics surfaces (pygame, etc.)',
        'embed_method': 'embed'
    }
}

# Default editor colors - libs can override via get_gui_info()['editor_colors']
DEFAULT_EDITOR_COLORS = {
    'window': {'bg': '#3c3c3c', 'border': '#569cd6', 'titlebar': '#252526', 'text': '#cccccc'},
    'container': {'bg': '#2d3436', 'border': '#74b9ff', 'text': '#dfe6e9'},
    'widget': {'bg': '#2d3436', 'border': '#a29bfe', 'text': '#dfe6e9'},
    'graphic': {'bg': '#1a1a2e', 'border': '#16c79a', 'text': '#16c79a'},
    'surface': {'bg': '#0d0d0d', 'border': '#e94560', 'text': '#e94560'},
}


class GUINodeRegistry:
    """Registry of all GUI node types from libs - dynamically discovers all available elements"""
    
    def __init__(self):
        self.nodes = {}
        self.containers = []
        self.widgets = []
        self.graphics = []  # Canvas/plot elements
        self.surfaces = []  # Embedded surfaces (pygame, etc.)
        self.all_items = []  # All items in a flat list for the menu
        self._categories = {}  # Grouped by category
    
    def load_from_libs(self):
        """Scan all libs and discover GUI elements"""
        self.nodes = {}
        self.containers = []
        self.widgets = []
        self.graphics = []
        self.surfaces = []
        self.all_items = []
        self._categories = {
            'Containers': [],
            'Widgets': [],
            'Graphics': [],
            'Surfaces': []
        }
        
        libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        
        for lib_file in glob.glob(os.path.join(libs_path, '*.py')):
            if lib_file.endswith('__init__.py'):
                continue
            self._load_from_lib(lib_file)
        
        # Build flat list for menu
        self._build_menu_items()
    
    def _load_from_lib(self, filepath):
        """Load GUI info from a lib file"""
        module_name = os.path.basename(filepath)[:-3]
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'get_gui_info'):
                gui_info = module.get_gui_info()
                category = gui_info.get('category', module_name)
                gui_info['_module'] = module_name
                gui_info['_source'] = filepath
                self.nodes[category] = gui_info
                
                element_type = gui_info.get('type', 'widget')
                framework = gui_info.get('framework', 'tkinter')
                
                if element_type == 'container':
                    self.containers.append(gui_info)
                    self._categories['Containers'].append(gui_info)
                elif element_type == 'widget':
                    self.widgets.append(gui_info)
                    self._categories['Widgets'].append(gui_info)
                elif element_type == 'graphic' or framework == 'canvas':
                    self.graphics.append(gui_info)
                    self._categories['Graphics'].append(gui_info)
                elif element_type == 'surface' or framework in ('pygame', 'sdl', 'opengl'):
                    self.surfaces.append(gui_info)
                    self._categories['Surfaces'].append(gui_info)
                else:
                    # Default to widgets
                    self.widgets.append(gui_info)
                    self._categories['Widgets'].append(gui_info)
                    
        except Exception as e:
            print(f"GUINodeRegistry: Could not load {filepath}: {e}")
    
    def _build_menu_items(self):
        """Build flat list of all items for dropdown menu"""
        self.all_items = []
        
        # Add containers first
        if self.containers:
            self.all_items.append({'type': 'separator', 'label': '── Containers ──'})
            for item in sorted(self.containers, key=lambda x: x.get('display_name', '')):
                self.all_items.append(item)
        
        # Add widgets
        if self.widgets:
            self.all_items.append({'type': 'separator', 'label': '── Widgets ──'})
            for item in sorted(self.widgets, key=lambda x: x.get('display_name', '')):
                self.all_items.append(item)
        
        # Add graphics elements
        if self.graphics:
            self.all_items.append({'type': 'separator', 'label': '── Graphics ──'})
            for item in sorted(self.graphics, key=lambda x: x.get('display_name', '')):
                self.all_items.append(item)
        
        # Add surface elements
        if self.surfaces:
            self.all_items.append({'type': 'separator', 'label': '── Surfaces ──'})
            for item in sorted(self.surfaces, key=lambda x: x.get('display_name', '')):
                self.all_items.append(item)
    
    def get_containers(self):
        return self.containers
    
    def get_widgets(self):
        return self.widgets
    
    def get_graphics(self):
        return self.graphics
    
    def get_surfaces(self):
        return self.surfaces
    
    def get_all_items(self):
        """Get all items for the Add Item menu"""
        return self.all_items
    
    def get_categories(self):
        """Get items grouped by category"""
        return self._categories
    
    def get_by_category(self, category):
        """Get a specific GUI info by category name"""
        return self.nodes.get(category)


class GUIBlock:
    """Represents a <gui>...</gui> block in the code"""
    
    def __init__(self, start_line, end_line, content):
        self.start_line = start_line  # 1-indexed
        self.end_line = end_line      # 1-indexed
        self.content = content
    
    @staticmethod
    def find_all_blocks(code):
        """Find all GUI blocks in the code"""
        blocks = []
        lines = code.split('\n')
        
        in_block = False
        block_start = 0
        block_content = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if stripped == '<gui>':
                in_block = True
                block_start = i
                block_content = []
            elif stripped == '</gui>' and in_block:
                blocks.append(GUIBlock(block_start, i, '\n'.join(block_content)))
                in_block = False
            elif in_block:
                block_content.append(line)
        
        return blocks
    
    def get_label(self):
        """Generate a label for this block"""
        return f"GUI Block (line {self.start_line}-{self.end_line})"


class GUIElement:
    """Represents a GUI element with relative positioning"""
    
    def __init__(self, element_type, name, x=0, y=0, width=100, height=30):
        self.element_type = element_type
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.properties = {}
        self.children = []
        self.parent = None
        self.selected = False
    
    def set_property(self, name, value):
        self.properties[name] = value
    
    def get_property(self, name, default=None):
        return self.properties.get(name, default)
    
    def add_child(self, child):
        child.parent = self
        if child not in self.children:
            self.children.append(child)
    
    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)
            child.parent = None
    
    def get_absolute_position(self):
        abs_x = self.x
        abs_y = self.y
        
        if self.parent:
            parent_x, parent_y = self.parent.get_absolute_position()
            abs_x += parent_x
            abs_y += parent_y
            if self.parent.element_type == 'window':
                abs_y += 30
        
        return abs_x, abs_y
    
    def contains_point(self, canvas_x, canvas_y):
        abs_x, abs_y = self.get_absolute_position()
        return (abs_x <= canvas_x <= abs_x + self.width and 
                abs_y <= canvas_y <= abs_y + self.height)
    
    def to_pytml(self):
        """Generate PyTML code - includes ALL properties"""
        attrs = [f'name="{self.name}"']
        
        if self.element_type == 'window':
            title = self.get_property('title', 'Window')
            attrs.insert(0, f'title="{title}"')
            attrs.append(f'size="{self.width}","{self.height}"')
        else:
            if 'text' in self.properties:
                attrs.insert(0, f'text="{self.properties["text"]}"')
            if self.parent:
                attrs.append(f'parent="{self.parent.name}"')
            attrs.append(f'x="{self.x}"')
            attrs.append(f'y="{self.y}"')
        
        # Add ALL other properties (colors, etc.) - preserves user's code
        skip_props = {'title', 'text', 'parent', 'x', 'y', 'name', 'size', 'width', 'height'}
        for prop_name, prop_value in self.properties.items():
            if prop_name not in skip_props and prop_value is not None:
                attrs.append(f'{prop_name}="{prop_value}"')
        
        return f'<{self.element_type} {" ".join(attrs)}>'


class GUICanvas(tk.Canvas):
    """Canvas for visual GUI editing"""
    
    def __init__(self, parent, on_change=None, **kwargs):
        super().__init__(parent, bg='#2d2d2d', highlightthickness=0, **kwargs)
        
        self.windows = []
        self.all_elements = {}
        self.selected_element = None
        self.drag_data = {"x": 0, "y": 0, "element": None}
        self.on_select = None
        self.on_change = on_change  # Callback for realtime updates
        self.registry = GUINodeRegistry()
        self.registry.load_from_libs()
        
        self.grid_size = 10
        
        # Build colors dynamically from registry
        self.colors = dict(DEFAULT_EDITOR_COLORS)  # Start with defaults
        self._load_colors_from_registry()
        
        self.bind('<Button-1>', self._on_click)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Configure>', self._on_resize)
        
        self._draw_grid()
    
    def _draw_grid(self):
        self.delete('grid')
        width = self.winfo_width() or 800
        height = self.winfo_height() or 600
        
        for x in range(0, width, self.grid_size * 2):
            self.create_line(x, 0, x, height, fill='#383838', tags='grid')
        for y in range(0, height, self.grid_size * 2):
            self.create_line(0, y, width, y, fill='#383838', tags='grid')
        
        self.tag_lower('grid')
    
    def _load_colors_from_registry(self):
        """Load editor colors from libs - allows libs to define their own colors"""
        for category, gui_info in self.registry.nodes.items():
            if 'editor_colors' in gui_info:
                # Lib defines custom colors
                self.colors[category] = gui_info['editor_colors']
            elif category not in self.colors:
                # Use type-based fallback
                element_type = gui_info.get('type', 'widget')
                framework = gui_info.get('framework', 'tkinter')
                
                if element_type == 'graphic' or framework == 'canvas':
                    self.colors[category] = dict(DEFAULT_EDITOR_COLORS['graphic'])
                elif element_type == 'surface' or framework in ('pygame', 'sdl', 'opengl'):
                    self.colors[category] = dict(DEFAULT_EDITOR_COLORS['surface'])
                elif element_type == 'container':
                    self.colors[category] = dict(DEFAULT_EDITOR_COLORS['container'])
                else:
                    self.colors[category] = dict(DEFAULT_EDITOR_COLORS['widget'])
    
    def get_element_info(self, element_type):
        """Get gui_info for an element type from registry"""
        return self.registry.get_by_category(element_type)
    
    def _on_resize(self, event):
        self._draw_grid()
    
    def _notify_change(self):
        """Notify about change for realtime sync"""
        if self.on_change:
            self.on_change()
    
    def add_window(self, element):
        self.windows.append(element)
        self.all_elements[element.name] = element
        self._draw_window(element)
        return element
    
    def add_widget(self, element, parent_window):
        if parent_window:
            parent_window.add_child(element)
        self.all_elements[element.name] = element
        self._draw_widget(element)
        return element
    
    def _draw_window(self, window):
        tag = f"window_{window.name}"
        self.delete(tag)
        
        abs_x, abs_y = window.get_absolute_position()
        colors = self.colors['window']
        
        border_color = '#ff6b6b' if window.selected else colors['border']
        border_width = 3 if window.selected else 2
        
        self.create_rectangle(
            abs_x, abs_y, abs_x + window.width, abs_y + window.height,
            fill=colors['bg'], outline=border_color, width=border_width,
            tags=(tag, 'window', 'element')
        )
        
        self.create_rectangle(
            abs_x, abs_y, abs_x + window.width, abs_y + 30,
            fill=colors['titlebar'], outline='',
            tags=(tag, 'window', 'element')
        )
        
        title = window.get_property('title', window.name)
        self.create_text(
            abs_x + 10, abs_y + 15,
            text=f"🪟 {title}", fill='#cccccc', font=('Segoe UI', 9, 'bold'),
            anchor='w', tags=(tag, 'window', 'element')
        )
        
        self.create_text(
            abs_x + window.width - 10, abs_y + 15,
            text=f"{window.width}x{window.height}", fill='#808080', font=('Consolas', 8),
            anchor='e', tags=(tag, 'window', 'element')
        )
        
        self.create_rectangle(
            abs_x + 2, abs_y + 32,
            abs_x + window.width - 2, abs_y + window.height - 2,
            fill='', outline='#4a4a4a', dash=(2, 2),
            tags=(tag, 'window', 'element')
        )
        
        for child in window.children:
            self._draw_widget(child)
        
        self._raise_window_children(window)
    
    def _draw_widget(self, widget):
        """Draw any widget type - fully dynamic based on registry"""
        tag = f"widget_{widget.name}"
        self.delete(tag)
        
        abs_x, abs_y = widget.get_absolute_position()
        
        # Get gui_info from registry if available
        gui_info = self.get_element_info(widget.element_type) or {}
        element_type = gui_info.get('type', 'widget')
        framework = gui_info.get('framework', 'tkinter')
        icon = gui_info.get('icon', '📦')
        
        # Get colors - check registry, then widget type, then fallback
        colors = self.colors.get(widget.element_type, 
                                 self.colors.get(element_type, 
                                                 DEFAULT_EDITOR_COLORS['widget']))
        
        border_color = '#ff6b6b' if widget.selected else colors.get('border', '#a29bfe')
        border_width = 2 if widget.selected else 1
        bg_color = colors.get('bg', '#2d3436')
        text_color = colors.get('text', '#dfe6e9')
        
        # Draw based on category type
        if element_type == 'graphic' or framework == 'canvas':
            # Canvas/graphic elements - grid pattern
            self.create_rectangle(
                abs_x, abs_y, abs_x + widget.width, abs_y + widget.height,
                fill=bg_color, outline=border_color, width=border_width,
                tags=(tag, 'widget', 'element')
            )
            # Grid pattern
            for i in range(0, widget.width, 20):
                self.create_line(abs_x + i, abs_y, abs_x + i, abs_y + widget.height,
                               fill='#2a2a4e', tags=(tag, 'widget', 'element'))
            for i in range(0, widget.height, 20):
                self.create_line(abs_x, abs_y + i, abs_x + widget.width, abs_y + i,
                               fill='#2a2a4e', tags=(tag, 'widget', 'element'))
            text = widget.get_property('text', f'{icon} {widget.element_type}')
            self.create_text(
                abs_x + widget.width // 2, abs_y + widget.height // 2,
                text=text, fill=text_color, font=('Consolas', 10, 'bold'),
                tags=(tag, 'widget', 'element')
            )
            self.create_text(
                abs_x + widget.width - 5, abs_y + 12,
                text=f"🎨 {framework}", fill='#808080', font=('Consolas', 8),
                anchor='e', tags=(tag, 'widget', 'element')
            )
            
        elif element_type == 'surface' or framework in ('pygame', 'sdl', 'opengl'):
            # Embedded surface - X pattern
            self.create_rectangle(
                abs_x, abs_y, abs_x + widget.width, abs_y + widget.height,
                fill=bg_color, outline=border_color, width=border_width,
                tags=(tag, 'widget', 'element')
            )
            self.create_line(abs_x, abs_y, abs_x + widget.width, abs_y + widget.height,
                           fill='#2a2a2a', tags=(tag, 'widget', 'element'))
            self.create_line(abs_x + widget.width, abs_y, abs_x, abs_y + widget.height,
                           fill='#2a2a2a', tags=(tag, 'widget', 'element'))
            text = widget.get_property('text', f'{icon} {widget.element_type}')
            self.create_text(
                abs_x + widget.width // 2, abs_y + widget.height // 2,
                text=text, fill=text_color, font=('Consolas', 10, 'bold'),
                tags=(tag, 'widget', 'element')
            )
            self.create_text(
                abs_x + widget.width - 5, abs_y + 12,
                text=f"🎮 {framework}", fill='#808080', font=('Consolas', 8),
                anchor='e', tags=(tag, 'widget', 'element')
            )
        
        else:
            # Standard widget - rectangle with text
            # Use transparent bg for label-like widgets (no fill)
            if bg_color == 'transparent':
                # Draw text only with optional selection border
                text = widget.get_property('text', widget.name)
                self.create_text(
                    abs_x, abs_y + widget.height // 2,
                    text=f"{icon} {text}", fill=text_color, font=('Segoe UI', 9),
                    anchor='w', tags=(tag, 'widget', 'element')
                )
                if widget.selected:
                    self.create_rectangle(
                        abs_x - 2, abs_y, abs_x + widget.width + 2, abs_y + widget.height,
                        fill='', outline=border_color, width=border_width, dash=(2, 2),
                        tags=(tag, 'widget', 'element')
                    )
            else:
                # Normal widget with background
                self.create_rectangle(
                    abs_x, abs_y, abs_x + widget.width, abs_y + widget.height,
                    fill=bg_color, outline=border_color, width=border_width,
                    tags=(tag, 'widget', 'element')
                )
                text = widget.get_property('text', widget.get_property('placeholder', widget.name))
                self.create_text(
                    abs_x + widget.width // 2, abs_y + widget.height // 2,
                    text=f"{icon} {text}", fill=text_color, font=('Segoe UI', 9),
                    tags=(tag, 'widget', 'element')
                )
        
        # Position indicator
        self.create_text(
            abs_x + widget.width // 2, abs_y + widget.height + 8,
            text=f"({widget.x}, {widget.y})", fill='#606060', font=('Consolas', 7),
            tags=(tag, 'widget', 'element')
        )
    
    def _raise_window_children(self, window):
        for child in window.children:
            tag = f"widget_{child.name}"
            self.tag_raise(tag)
    
    def redraw_all(self):
        self.delete('element')
        for window in self.windows:
            self._draw_window(window)
    
    def _find_element_at(self, x, y):
        for window in reversed(self.windows):
            for child in reversed(window.children):
                if child.contains_point(x, y):
                    return child
        
        for window in reversed(self.windows):
            if window.contains_point(x, y):
                return window
        
        return None
    
    def _on_click(self, event):
        clicked = self._find_element_at(event.x, event.y)
        
        if self.selected_element:
            self.selected_element.selected = False
        
        self.selected_element = clicked
        
        if clicked:
            clicked.selected = True
            
            abs_x, abs_y = clicked.get_absolute_position()
            self.drag_data = {
                "x": event.x - abs_x,
                "y": event.y - abs_y,
                "element": clicked
            }
            
            if clicked.parent:
                self._bring_window_to_front(clicked.parent)
            elif clicked.element_type == 'window':
                self._bring_window_to_front(clicked)
        else:
            self.drag_data = {"x": 0, "y": 0, "element": None}
        
        self.redraw_all()
        
        if self.on_select:
            self.on_select(clicked)
    
    def _bring_window_to_front(self, window):
        if window in self.windows:
            self.windows.remove(window)
            self.windows.append(window)
    
    def _on_drag(self, event):
        element = self.drag_data.get("element")
        if not element:
            return
        
        if element.element_type == 'window':
            new_x = round((event.x - self.drag_data["x"]) / self.grid_size) * self.grid_size
            new_y = round((event.y - self.drag_data["y"]) / self.grid_size) * self.grid_size
            element.x = max(0, new_x)
            element.y = max(0, new_y)
        else:
            if element.parent:
                parent_x, parent_y = element.parent.get_absolute_position()
                titlebar_offset = 30 if element.parent.element_type == 'window' else 0
                
                new_abs_x = event.x - self.drag_data["x"]
                new_abs_y = event.y - self.drag_data["y"]
                
                new_rel_x = new_abs_x - parent_x
                new_rel_y = new_abs_y - parent_y - titlebar_offset
                
                new_rel_x = round(new_rel_x / self.grid_size) * self.grid_size
                new_rel_y = round(new_rel_y / self.grid_size) * self.grid_size
                
                new_rel_x = max(0, min(new_rel_x, element.parent.width - element.width))
                new_rel_y = max(0, min(new_rel_y, element.parent.height - titlebar_offset - element.height))
                
                element.x = new_rel_x
                element.y = new_rel_y
        
        self.redraw_all()
    
    def _on_release(self, event):
        if self.drag_data.get("element"):
            self._notify_change()  # Realtime sync after drag
        self.drag_data = {"x": 0, "y": 0, "element": None}
    
    def clear(self):
        self.delete('element')
        self.windows = []
        self.all_elements = {}
        self.selected_element = None
    
    def generate_code(self):
        """Generate PyTML code for all elements"""
        lines = []
        
        for window in self.windows:
            lines.append(window.to_pytml())
            lines.append(f"<{window.name}_show>")
            
            for child in window.children:
                lines.append(child.to_pytml())
        
        return '\n'.join(lines)


class GUIEditPanel(ttk.Frame):
    """Main panel for GUI editing with realtime synchronization"""
    
    def __init__(self, parent, on_code_change=None, on_element_select=None):
        super().__init__(parent)
        self.on_code_change = on_code_change
        self.on_element_select = on_element_select  # External callback for element selection
        self.registry = GUINodeRegistry()
        self.registry.load_from_libs()
        self._element_counter = 0
        
        # GUI block tracking
        self.gui_blocks = []
        self.active_block_index = 0
        self.full_code = ""
        self._updating_code = False  # Prevent recursion
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="🎨 GUI Edit", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Block selector
        ttk.Label(toolbar, text="Block:").pack(side=tk.LEFT, padx=5)
        self.block_var = tk.StringVar()
        self.block_combo = ttk.Combobox(toolbar, textvariable=self.block_var, state='readonly', width=25)
        self.block_combo.pack(side=tk.LEFT, padx=2)
        self.block_combo.bind('<<ComboboxSelected>>', self._on_block_selected)
        
        ttk.Button(toolbar, text="➕ New Block", command=self._create_new_block).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Add Item button with dropdown menu
        self.add_item_btn = ttk.Menubutton(toolbar, text="➕ Add Item ▼")
        self.add_item_btn.pack(side=tk.LEFT, padx=5)
        
        # Create the dropdown menu
        self.add_menu = tk.Menu(self.add_item_btn, tearoff=0)
        self.add_item_btn['menu'] = self.add_menu
        self._populate_add_menu()
        
        # Refresh button to reload libs
        ttk.Button(toolbar, text="🔄", width=3, command=self._refresh_registry).pack(side=tk.LEFT, padx=2)
        
        # Main area - just the canvas, no built-in properties panel
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = GUICanvas(canvas_frame, on_change=self._on_canvas_change)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.on_select = self._on_element_select_internal
        
        # Info bar
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, pady=5)
        
        self.info_var = tk.StringVar(value="Add a window to start • Changes sync automatically")
        ttk.Label(info_frame, textvariable=self.info_var).pack(side=tk.LEFT, padx=5)
        
        self.sync_label = ttk.Label(info_frame, text="🔄 LIVE", foreground='#4ec9b0')
        self.sync_label.pack(side=tk.RIGHT, padx=5)
    
    def _populate_add_menu(self):
        """Populate the Add Item dropdown menu with all available elements from libs"""
        self.add_menu.delete(0, tk.END)
        
        categories = self.registry.get_categories()
        
        # Add Containers section
        if categories.get('Containers'):
            self.add_menu.add_command(label="── Containers ──", state='disabled')
            for gui_info in categories['Containers']:
                icon = gui_info.get('icon', '📦')
                name = gui_info.get('display_name', gui_info.get('category', 'Unknown'))
                framework = gui_info.get('framework', 'tkinter')
                label = f"{icon} {name}"
                if framework != 'tkinter':
                    label += f" ({framework})"
                self.add_menu.add_command(
                    label=label,
                    command=lambda g=gui_info: self._add_item(g)
                )
            self.add_menu.add_separator()
        
        # Add Widgets section
        if categories.get('Widgets'):
            self.add_menu.add_command(label="── Widgets ──", state='disabled')
            for gui_info in categories['Widgets']:
                icon = gui_info.get('icon', '📦')
                name = gui_info.get('display_name', gui_info.get('category', 'Unknown'))
                framework = gui_info.get('framework', 'tkinter')
                label = f"{icon} {name}"
                if framework != 'tkinter':
                    label += f" ({framework})"
                self.add_menu.add_command(
                    label=label,
                    command=lambda g=gui_info: self._add_item(g)
                )
            self.add_menu.add_separator()
        
        # Add Graphics section (for canvas-based elements like plots, turtle, etc.)
        if categories.get('Graphics'):
            self.add_menu.add_command(label="── Graphics ──", state='disabled')
            for gui_info in categories['Graphics']:
                icon = gui_info.get('icon', '🎨')
                name = gui_info.get('display_name', gui_info.get('category', 'Unknown'))
                framework = gui_info.get('framework', 'canvas')
                label = f"{icon} {name} ({framework})"
                self.add_menu.add_command(
                    label=label,
                    command=lambda g=gui_info: self._add_item(g)
                )
            self.add_menu.add_separator()
        
        # Add Surfaces section (for embedded surfaces like pygame)
        if categories.get('Surfaces'):
            self.add_menu.add_command(label="── Surfaces ──", state='disabled')
            for gui_info in categories['Surfaces']:
                icon = gui_info.get('icon', '🎮')
                name = gui_info.get('display_name', gui_info.get('category', 'Unknown'))
                framework = gui_info.get('framework', 'surface')
                label = f"{icon} {name} ({framework})"
                self.add_menu.add_command(
                    label=label,
                    command=lambda g=gui_info: self._add_item(g)
                )
        
        # If no items found, show info
        if not any(categories.values()):
            self.add_menu.add_command(
                label="No GUI elements found in libs/",
                state='disabled'
            )
            self.add_menu.add_separator()
            self.add_menu.add_command(
                label="Add get_gui_info() to lib files",
                state='disabled'
            )
    
    def _refresh_registry(self):
        """Refresh the registry by reloading all libs"""
        self.registry.load_from_libs()
        self._populate_add_menu()
        self.info_var.set(f"Refreshed: Found {len(self.registry.nodes)} GUI elements")
    
    def _add_item(self, gui_info):
        """Add any item from the registry - unified handler"""
        element_type = gui_info.get('type', 'widget')
        
        if element_type == 'container':
            self._add_container(gui_info)
        else:
            # All non-containers are treated as widgets (including graphics/surfaces)
            self._add_widget(gui_info)

    def _on_canvas_change(self):
        """Callback when canvas changes (drag etc)"""
        self._sync_to_code()
        # Notify external callback that element may have changed
        if self.on_element_select and self.canvas.selected_element:
            self.on_element_select(self.canvas.selected_element, self.registry)
    
    def _sync_to_code(self):
        """Synchronize canvas to code in realtime"""
        if self._updating_code:
            return
        
        self._updating_code = True
        
        try:
            # Generate new code for GUI block
            new_gui_content = self.canvas.generate_code()
            
            if self.gui_blocks and self.active_block_index < len(self.gui_blocks):
                # Replace existing block
                block = self.gui_blocks[self.active_block_index]
                lines = self.full_code.split('\n')
                
                # Build new code
                new_lines = []
                new_lines.extend(lines[:block.start_line - 1])  # Before block
                new_lines.append('<gui>')
                if new_gui_content:
                    new_lines.extend(new_gui_content.split('\n'))
                new_lines.append('</gui>')
                new_lines.extend(lines[block.end_line:])  # After block
                
                new_code = '\n'.join(new_lines)
            else:
                # No existing block - don't add anything
                # (only via "New Block" button)
                new_code = self.full_code
            
            if self.on_code_change:
                self.on_code_change(new_code, realtime=True)
            
        finally:
            self._updating_code = False
    
    def _create_new_block(self):
        """Create a new GUI block in the code"""
        new_block = "\n<gui>\n</gui>\n"
        
        # Add to end of code
        new_code = self.full_code.rstrip() + new_block
        
        if self.on_code_change:
            self.on_code_change(new_code, realtime=True)
        
        # Reload to find the new block
        self.load_from_code(new_code)
        
        # Select the new block
        if self.gui_blocks:
            self.active_block_index = len(self.gui_blocks) - 1
            self._update_block_combo()
    
    def _on_block_selected(self, event=None):
        """Handle GUI block selection"""
        selection = self.block_combo.current()
        if selection >= 0 and selection < len(self.gui_blocks):
            self.active_block_index = selection
            self._load_block(self.gui_blocks[selection])
    
    def _update_block_combo(self):
        """Update block combobox"""
        if not self.gui_blocks:
            self.block_combo['values'] = ['(No GUI blocks)']
            self.block_combo.current(0)
        else:
            values = [block.get_label() for block in self.gui_blocks]
            self.block_combo['values'] = values
            if self.active_block_index < len(values):
                self.block_combo.current(self.active_block_index)
    
    def _load_block(self, block):
        """Load a specific GUI block"""
        self.canvas.clear()
        self._element_counter = 0
        self._parse_gui_content(block.content)
        self.canvas.redraw_all()
    
    def _delete_selected(self):
        element = self.canvas.selected_element
        if not element:
            return
        
        if element.element_type == 'window':
            self.canvas.windows.remove(element)
            for child in element.children:
                del self.canvas.all_elements[child.name]
            del self.canvas.all_elements[element.name]
        else:
            if element.parent:
                element.parent.remove_child(element)
            del self.canvas.all_elements[element.name]
        
        self.canvas.selected_element = None
        self.canvas.redraw_all()
        # Notify external callback that selection cleared
        if self.on_element_select:
            self.on_element_select(None, self.registry)
        self._sync_to_code()
        self.info_var.set("Element deleted")
    
    def _get_next_name(self, prefix):
        self._element_counter += 1
        return f"{prefix}{self._element_counter}"
    
    def _add_container(self, gui_info):
        category = gui_info['category']
        name = self._get_next_name(category[:3])
        default_size = gui_info.get('default_size', (300, 200))
        framework = gui_info.get('framework', 'tkinter')
        
        element = GUIElement(category, name, 50, 50, default_size[0], default_size[1])
        element.set_property('title', gui_info.get('display_name', 'Window'))
        element.set_property('framework', framework)
        
        self.canvas.add_window(element)
        self._sync_to_code()
        self.info_var.set(f"Added {category}: {name}")
    
    def _add_widget(self, gui_info):
        if not self.canvas.windows:
            self.info_var.set("⚠️ Add a window first!")
            return
        
        parent = self.canvas.windows[-1]
        if self.canvas.selected_element:
            if self.canvas.selected_element.element_type == 'window':
                parent = self.canvas.selected_element
            elif self.canvas.selected_element.parent:
                parent = self.canvas.selected_element.parent
        
        category = gui_info['category']
        name = self._get_next_name(category[:3])
        default_size = gui_info.get('default_size', (100, 30))
        framework = gui_info.get('framework', 'tkinter')
        element_type = gui_info.get('type', 'widget')
        
        element = GUIElement(category, name, 10, 10, default_size[0], default_size[1])
        element.set_property('framework', framework)
        element.set_property('element_type', element_type)
        
        # Set default properties based on element type
        if category in ('button', 'label'):
            element.set_property('text', gui_info.get('display_name', category.title()))
        elif category == 'entry':
            element.set_property('placeholder', 'Enter text...')
        elif element_type == 'graphic':
            # Canvas/plot elements
            element.set_property('text', f"[{gui_info.get('display_name', category)}]")
        elif element_type == 'surface':
            # Embedded surfaces (pygame, etc.)
            element.set_property('text', f"[{gui_info.get('display_name', category)}]")
        else:
            # Generic - use display name or category
            display_name = gui_info.get('display_name', category.title())
            element.set_property('text', display_name)
        
        self.canvas.add_widget(element, parent)
        self._sync_to_code()
        
        type_label = element_type if element_type != 'widget' else category
        self.info_var.set(f"Added {type_label} '{name}' to {parent.name}")
    
    def _on_element_select_internal(self, element):
        """Internal callback when element is selected - notifies external callback"""
        if element:
            self.info_var.set(f"Selected: {element.element_type} '{element.name}'")
        else:
            self.info_var.set("Click on an element to select")
        
        # Call external callback so Properties panel can update
        if self.on_element_select:
            self.on_element_select(element, self.registry)
    
    def get_selected_element(self):
        """Get the currently selected element"""
        return self.canvas.selected_element
    
    def load_from_code(self, code):
        """Load GUI elements from PyTML code"""
        self.full_code = code
        self._updating_code = True
        
        try:
            # Find all GUI blocks
            self.gui_blocks = GUIBlock.find_all_blocks(code)
            self._update_block_combo()
            
            # Load first block if any
            if self.gui_blocks:
                self.active_block_index = 0
                self._load_block(self.gui_blocks[0])
                self.info_var.set(f"Loaded {len(self.gui_blocks)} GUI block(s)")
            else:
                self.canvas.clear()
                self.info_var.set("No GUI blocks found. Click '➕ New Block' to start.")
        
        finally:
            self._updating_code = False
    
    def _parse_gui_content(self, content):
        """Parse GUI content and create elements - fully dynamic from registry"""
        windows_by_name = {}
        
        # Regex pattern that handles > inside quoted values: matches non-quote/non-> OR quoted strings
        # This fixes parsing of attributes like: backgroundcolor="<bc_value>"
        ATTR_PATTERN = r'(?:[^>"]*|"[^"]*")*'
        
        # Parse windows (containers)
        window_pattern = rf'<window\s+({ATTR_PATTERN})>'
        for match in re.finditer(window_pattern, content):
            attrs = self._parse_attributes(match.group(1))
            name = attrs.get('name', self._get_next_name('wnd'))
            title = attrs.get('title', 'Window')
            
            size_match = re.search(r'size="(\d+)"(?:,"(\d+)")?', match.group(1))
            if size_match:
                width = int(size_match.group(1))
                height = int(size_match.group(2)) if size_match.group(2) else width
            else:
                width, height = 300, 200
            
            element = GUIElement('window', name, 50 + len(windows_by_name) * 30, 50, width, height)
            element.set_property('title', title)
            
            # Store ALL parsed attributes - preserve colors, etc.
            for attr_name, attr_value in attrs.items():
                if attr_name not in ('name', 'title', 'size'):
                    element.set_property(attr_name, attr_value)
            
            self.canvas.add_window(element)
            windows_by_name[name] = element
        
        # Build dynamic widget patterns from registry
        # Get all widget categories from registry
        widget_types = set()
        for gui_info in self.registry.widgets:
            category = gui_info.get('category', '')
            if category:
                widget_types.add(category)
        
        # Also check for any tags in the content that we might have missed
        # Find all <tagname ...> patterns - use pattern that handles > in quotes
        all_tags = set(re.findall(rf'<(\w+)\s+{ATTR_PATTERN}>', content))
        all_tags.discard('window')  # Already handled
        all_tags.discard('gui')     # Container tag, not widget
        
        # Combine registry widgets + found tags
        widget_types.update(all_tags)
        
        # Parse each widget type dynamically
        for widget_type in widget_types:
            # Get gui_info from registry for default size
            gui_info = self.registry.get_by_category(widget_type) or {}
            default_size = gui_info.get('default_size', (100, 30))
            
            # Use ATTR_PATTERN to handle > inside quoted values
            pattern = rf'<{widget_type}\s+({ATTR_PATTERN})>'
            for match in re.finditer(pattern, content):
                attrs = self._parse_attributes(match.group(1))
                name = attrs.get('name', self._get_next_name(widget_type[:3]))
                text = attrs.get('text', gui_info.get('display_name', widget_type.title()))
                x = int(attrs.get('x', 10))
                y = int(attrs.get('y', 10))
                parent_name = attrs.get('parent')
                
                # Get width/height from attrs or default_size
                width = int(attrs.get('width', default_size[0]))
                height = int(attrs.get('height', default_size[1]))
                
                parent = None
                if parent_name and parent_name in windows_by_name:
                    parent = windows_by_name[parent_name]
                elif windows_by_name:
                    parent = list(windows_by_name.values())[0]
                
                element = GUIElement(widget_type, name, x, y, width, height)
                element.set_property('text', text)
                
                # Store ALL parsed attributes - preserve colors, etc.
                for attr_name, attr_value in attrs.items():
                    if attr_name not in ('name', 'text', 'x', 'y', 'parent', 'width', 'height'):
                        element.set_property(attr_name, attr_value)
                
                if parent:
                    self.canvas.add_widget(element, parent)
    
    def _parse_attributes(self, attr_string):
        attrs = {}
        for match in re.finditer(r'(\w+)="([^"]*)"', attr_string):
            attrs[match.group(1)] = match.group(2)
        return attrs


def get_plugin_info():
    """Plugin registration for auto-discovery"""
    return {
        'name': 'GUIEdit',
        'panel_type': 'center_tab',
        'panel_class': GUIEditPanel,
        'panel_icon': '🎨',
        'panel_name': 'GUI Editor',
        'priority': 10,  # Show as first tab after Code
        'callbacks': {},
        'menu_items': [
            {'menu': 'View', 'label': 'Toggle GUI Editor', 'command': 'select_tab'}
        ]
    }


__all__ = ['GUINodeRegistry', 'GUIElement', 'GUICanvas', 'GUIEditPanel', 'GUIBlock', 'get_plugin_info']
