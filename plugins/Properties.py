"""
PyTML Editor Plugin: Properties Panel
Dynamisk indlæsning af properties fra lib filer og nodes
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


class PropertyValue:
    """Repræsenterer en property værdi"""
    
    def __init__(self, name, value, prop_type="string", editable=True, description=""):
        self.name = name
        self.value = value
        self.prop_type = prop_type  # 'string', 'int', 'bool', 'stack', 'color', 'list'
        self.editable = editable
        self.description = description
        self.on_change = None  # Callback når værdien ændres
    
    def set_value(self, value):
        """Sæt værdien"""
        old_value = self.value
        self.value = value
        if self.on_change and old_value != value:
            self.on_change(self.name, value, old_value)
    
    def get_value(self):
        """Hent værdien"""
        return self.value


class PropertyGroup:
    """Gruppe af relaterede properties"""
    
    def __init__(self, name, expanded=True):
        self.name = name
        self.expanded = expanded
        self.properties = []
    
    def add_property(self, prop):
        """Tilføj en property til gruppen"""
        self.properties.append(prop)
        return prop
    
    def get_property(self, name):
        """Hent en property ved navn"""
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None


class PropertyExtractor:
    """Udtræk properties dynamisk fra klasser og regex patterns"""
    
    def __init__(self):
        self.class_properties = {}  # Cache af klasse properties
        self.syntax_patterns = {}   # Cache af syntax patterns -> properties
        self._load_all()
    
    def _load_all(self):
        """Load properties fra alle libs"""
        libs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        
        for lib_file in glob.glob(os.path.join(libs_path, '*.py')):
            if lib_file.endswith('__init__.py'):
                continue
            self._load_from_file(lib_file)
        
        # Load fra Compiler.py
        compiler_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Compiler.py')
        self._load_from_file(compiler_path)
    
    def _load_from_file(self, filepath):
        """Load properties fra en fil"""
        module_name = os.path.basename(filepath)[:-3]
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Udtræk fra klasser
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if name.startswith('_') or name == 'ActionNode':
                    continue
                self.class_properties[name] = self._extract_class_properties(cls)
            
            # Udtræk fra parsers
            if hasattr(module, 'get_line_parsers'):
                for pattern, handler in module.get_line_parsers():
                    props = self._extract_pattern_properties(pattern)
                    if props:
                        self.syntax_patterns[pattern] = props
                        
        except Exception as e:
            print(f"PropertyExtractor: Kunne ikke loade {filepath}: {e}")
    
    def _extract_class_properties(self, cls):
        """Udtræk properties fra en klasse"""
        properties = []
        
        # Fra __init__ signatur
        try:
            sig = inspect.signature(cls.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                prop_type = 'string'
                default = None
                
                # Tjek annotation
                if param.annotation != inspect.Parameter.empty:
                    ann = str(param.annotation)
                    if 'int' in ann:
                        prop_type = 'int'
                    elif 'bool' in ann:
                        prop_type = 'bool'
                    elif 'list' in ann or 'List' in ann:
                        prop_type = 'list'
                
                # Tjek default værdi
                if param.default != inspect.Parameter.empty:
                    default = param.default
                    if isinstance(default, bool):
                        prop_type = 'bool'
                    elif isinstance(default, int):
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
        
        # Fra klasse attributter
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
            if attr_name in [p['name'] for p in properties]:
                continue
            
            attr = getattr(cls, attr_name, None)
            if not callable(attr) and not inspect.ismethod(attr):
                prop_type = 'string'
                if isinstance(attr, bool):
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
        """Udtræk properties fra et regex pattern"""
        properties = []
        
        # Find navngivne grupper eller standard grupper
        # F.eks: <window title="([^"]*)" size="(\d+)"
        
        # Find alle attribut navne
        attr_pattern = r'(\w+)=["\']\([^)]+\)["\']'
        for match in re.finditer(attr_pattern, pattern):
            attr_name = match.group(1)
            properties.append({
                'name': attr_name,
                'type': 'string',
                'default': '',
                'editable': True
            })
        
        # Tjek for specielle patterns
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
        """Hent properties for en klasse"""
        return self.class_properties.get(class_name, [])
    
    def get_properties_for_tag(self, tag_name):
        """Hent properties baseret på tag navn"""
        # Prøv at matche mod kendte klasser
        class_name = tag_name.title().replace('_', '') + 'Node'
        if class_name in self.class_properties:
            return self.class_properties[class_name]
        
        # Prøv uden Node suffix
        class_name = tag_name.title().replace('_', '')
        if class_name in self.class_properties:
            return self.class_properties[class_name]
        
        return []


class ElementProperties:
    """Properties for et PyTML element - dynamisk indlæst"""
    
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
        """Load properties baseret på element type"""
        props = self._extractor.get_properties_for_tag(self.element_type)
        
        if props:
            group = PropertyGroup(self.element_type.title())
            for prop_def in props:
                # Brug eksisterende værdi fra attributes hvis tilgængelig
                value = self.attributes.get(prop_def['name'], prop_def.get('default', ''))
                prop = PropertyValue(
                    name=prop_def['name'],
                    value=value,
                    prop_type=prop_def['type'],
                    editable=prop_def.get('editable', True)
                )
                group.add_property(prop)
            self.groups.append(group)
        else:
            # Fallback: Opret properties fra attributes
            if self.attributes:
                group = PropertyGroup("Attributes")
                for name, value in self.attributes.items():
                    prop_type = 'string'
                    if isinstance(value, bool):
                        prop_type = 'bool'
                    elif isinstance(value, int):
                        prop_type = 'int'
                    elif isinstance(value, list):
                        prop_type = 'list'
                    
                    prop = PropertyValue(name=name, value=value, prop_type=prop_type)
                    group.add_property(prop)
                self.groups.append(group)
    
    def add_group(self, group):
        """Tilføj en property gruppe"""
        self.groups.append(group)
        return group
    
    def get_all_properties(self):
        """Hent alle properties"""
        props = []
        for group in self.groups:
            props.extend(group.properties)
        return props
    
    def to_pytml(self):
        """Generer PyTML kode fra properties"""
        props = {p.name: p.value for p in self.get_all_properties()}
        
        # Byg tag
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
        """Hent værdi af en property"""
        for group in self.groups:
            prop = group.get_property(name)
            if prop:
                return prop.value
        return ""


class PropertiesPanel(ttk.Frame):
    """Panel der viser properties for valgt element - dynamisk"""
    
    def __init__(self, parent, on_property_change=None):
        super().__init__(parent)
        self.on_property_change = on_property_change
        self.current_element = None
        self.property_widgets = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Opsæt UI"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(header_frame, text="⚙️ Properties", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        
        self.element_label = ttk.Label(header_frame, text="(ingen valgt)")
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
        
        # Placeholder tekst
        self.placeholder = ttk.Label(self.scrollable_frame, text="Vælg et element for at se properties")
        self.placeholder.pack(pady=20)
    
    def load_element(self, element):
        """Load properties for et element"""
        self.current_element = element
        
        # Ryd eksisterende widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.property_widgets = {}
        
        if element is None:
            self.element_label.config(text="(ingen valgt)")
            self.placeholder = ttk.Label(self.scrollable_frame, text="Vælg et element for at se properties")
            self.placeholder.pack(pady=20)
            return
        
        self.element_label.config(text=f"<{element.element_type}>")
        
        # Opret widgets for hver gruppe
        for group in element.groups:
            self._create_group(group)
    
    def load_from_line(self, line):
        """Parse en linje og vis properties"""
        element = parse_line_to_element(line)
        if element:
            self.load_element(element)
    
    def _create_group(self, group):
        """Opret widgets for en property gruppe"""
        # Gruppe header
        group_frame = ttk.LabelFrame(self.scrollable_frame, text=group.name)
        group_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Properties
        for prop in group.properties:
            self._create_property_widget(group_frame, prop)
    
    def _create_property_widget(self, parent, prop):
        """Opret widget for en property"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Label
        ttk.Label(frame, text=prop.name, width=12).pack(side=tk.LEFT)
        
        # Input widget baseret på type
        if prop.prop_type == 'bool':
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
            # For stack/list, vis som komma-separeret
            val = prop.value
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            var = tk.StringVar(value=val if val else "")
            widget = ttk.Entry(frame, textvariable=var)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_list_change(p, v))
        
        elif prop.prop_type == 'color':
            var = tk.StringVar(value=prop.value if prop.value else "#ffffff")
            widget = ttk.Entry(frame, textvariable=var, width=15)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_string_change(p, v))
            # Color preview
            try:
                preview = tk.Frame(frame, width=20, height=20, bg=prop.value if prop.value else '#ffffff')
                preview.pack(side=tk.RIGHT, padx=2)
            except:
                pass
        
        else:  # string (default)
            var = tk.StringVar(value=str(prop.value) if prop.value is not None else "")
            widget = ttk.Entry(frame, textvariable=var)
            widget.var = var
            var.trace('w', lambda *args, p=prop, v=var: self._on_string_change(p, v))
        
        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        if not prop.editable:
            widget.config(state='disabled')
        
        self.property_widgets[prop.name] = widget
    
    def _on_string_change(self, prop, var):
        """Håndter string ændring"""
        prop.set_value(var.get())
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _on_int_change(self, prop, var):
        """Håndter int ændring"""
        try:
            prop.set_value(int(var.get()))
        except ValueError:
            pass
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _on_bool_change(self, prop, var):
        """Håndter bool ændring"""
        prop.set_value(var.get())
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)
    
    def _on_list_change(self, prop, var):
        """Håndter list/stack ændring"""
        val = var.get()
        # Parse komma-separeret liste
        if val:
            parts = [p.strip() for p in val.split(',')]
            # Prøv at konvertere til int hvis muligt
            try:
                parts = [int(p) for p in parts]
            except:
                pass
            prop.set_value(parts)
        else:
            prop.set_value([])
        
        if self.on_property_change:
            self.on_property_change(self.current_element, prop)


def parse_line_to_element(line):
    """Parse en PyTML linje og returner ElementProperties"""
    line = line.strip()
    if not line.startswith('<'):
        return None
    
    # Find tag type
    tag_match = re.match(r'<(\w+)', line)
    if not tag_match:
        return None
    
    tag_type = tag_match.group(1)
    
    # Udtræk attributter
    attributes = {}
    
    # Standard attributter: name="value"
    for match in re.finditer(r'(\w+)="([^"]*)"', line):
        attributes[match.group(1)] = match.group(2)
    
    # Stack attributter: size="300","350"
    stack_match = re.search(r'(\w+)=("[\d,"\s]+"|"\d+")', line)
    if stack_match:
        attr_name = stack_match.group(1)
        stack_str = stack_match.group(2)
        values = re.findall(r'"(\d+)"', stack_str)
        if values:
            attributes[attr_name] = [int(v) for v in values]
    
    return ElementProperties(tag_type, attributes=attributes)


# Eksporter
__all__ = [
    'PropertyValue',
    'PropertyGroup',
    'PropertyExtractor',
    'ElementProperties', 
    'PropertiesPanel',
    'parse_line_to_element'
]
