"""
PyTML Editor Plugin: Properties Panel
Dynamic loading of properties from lib files and nodes

Supports:
- Dynamic property loading from libs
- Variable references (<varname_value>) detection and display
- Automatic property type inference from names
- Preservation of ALL properties (known + unknown)
"""

import tkinter as tk
from tkinter import ttk, colorchooser
import os
import sys
import inspect
import re
import importlib.util
import glob

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Variable Reference Detection
# ============================================================================

def is_variable_reference(value):
    """Check if a value is a variable reference like <varname_value> or <name_random>"""
    if not isinstance(value, str):
        return False
    # Match patterns like <name_value>, <name_random>, <name_float>
    return bool(re.match(r'^<\w+_\w+>$', value.strip()))


def get_variable_name(value):
    """Extract variable name from a reference like <varname_value>"""
    if not is_variable_reference(value):
        return None
    match = re.match(r'^<(\w+)_(\w+)>$', value.strip())
    if match:
        return match.group(1)
    return None


def get_variable_suffix(value):
    """Extract suffix from a reference like <varname_value> -> 'value'"""
    if not is_variable_reference(value):
        return None
    match = re.match(r'^<(\w+)_(\w+)>$', value.strip())
    if match:
        return match.group(2)
    return None


def infer_property_type(name, value=None):
    """
    Infer property type from name and optionally value.
    
    Patterns:
    - *color* -> 'color'
    - x, y, width, height -> 'int'
    - enabled, visible, readonly -> 'bool'
    - size -> 'size'
    - Variable reference -> keeps underlying type but marks as 'var_*'
    """
    name_lower = name.lower()
    
    # Check value first for variable references
    if value is not None and is_variable_reference(value):
        # Infer base type from name, mark as variable
        base_type = _infer_type_from_name(name_lower)
        return f'var_{base_type}'
    
    return _infer_type_from_name(name_lower)


def _infer_type_from_name(name_lower):
    """Infer property type from name pattern"""
    # Color properties
    if 'color' in name_lower or name_lower in ('bg', 'fg', 'background', 'foreground'):
        return 'color'
    
    # Integer properties
    if name_lower in ('x', 'y', 'width', 'height', 'padx', 'pady', 'padding', 'margin'):
        return 'int'
    
    # Boolean properties  
    if name_lower in ('enabled', 'visible', 'readonly', 'disabled', 'checked', 'selected'):
        return 'bool'
    
    # Size (tuple/list)
    if name_lower == 'size':
        return 'size'
    
    # Default to string
    return 'string'


class PropertyValue:
    """Represents a property value"""
    
    def __init__(self, name, value, prop_type="string", editable=True, description=""):
        self.name = name
        self.value = value
        self.prop_type = prop_type  # 'string', 'int', 'bool', 'stack', 'color', 'list'
        self.editable = editable
        self.description = description
        self.on_change = None  # Callback when value changes
    
    def set_value(self, value):
        """Set the value"""
        old_value = self.value
        self.value = value
        if self.on_change and old_value != value:
            self.on_change(self.name, value, old_value)
    
    def get_value(self):
        """Get the value"""
        return self.value


class PropertyGroup:
    """Group of related properties"""
    
    def __init__(self, name, expanded=True):
        self.name = name
        self.expanded = expanded
        self.properties = []
    
    def add_property(self, prop):
        """Add a property to the group"""
        self.properties.append(prop)
        return prop
    
    def get_property(self, name):
        """Get a property by name"""
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None


class PropertyExtractor:
    """Extract properties dynamically from classes and regex patterns"""
    
    def __init__(self):
        self.class_properties = {}  # Cache of class properties
        self.syntax_patterns = {}   # Cache of syntax patterns -> properties
        self._load_all()
    
    def _load_all(self):
        """Load properties from all libs"""
        libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        
        for lib_file in glob.glob(os.path.join(libs_path, '*.py')):
            if lib_file.endswith('__init__.py'):
                continue
            self._load_from_file(lib_file)
        
        # Load from Compiler.py
        compiler_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Compiler.py')
        self._load_from_file(compiler_path)
    
    def _load_from_file(self, filepath):
        """Load properties from a file"""
        module_name = os.path.basename(filepath)[:-3]
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # PRIORITY: Use get_gui_info() if available (dynamic properties)
            if hasattr(module, 'get_gui_info'):
                gui_info = module.get_gui_info()
                category = gui_info.get('category', module_name)
                properties = gui_info.get('properties', [])
                
                # Convert to our format
                converted_props = []
                for prop in properties:
                    if isinstance(prop, dict):
                        converted_props.append({
                            'name': prop['name'],
                            'type': prop.get('type', 'string'),
                            'default': prop.get('default', ''),
                            'editable': True
                        })
                    else:
                        converted_props.append({
                            'name': prop,
                            'type': 'string',
                            'default': '',
                            'editable': True
                        })
                
                # Store under category name (button, window, etc.)
                self.class_properties[category] = converted_props
                # Also store under class name
                class_name = category.title()
                self.class_properties[class_name] = converted_props
            
            # Also extract from classes as fallback
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if name.startswith('_') or name == 'ActionNode':
                    continue
                if name not in self.class_properties:
                    self.class_properties[name] = self._extract_class_properties(cls)
            
            # Extract from parsers
            if hasattr(module, 'get_line_parsers'):
                for pattern, handler in module.get_line_parsers():
                    props = self._extract_pattern_properties(pattern)
                    if props:
                        self.syntax_patterns[pattern] = props
                        
        except Exception as e:
            print(f"PropertyExtractor: Could not load {filepath}: {e}")
    
    def _extract_class_properties(self, cls):
        """Extract properties from a class"""
        properties = []
        
        # From __init__ signature
        try:
            sig = inspect.signature(cls.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                prop_type = 'string'
                default = None
                
                # Check if it's a color property by name
                if 'color' in param_name.lower() or param_name in ('foreground', 'background', 'bg', 'fg'):
                    prop_type = 'color'
                
                # Check annotation
                elif param.annotation != inspect.Parameter.empty:
                    ann = str(param.annotation)
                    if 'int' in ann:
                        prop_type = 'int'
                    elif 'bool' in ann:
                        prop_type = 'bool'
                    elif 'list' in ann or 'List' in ann:
                        prop_type = 'list'
                
                # Check default value
                if param.default != inspect.Parameter.empty:
                    default = param.default
                    if isinstance(default, bool):
                        prop_type = 'bool'
                    elif isinstance(default, int) and prop_type == 'string':
                        prop_type = 'int'
                    elif isinstance(default, list):
                        prop_type = 'list'
                
                properties.append({
                    'name': param_name,
                    'type': prop_type,
                    'default': default,
                    'editable': True
                })
        except:
            pass
        
        # From class attributes
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
            if attr_name in [p['name'] for p in properties]:
                continue
            
            attr = getattr(cls, attr_name, None)
            if not callable(attr) and not inspect.ismethod(attr):
                prop_type = 'string'
                
                # Check if it's a color by name
                if 'color' in attr_name.lower() or attr_name in ('foreground', 'background', 'bg', 'fg'):
                    prop_type = 'color'
                elif isinstance(attr, bool):
                    prop_type = 'bool'
                elif isinstance(attr, int):
                    prop_type = 'int'
                elif isinstance(attr, list):
                    prop_type = 'list'
                
                properties.append({
                    'name': attr_name,
                    'type': prop_type,
                    'default': attr,
                    'editable': True
                })
        
        return properties
    
    def _extract_pattern_properties(self, pattern):
        """Extract properties from a regex pattern"""
        properties = []
        
        # Find named groups or standard groups
        # E.g: <window title="([^"]*)" size="(\d+)"
        
        # Find all attribute names
        attr_pattern = r'(\w+)=["\']\([^)]+\)["\']'
        for match in re.finditer(attr_pattern, pattern):
            attr_name = match.group(1)
            properties.append({
                'name': attr_name,
                'type': 'string',
                'default': '',
                'editable': True
            })
        
        # Check for special patterns
        if 'name=' in pattern:
            if not any(p['name'] == 'name' for p in properties):
                properties.append({'name': 'name', 'type': 'string', 'default': '', 'editable': True})
        
        if 'title=' in pattern:
            if not any(p['name'] == 'title' for p in properties):
                properties.append({'name': 'title', 'type': 'string', 'default': '', 'editable': True})
        
        if 'size=' in pattern:
            if not any(p['name'] == 'size' for p in properties):
                properties.append({'name': 'size', 'type': 'stack', 'default': [300, 300], 'editable': True})
        
        if 'count=' in pattern:
            if not any(p['name'] == 'count' for p in properties):
                properties.append({'name': 'count', 'type': 'int', 'default': 1, 'editable': True})
        
        if 'condition=' in pattern:
            if not any(p['name'] == 'condition' for p in properties):
                properties.append({'name': 'condition', 'type': 'string', 'default': '', 'editable': True})
        
        return properties
    
    def get_properties_for_class(self, class_name):
        """Get properties for a class"""
        return self.class_properties.get(class_name, [])
    
    def get_properties_for_tag(self, tag_name):
        """Get properties based on tag name"""
        # First try exact match (e.g., 'button', 'window')
        if tag_name in self.class_properties:
            return self.class_properties[tag_name]
        
        # Try lowercase (e.g., 'Button' -> 'button')
        tag_lower = tag_name.lower()
        if tag_lower in self.class_properties:
            return self.class_properties[tag_lower]
        
        # Try title case (e.g., 'button' -> 'Button')
        tag_title = tag_name.title()
        if tag_title in self.class_properties:
            return self.class_properties[tag_title]
        
        # Try with Node suffix
        class_name = tag_name.title().replace('_', '') + 'Node'
        if class_name in self.class_properties:
            return self.class_properties[class_name]
        
        # Try without Node suffix
        class_name = tag_name.title().replace('_', '')
        if class_name in self.class_properties:
            return self.class_properties[class_name]
        
        return []


class ElementProperties:
    """Properties for a PyTML element - dynamically loaded"""
    
    def __init__(self, element_type, element_name=None, attributes=None):
        self.element_type = element_type
        self.element_name = element_name
        self.attributes = attributes or {}
        self.groups = []
        self.source_line = None
        self._extractor = PropertyExtractor()
        
        # Auto-load properties
        self._load_properties()
    
    def _load_properties(self):
        """Load properties based on element type - preserves ALL attributes"""
        props = self._extractor.get_properties_for_tag(self.element_type)
        
        # Track which attributes we've processed
        processed_attrs = set()
        
        # First: Load known properties from registry
        if props:
            group = PropertyGroup(self.element_type.title())
            for prop_def in props:
                prop_name = prop_def['name']
                processed_attrs.add(prop_name)
                
                # Use existing value from attributes if available
                value = self.attributes.get(prop_name, prop_def.get('default', ''))
                
                # Determine type - check for variable reference first
                if is_variable_reference(value):
                    prop_type = infer_property_type(prop_name, value)
                else:
                    prop_type = prop_def.get('type', 'string')
                
                prop = PropertyValue(
                    name=prop_name,
                    value=value,
                    prop_type=prop_type,
                    editable=prop_def.get('editable', True)
                )
                group.add_property(prop)
            self.groups.append(group)
        
        # Second: Add any EXTRA attributes not in registry (preserve unknown properties)
        extra_attrs = {k: v for k, v in self.attributes.items() if k not in processed_attrs}
        if extra_attrs:
            group_name = "Custom Properties" if props else "Attributes"
            
            # Check if we need a new group or can use existing
            if props:
                extra_group = PropertyGroup(group_name)
            else:
                extra_group = PropertyGroup(self.element_type.title())
            
            for name, value in extra_attrs.items():
                # Use smart type inference
                prop_type = infer_property_type(name, value)
                
                # Handle list/stack values
                if isinstance(value, list):
                    prop_type = 'list'
                elif isinstance(value, bool):
                    prop_type = 'bool'
                elif isinstance(value, int) and prop_type == 'string':
                    prop_type = 'int'
                
                prop = PropertyValue(name=name, value=value, prop_type=prop_type)
                extra_group.add_property(prop)
            
            self.groups.append(extra_group)
    
    def add_group(self, group):
        """Add a property group"""
        self.groups.append(group)
        return group
    
    def get_all_properties(self):
        """Get all properties"""
        props = []
        for group in self.groups:
            props.extend(group.properties)
        return props
    
    def to_pytml(self):
        """Generate PyTML code from properties"""
        props = {p.name: p.value for p in self.get_all_properties()}
        
        # Build tag
        attrs = []
        for name, value in props.items():
            if value is None or value == '':
                continue
            if isinstance(value, list):
                # Stack format
                attr_str = ','.join(f'"{v}"' for v in value)
                attrs.append(f'{name}={attr_str}')
            elif isinstance(value, bool):
                if value:
                    attrs.append(name)
            else:
                attrs.append(f'{name}="{value}"')
        
        if attrs:
            return f'<{self.element_type} {" ".join(attrs)}>'
        return f'<{self.element_type}>'
    
    def _get_prop_value(self, name):
        """Get value of a property"""
        for group in self.groups:
            prop = group.get_property(name)
            if prop:
                return prop.value
        return ""


class PropertiesPanel(ttk.Frame):
    """Panel showing properties for selected element - dynamic"""
    
    def __init__(self, parent, on_property_change=None):
        super().__init__(parent)
        self.on_property_change = on_property_change
        self.current_element = None
        self.property_widgets = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(header_frame, text="⚙️ Properties", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        
        self.element_label = ttk.Label(header_frame, text="(none selected)")
        self.element_label.pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Scrollable frame for properties
        self.canvas = tk.Canvas(self, bg='#2d2d2d', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Placeholder text
        self.placeholder = ttk.Label(self.scrollable_frame, text="Select an element to see properties")
        self.placeholder.pack(pady=20)
    
    def load_gui_element(self, gui_element, registry=None):
        """Load properties from a GUIElement (from GUIEdit plugin)
        
        Args:
            gui_element: GUIElement instance with element_type, name, properties dict
            registry: Optional GUINodeRegistry for getting property definitions
        """
        if gui_element is None:
            self.load_element(None)
            return
        
        # Build attributes dict from GUIElement
        attrs = dict(gui_element.properties)
        attrs['name'] = gui_element.name
        attrs['x'] = gui_element.x
        attrs['y'] = gui_element.y
        if gui_element.element_type != 'window':
            attrs['width'] = gui_element.width
            attrs['height'] = gui_element.height
        
        # Create ElementProperties
        element = ElementProperties(
            element_type=gui_element.element_type,
            element_name=gui_element.name,
            attributes=attrs
        )
        
        # Store reference to original GUIElement for updates
        element._gui_element = gui_element
        
        self.load_element(element)
    
    def load_element(self, element):
        """Load properties for an element"""
        self.current_element = element
        
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.property_widgets = {}
        
        if element is None:
            self.element_label.config(text="(none selected)")
            self.placeholder = ttk.Label(self.scrollable_frame, text="Select an element to see properties")
            self.placeholder.pack(pady=20)
            return
        
        self.element_label.config(text=f"<{element.element_type}>")
        
        # Create widgets for each group
        for group in element.groups:
            self._create_group(group)
    
    def _sync_to_gui_element(self, prop):
        """Sync a property change back to the GUIElement (if present)"""
        if not self.current_element:
            return
        gui_elem = getattr(self.current_element, '_gui_element', None)
        if not gui_elem:
            return
        
        # Handle special position/size properties
        if prop.name == 'x':
            gui_elem.x = int(prop.value) if prop.value else 0
        elif prop.name == 'y':
            gui_elem.y = int(prop.value) if prop.value else 0
        elif prop.name == 'width':
            gui_elem.width = int(prop.value) if prop.value else 100
        elif prop.name == 'height':
            gui_elem.height = int(prop.value) if prop.value else 30
        elif prop.name == 'name':
            gui_elem.name = str(prop.value) if prop.value else ''
        else:
            # Store in properties dict
            gui_elem.set_property(prop.name, prop.value)
    
    def load_from_line(self, line):
        """Parse a line and show properties"""
        element = parse_line_to_element(line)
        if element:
            self.load_element(element)
    
    def _create_group(self, group):
        """Create widgets for a property group"""
        # Group header
        group_frame = ttk.LabelFrame(self.scrollable_frame, text=group.name)
        group_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Properties
        for prop in group.properties:
            self._create_property_widget(group_frame, prop)
    
    def _create_property_widget(self, parent, prop):
        """Create widget for a property"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Label
        ttk.Label(frame, text=prop.name, width=12).pack(side=tk.LEFT)
        
        # Input widget based on type
        # Handle variable reference types (var_color, var_string, etc.)
        if prop.prop_type.startswith('var_'):
            # Variable reference - show with indicator
            var = tk.StringVar(value=str(prop.value) if prop.value is not None else "")
            
            # Variable indicator label
            var_indicator = ttk.Label(frame, text="📌", width=2)
            var_indicator.pack(side=tk.LEFT)
            
            widget = ttk.Entry(frame, textvariable=var)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_var_ref_change(p, v))
            
            # For var_color, try to show a preview with resolved value
            if prop.prop_type == 'var_color':
                resolved_color = self._resolve_variable_color(prop.value)
                if resolved_color:
                    try:
                        preview = tk.Frame(frame, width=20, height=20, bg=resolved_color, 
                                           relief=tk.RAISED)
                        preview.pack(side=tk.RIGHT, padx=2)
                    except:
                        pass
        
        elif prop.prop_type == 'bool':
            var = tk.BooleanVar(value=bool(prop.value))
            widget = ttk.Checkbutton(frame, variable=var)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_bool_change(p, v))
        
        elif prop.prop_type == 'int':
            var = tk.StringVar(value=str(prop.value) if prop.value else "0")
            widget = ttk.Spinbox(frame, from_=0, to=9999, textvariable=var, width=10)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_int_change(p, v))
        
        elif prop.prop_type == 'stack' or prop.prop_type == 'list':
            # For stack/list, show as comma-separated
            val = prop.value
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            var = tk.StringVar(value=val if val else "")
            widget = ttk.Entry(frame, textvariable=var)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_list_change(p, v))
        
        elif prop.prop_type == 'color':
            var = tk.StringVar(value=prop.value if prop.value else "#ffffff")
            widget = ttk.Entry(frame, textvariable=var, width=12)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_string_change(p, v))
            
            # Color preview that acts as picker button
            try:
                preview = tk.Frame(frame, width=20, height=20, bg=prop.value if prop.value else '#ffffff', 
                                   relief=tk.RAISED, cursor='hand2')
                preview.pack(side=tk.RIGHT, padx=2)
                preview.bind('<Button-1>', lambda e, v=var, p=preview: self._pick_color(v, p))
            except:
                pass
            
            # Color picker button
            pick_btn = ttk.Button(frame, text="...", width=3,
                                  command=lambda v=var, p=preview: self._pick_color(v, p))
            pick_btn.pack(side=tk.RIGHT, padx=2)
        
        else:  # string (default)
            var = tk.StringVar(value=str(prop.value) if prop.value is not None else "")
            widget = ttk.Entry(frame, textvariable=var)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_string_change(p, v))
        
        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        if not prop.editable:
            widget.config(state='disabled')
        
        self.property_widgets[prop.name] = widget
    
    def _on_var_ref_change(self, prop, var):
        """Handle variable reference change - preserve as-is"""
        prop.set_value(var.get())
        self._sync_to_gui_element(prop)
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _resolve_variable_color(self, value):
        """Try to resolve a variable reference to a color value"""
        if not value or not is_variable_reference(value):
            return None
        
        var_name = get_variable_name(value)
        if not var_name:
            return None
        
        # Try to find the variable in the current file context
        # Look for var definitions like: var name = #color
        # This is a best-effort preview - may not always work
        try:
            if hasattr(self, 'editor') and hasattr(self.editor, 'code_area'):
                code = self.editor.code_area.get("1.0", "end-1c")
                # Look for: var <varname> = <value>
                import re
                pattern = rf'var\s+{re.escape(var_name)}\s*=\s*([^\n]+)'
                match = re.search(pattern, code)
                if match:
                    val = match.group(1).strip()
                    # Check if it's a color
                    if val.startswith('#') or val.startswith('rgb'):
                        return val
        except:
            pass
        
        return None
    
    def _on_string_change(self, prop, var):
        """Handle string change"""
        prop.set_value(var.get())
        self._sync_to_gui_element(prop)
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _on_int_change(self, prop, var):
        """Handle int change"""
        try:
            prop.set_value(int(var.get()))
        except ValueError:
            pass
        self._sync_to_gui_element(prop)
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _on_bool_change(self, prop, var):
        """Handle bool change"""
        prop.set_value(var.get())
        self._sync_to_gui_element(prop)
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _on_list_change(self, prop, var):
        """Handle list/stack change"""
        val = var.get()
        # Parse comma-separated list
        if val:
            parts = [p.strip() for p in val.split(',')]
            # Try to convert to int if possible
            try:
                parts = [int(p) for p in parts]
            except:
                pass
            prop.set_value(parts)
        else:
            prop.set_value([])
        
        self._sync_to_gui_element(prop)
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _pick_color(self, var, preview_frame=None):
        """Open color picker dialog"""
        current_color = var.get() if var.get() else "#ffffff"
        try:
            color = colorchooser.askcolor(color=current_color, title="Vælg farve")
            if color[1]:  # color is ((r,g,b), "#hexcolor")
                var.set(color[1])
                if preview_frame:
                    try:
                        preview_frame.configure(bg=color[1])
                    except:
                        pass
        except:
            pass


def parse_line_to_element(line):
    """Parse a PyTML line and return ElementProperties"""
    line = line.strip()
    if not line.startswith('<'):
        return None
    
    # Find tag type
    tag_match = re.match(r'<(\w+)', line)
    if not tag_match:
        return None
    
    tag_type = tag_match.group(1)
    
    # Extract attributes
    attributes = {}
    
    # Standard attributes: name="value"
    for match in re.finditer(r'(\w+)="([^"]*)"', line):
        attributes[match.group(1)] = match.group(2)
    
    # Stack attributes: size="300","350"
    stack_match = re.search(r'(\w+)=("[\d,"\s]+"|"\d+")', line)
    if stack_match:
        attr_name = stack_match.group(1)
        stack_str = stack_match.group(2)
        values = re.findall(r'"(\d+)"', stack_str)
        if values:
            attributes[attr_name] = [int(v) for v in values]
    
    return ElementProperties(tag_type, attributes=attributes)


def get_plugin_info():
    """Plugin registration for auto-discovery"""
    return {
        'name': 'Properties',
        'panel_type': 'right',
        'panel_class': PropertiesPanel,
        'panel_icon': '⚙️',
        'panel_name': 'Properties',
        'priority': 10,  # Show first in right panel
        'callbacks': {},
        'menu_items': [
            {'menu': 'View', 'label': 'Toggle Properties Panel', 'command': 'toggle'}
        ]
    }


# Export
__all__ = [
    'PropertyValue',
    'PropertyGroup',
    'PropertyExtractor',
    'ElementProperties',
    'PropertiesPanel',
    'parse_line_to_element',
    'get_plugin_info'
]
