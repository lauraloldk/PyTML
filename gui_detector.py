"""
PyTML GUI Detector
Intelligent detection of graphical packages, modules and classes.
Detects visual elements by analyzing property types, method signatures, and inheritance.
"""

import importlib
import inspect
import pkgutil
import sys

# Known graphical frameworks with metadata
GRAPHICAL_PACKAGES = {
    'tkinter': {
        'icon': '🪟', 
        'type': 'widget', 
        'framework': 'tkinter',
        'description': 'Native Python GUI toolkit',
        'embed_method': 'native',
        'display': 'window'
    },
    'pygame': {
        'icon': '🎮', 
        'type': 'surface', 
        'framework': 'pygame',
        'description': 'Game development library',
        'embed_method': 'embed',
        'display': 'window'
    },
    'PIL': {
        'icon': '🖼️', 
        'type': 'graphic', 
        'framework': 'pillow',
        'description': 'Image processing library',
        'embed_method': 'canvas',
        'display': 'image'
    },
    'Pillow': {
        'icon': '🖼️', 
        'type': 'graphic', 
        'framework': 'pillow',
        'description': 'Image processing library',
        'embed_method': 'canvas',
        'display': 'image'
    },
    'matplotlib': {
        'icon': '📊', 
        'type': 'graphic', 
        'framework': 'matplotlib',
        'description': 'Plotting library',
        'embed_method': 'canvas',
        'display': 'figure'
    },
    'PyQt5': {
        'icon': '🖥️', 
        'type': 'widget', 
        'framework': 'qt',
        'description': 'Qt5 GUI framework',
        'embed_method': 'native',
        'display': 'window'
    },
    'PyQt6': {
        'icon': '🖥️', 
        'type': 'widget', 
        'framework': 'qt',
        'description': 'Qt6 GUI framework',
        'embed_method': 'native',
        'display': 'window'
    },
    'PySide2': {
        'icon': '🖥️', 
        'type': 'widget', 
        'framework': 'qt',
        'description': 'Qt for Python (PySide2)',
        'embed_method': 'native',
        'display': 'window'
    },
    'PySide6': {
        'icon': '🖥️', 
        'type': 'widget', 
        'framework': 'qt',
        'description': 'Qt for Python (PySide6)',
        'embed_method': 'native',
        'display': 'window'
    },
    'wx': {
        'icon': '🪟', 
        'type': 'widget', 
        'framework': 'wxpython',
        'description': 'wxWidgets GUI toolkit',
        'embed_method': 'native',
        'display': 'window'
    },
    'kivy': {
        'icon': '📱', 
        'type': 'widget', 
        'framework': 'kivy',
        'description': 'Multi-touch GUI framework',
        'embed_method': 'native',
        'display': 'window'
    },
    'arcade': {
        'icon': '🕹️', 
        'type': 'surface', 
        'framework': 'arcade',
        'description': '2D game library',
        'embed_method': 'embed',
        'display': 'window'
    },
    'pyglet': {
        'icon': '🎮', 
        'type': 'surface', 
        'framework': 'pyglet',
        'description': 'Multimedia library',
        'embed_method': 'embed',
        'display': 'window'
    },
    'turtle': {
        'icon': '🐢', 
        'type': 'graphic', 
        'framework': 'turtle',
        'description': 'Turtle graphics',
        'embed_method': 'canvas',
        'display': 'canvas'
    },
    'vtk': {
        'icon': '🔬', 
        'type': 'graphic', 
        'framework': 'vtk',
        'description': '3D visualization toolkit',
        'embed_method': 'embed',
        'display': 'window'
    },
    'cv2': {
        'icon': '👁️', 
        'type': 'graphic', 
        'framework': 'opencv',
        'description': 'Computer vision library',
        'embed_method': 'canvas',
        'display': 'window'
    },
    'cairo': {
        'icon': '✏️', 
        'type': 'graphic', 
        'framework': 'cairo',
        'description': '2D graphics library',
        'embed_method': 'canvas',
        'display': 'surface'
    },
    'reportlab': {
        'icon': '📄', 
        'type': 'graphic', 
        'framework': 'reportlab',
        'description': 'PDF generation',
        'embed_method': 'file',
        'display': 'document'
    },
    'plotly': {
        'icon': '📈', 
        'type': 'graphic', 
        'framework': 'plotly',
        'description': 'Interactive plotting',
        'embed_method': 'html',
        'display': 'browser'
    },
    'bokeh': {
        'icon': '📊', 
        'type': 'graphic', 
        'framework': 'bokeh',
        'description': 'Interactive visualization',
        'embed_method': 'html',
        'display': 'browser'
    },
    'dash': {
        'icon': '🌐', 
        'type': 'widget', 
        'framework': 'dash',
        'description': 'Web application framework',
        'embed_method': 'html',
        'display': 'browser'
    },
    'manim': {
        'icon': '🎬', 
        'type': 'graphic', 
        'framework': 'manim',
        'description': 'Mathematical animation',
        'embed_method': 'video',
        'display': 'video'
    },
    'moderngl': {
        'icon': '🎨', 
        'type': 'surface', 
        'framework': 'opengl',
        'description': 'Modern OpenGL wrapper',
        'embed_method': 'embed',
        'display': 'window'
    },
    'pyopengl': {
        'icon': '🎨', 
        'type': 'surface', 
        'framework': 'opengl',
        'description': 'OpenGL bindings',
        'embed_method': 'embed',
        'display': 'window'
    },
    'dearpygui': {
        'icon': '🖥️', 
        'type': 'widget', 
        'framework': 'dearpygui',
        'description': 'GPU-accelerated GUI',
        'embed_method': 'native',
        'display': 'window'
    },
}

# GUI element type categories
GUI_ELEMENT_TYPES = {
    'container': {
        'icon': '📦',
        'description': 'Container that holds other elements',
        'examples': ['Window', 'Frame', 'Panel', 'Dialog']
    },
    'widget': {
        'icon': '🔲',
        'description': 'Interactive GUI widget',
        'examples': ['Button', 'Label', 'Entry', 'Checkbox']
    },
    'graphic': {
        'icon': '🎨',
        'description': 'Graphics/drawing element',
        'examples': ['Canvas', 'Image', 'Shape', 'Plot']
    },
    'surface': {
        'icon': '🖼️',
        'description': 'Rendering surface',
        'examples': ['Surface', 'Screen', 'Display']
    },
    'console': {
        'icon': '💻',
        'description': 'Console/terminal output',
        'examples': ['print', 'Console', 'Terminal']
    }
}

# Property types that indicate graphical elements
# These properties are typically only found on visual elements
GRAPHICAL_PROPERTY_INDICATORS = {
    # Color properties - strong indicator of visual element
    'Color': {
        'icon': '🎨',
        'weight': 100,
        'description': 'Color property - only visual elements have colors',
        'patterns': [
            'background', 'bg', 'foreground', 'fg', 'color', 'colour',
            'activebackground', 'activeforeground', 'disabledforeground',
            'highlightbackground', 'highlightcolor', 'insertbackground',
            'selectbackground', 'selectforeground', 'troughcolor',
            'fill', 'outline', 'stroke', 'tint'
        ]
    },
    # Size/dimension properties
    'Dimension': {
        'icon': '📏',
        'weight': 50,
        'description': 'Size/dimension property',
        'patterns': [
            'width', 'height', 'size', 'minwidth', 'minheight',
            'maxwidth', 'maxheight', 'borderwidth', 'bd',
            'padx', 'pady', 'padding', 'margin', 'spacing'
        ]
    },
    # Position properties
    'Position': {
        'icon': '📍',
        'weight': 40,
        'description': 'Position/layout property',
        'patterns': [
            'x', 'y', 'pos', 'position', 'anchor', 'sticky',
            'row', 'column', 'rowspan', 'columnspan',
            'left', 'right', 'top', 'bottom', 'center'
        ]
    },
    # Font/text styling
    'Font': {
        'icon': '🔤',
        'weight': 60,
        'description': 'Font/text styling property',
        'patterns': [
            'font', 'fontfamily', 'fontsize', 'fontweight',
            'fontstyle', 'textfont', 'labelfont'
        ]
    },
    # Visual style properties
    'Style': {
        'icon': '🎭',
        'weight': 70,
        'description': 'Visual style property',
        'patterns': [
            'relief', 'border', 'bordercolor', 'borderstyle',
            'style', 'theme', 'appearance', 'shadow', 'opacity',
            'alpha', 'transparent', 'visible', 'hidden'
        ]
    },
    # Image/graphics properties
    'Image': {
        'icon': '🖼️',
        'weight': 90,
        'description': 'Image/graphics property',
        'patterns': [
            'image', 'icon', 'bitmap', 'photo', 'picture',
            'texture', 'sprite', 'graphic', 'canvas'
        ]
    },
    # Cursor properties
    'Cursor': {
        'icon': '👆',
        'weight': 80,
        'description': 'Cursor property - indicates interactive element',
        'patterns': [
            'cursor', 'pointer', 'mouse'
        ]
    },
    # State properties (visual state)
    'State': {
        'icon': '⚡',
        'weight': 30,
        'description': 'Widget state property',
        'patterns': [
            'state', 'enabled', 'disabled', 'active', 'focused',
            'selected', 'pressed', 'hover', 'checked'
        ]
    }
}

# Method names that indicate graphical classes
GRAPHICAL_METHOD_INDICATORS = {
    'render': 80,
    'draw': 90,
    'paint': 90,
    'display': 70,
    'show': 60,
    'hide': 60,
    'update': 30,
    'refresh': 40,
    'redraw': 80,
    'blit': 90,
    'configure': 40,
    'pack': 50,
    'grid': 50,
    'place': 50,
    'create_window': 70,
    'create_widget': 70,
    'set_color': 100,
    'set_background': 100,
    'set_foreground': 100,
    'set_font': 80,
    'set_size': 60,
    'resize': 60,
    'move': 50,
    'bind': 40,
}

# Base classes that indicate graphical inheritance
GRAPHICAL_BASE_CLASSES = {
    'Widget': 100,
    'Frame': 90,
    'Canvas': 100,
    'Toplevel': 90,
    'BaseWidget': 100,
    'Misc': 50,
    'QWidget': 100,
    'QMainWindow': 100,
    'QFrame': 90,
    'Surface': 100,
    'Sprite': 100,
    'Window': 90,
    'Panel': 80,
    'Control': 80,
}


class GUIDetector:
    """
    Intelligent GUI detection system.
    Analyzes Python packages, modules and classes to determine
    if they contain graphical/visual elements.
    """
    
    def __init__(self):
        self.cache = {}
        self._installed_packages = None
    
    def get_installed_graphical_packages(self):
        """Get list of installed packages that are known graphical frameworks"""
        if self._installed_packages is not None:
            return self._installed_packages
        
        installed = []
        for pkg_name, info in GRAPHICAL_PACKAGES.items():
            try:
                importlib.import_module(pkg_name)
                installed.append({
                    'name': pkg_name,
                    'icon': info['icon'],
                    'type': info['type'],
                    'framework': info['framework'],
                    'description': info['description'],
                    'embed_method': info['embed_method'],
                    'display': info['display']
                })
            except ImportError:
                pass
        
        self._installed_packages = installed
        return installed
    
    def analyze_class_properties(self, cls):
        """
        Analyze a class for graphical property indicators.
        Returns a dict with detected property types and their scores.
        """
        results = {
            'properties': {},
            'total_score': 0,
            'property_types': {},
            'is_graphical': False
        }
        
        # Get all attributes that might be config options
        config_options = []
        
        # Try to get tkinter-style configure options
        try:
            instance = cls.__new__(cls)
            if hasattr(instance, 'configure'):
                # This is likely a tkinter widget
                pass
        except:
            pass
        
        # Analyze class attributes
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
            
            attr_name_lower = attr_name.lower()
            
            # Check against each property type
            for prop_type, info in GRAPHICAL_PROPERTY_INDICATORS.items():
                for pattern in info['patterns']:
                    if pattern in attr_name_lower:
                        if prop_type not in results['property_types']:
                            results['property_types'][prop_type] = {
                                'icon': info['icon'],
                                'weight': info['weight'],
                                'matches': []
                            }
                        results['property_types'][prop_type]['matches'].append(attr_name)
                        results['total_score'] += info['weight']
                        break
        
        # Determine if graphical based on score and property types
        results['is_graphical'] = (
            results['total_score'] >= 100 or 
            'Color' in results['property_types'] or
            'Image' in results['property_types']
        )
        
        return results
    
    def analyze_class_methods(self, cls):
        """
        Analyze a class for graphical method indicators.
        Returns a dict with detected methods and their scores.
        """
        results = {
            'methods': {},
            'total_score': 0,
            'is_graphical': False
        }
        
        for name in dir(cls):
            if name.startswith('_'):
                continue
            
            name_lower = name.lower()
            
            for method_pattern, weight in GRAPHICAL_METHOD_INDICATORS.items():
                if method_pattern in name_lower:
                    results['methods'][name] = weight
                    results['total_score'] += weight
                    break
        
        results['is_graphical'] = results['total_score'] >= 150
        return results
    
    def analyze_class_inheritance(self, cls):
        """
        Analyze a class's inheritance for graphical base classes.
        Returns a dict with detected base classes and their scores.
        """
        results = {
            'base_classes': {},
            'total_score': 0,
            'is_graphical': False
        }
        
        try:
            mro = inspect.getmro(cls)
            for base in mro:
                base_name = base.__name__
                if base_name in GRAPHICAL_BASE_CLASSES:
                    score = GRAPHICAL_BASE_CLASSES[base_name]
                    results['base_classes'][base_name] = score
                    results['total_score'] += score
        except:
            pass
        
        results['is_graphical'] = results['total_score'] >= 80
        return results
    
    def detect_class(self, cls):
        """
        Full analysis of a class for graphical indicators.
        Combines property, method, and inheritance analysis.
        """
        cache_key = f"{cls.__module__}.{cls.__name__}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        prop_analysis = self.analyze_class_properties(cls)
        method_analysis = self.analyze_class_methods(cls)
        inherit_analysis = self.analyze_class_inheritance(cls)
        
        total_score = (
            prop_analysis['total_score'] + 
            method_analysis['total_score'] + 
            inherit_analysis['total_score']
        )
        
        is_graphical = (
            prop_analysis['is_graphical'] or 
            method_analysis['is_graphical'] or 
            inherit_analysis['is_graphical'] or
            total_score >= 200
        )
        
        # Determine element type
        element_type = 'widget'  # default
        if inherit_analysis['base_classes']:
            if any(b in ['Canvas', 'Surface'] for b in inherit_analysis['base_classes']):
                element_type = 'graphic'
            elif any(b in ['Frame', 'Toplevel', 'Window', 'QMainWindow'] for b in inherit_analysis['base_classes']):
                element_type = 'container'
        
        result = {
            'class_name': cls.__name__,
            'module': cls.__module__,
            'is_graphical': is_graphical,
            'confidence': min(total_score, 1000),
            'element_type': element_type,
            'property_analysis': prop_analysis,
            'method_analysis': method_analysis,
            'inheritance_analysis': inherit_analysis,
            'property_types_found': list(prop_analysis['property_types'].keys()),
            'graphical_methods_found': list(method_analysis['methods'].keys()),
            'graphical_bases_found': list(inherit_analysis['base_classes'].keys())
        }
        
        self.cache[cache_key] = result
        return result
    
    def detect_module(self, module_name):
        """
        Analyze an entire module for graphical classes.
        Returns a summary with all graphical classes found.
        """
        result = {
            'module_name': module_name,
            'is_graphical_package': module_name in GRAPHICAL_PACKAGES,
            'package_info': GRAPHICAL_PACKAGES.get(module_name, {}),
            'graphical_classes': [],
            'non_graphical_classes': [],
            'property_types_summary': {},
            'total_graphical': 0
        }
        
        try:
            module = importlib.import_module(module_name)
            
            for name in dir(module):
                if name.startswith('_'):
                    continue
                
                obj = getattr(module, name, None)
                if obj is None or not inspect.isclass(obj):
                    continue
                
                # Only analyze classes defined in this module
                if obj.__module__ != module_name:
                    continue
                
                class_info = self.detect_class(obj)
                
                if class_info['is_graphical']:
                    result['graphical_classes'].append(class_info)
                    result['total_graphical'] += 1
                    
                    # Aggregate property types
                    for prop_type in class_info['property_types_found']:
                        if prop_type not in result['property_types_summary']:
                            result['property_types_summary'][prop_type] = []
                        result['property_types_summary'][prop_type].append(name)
                else:
                    result['non_graphical_classes'].append({
                        'class_name': name,
                        'confidence': class_info['confidence']
                    })
        
        except ImportError as e:
            result['error'] = f"Could not import module: {e}"
        except Exception as e:
            result['error'] = f"Error analyzing module: {e}"
        
        return result
    
    def find_modules_with_property_type(self, property_type, modules=None):
        """
        Find all modules/classes that have a specific property type.
        For example, find all modules with 'Color' properties.
        
        Args:
            property_type: One of the GRAPHICAL_PROPERTY_INDICATORS keys
            modules: List of module names to search (default: installed graphical packages)
        
        Returns:
            List of modules/classes with that property type
        """
        if modules is None:
            modules = [p['name'] for p in self.get_installed_graphical_packages()]
        
        results = []
        
        for module_name in modules:
            module_info = self.detect_module(module_name)
            
            if property_type in module_info.get('property_types_summary', {}):
                results.append({
                    'module': module_name,
                    'classes': module_info['property_types_summary'][property_type],
                    'icon': GRAPHICAL_PACKAGES.get(module_name, {}).get('icon', '📦')
                })
        
        return results
    
    def get_property_type_info(self, property_type):
        """Get information about a property type indicator"""
        return GRAPHICAL_PROPERTY_INDICATORS.get(property_type, {})
    
    def get_all_property_types(self):
        """Get list of all property type indicators"""
        return [
            {
                'name': name,
                'icon': info['icon'],
                'description': info['description'],
                'weight': info['weight'],
                'pattern_count': len(info['patterns'])
            }
            for name, info in GRAPHICAL_PROPERTY_INDICATORS.items()
        ]
    
    def quick_check(self, module_name):
        """
        Quick check if a module is likely graphical.
        Faster than full analysis.
        """
        # Check if it's a known graphical package
        if module_name in GRAPHICAL_PACKAGES:
            info = GRAPHICAL_PACKAGES[module_name]
            return {
                'is_graphical': True,
                'confidence': 1000,
                'reason': 'Known graphical package',
                'info': info
            }
        
        # Check if module name contains graphical keywords
        graphical_keywords = ['gui', 'window', 'widget', 'canvas', 'draw', 'render', 
                            'display', 'screen', 'graphics', 'visual', 'ui']
        
        module_lower = module_name.lower()
        for keyword in graphical_keywords:
            if keyword in module_lower:
                return {
                    'is_graphical': True,
                    'confidence': 500,
                    'reason': f'Module name contains "{keyword}"',
                    'info': {}
                }
        
        return {
            'is_graphical': False,
            'confidence': 0,
            'reason': 'No graphical indicators in name',
            'info': {}
        }
    
    def get_graphical_classes_by_property(self, property_type='Color', modules=None):
        """
        Get a detailed list of all classes that have a specific property type.
        This is useful for finding elements that can use colors, images, fonts, etc.
        
        Args:
            property_type: One of 'Color', 'Dimension', 'Position', 'Font', 'Style', 'Image', 'Cursor', 'State'
            modules: List of module names to search (default: all installed graphical packages)
        
        Returns:
            Dict with module names as keys, containing lists of class info
        """
        if modules is None:
            modules = [p['name'] for p in self.get_installed_graphical_packages()]
        
        results = {}
        
        for module_name in modules:
            try:
                module = importlib.import_module(module_name)
                
                module_results = []
                for name in dir(module):
                    if name.startswith('_'):
                        continue
                    
                    obj = getattr(module, name, None)
                    if not inspect.isclass(obj):
                        continue
                    
                    # Only classes from this module
                    if obj.__module__ != module_name:
                        continue
                    
                    # Analyze properties
                    prop_analysis = self.analyze_class_properties(obj)
                    
                    if property_type in prop_analysis['property_types']:
                        matches = prop_analysis['property_types'][property_type]['matches']
                        module_results.append({
                            'class_name': name,
                            'property_type': property_type,
                            'matching_attributes': matches,
                            'total_score': prop_analysis['total_score'],
                            'is_graphical': prop_analysis['is_graphical'],
                            'all_property_types': list(prop_analysis['property_types'].keys())
                        })
                
                if module_results:
                    pkg_info = GRAPHICAL_PACKAGES.get(module_name, {})
                    results[module_name] = {
                        'icon': pkg_info.get('icon', '📦'),
                        'framework': pkg_info.get('framework', module_name),
                        'classes': module_results
                    }
            
            except Exception as e:
                pass  # Skip modules that can't be imported
        
        return results
    
    def summarize_graphical_capabilities(self, modules=None):
        """
        Create a summary of graphical capabilities across all modules.
        Shows which modules support colors, images, fonts, etc.
        
        Returns a dict organized by property type.
        """
        if modules is None:
            modules = [p['name'] for p in self.get_installed_graphical_packages()]
        
        summary = {}
        
        for prop_type, info in GRAPHICAL_PROPERTY_INDICATORS.items():
            classes_with_prop = self.get_graphical_classes_by_property(prop_type, modules)
            
            total_classes = sum(len(m['classes']) for m in classes_with_prop.values())
            
            summary[prop_type] = {
                'icon': info['icon'],
                'description': info['description'],
                'weight': info['weight'],
                'total_modules': len(classes_with_prop),
                'total_classes': total_classes,
                'modules': list(classes_with_prop.keys())
            }
        
        return summary


# Convenience functions
def is_graphical_module(module_name):
    """Quick check if a module is graphical"""
    detector = GUIDetector()
    return detector.quick_check(module_name)['is_graphical']

def is_graphical_class(cls):
    """Quick check if a class is graphical"""
    detector = GUIDetector()
    return detector.detect_class(cls)['is_graphical']

def get_graphical_packages():
    """Get list of installed graphical packages"""
    detector = GUIDetector()
    return detector.get_installed_graphical_packages()

def find_color_elements(modules=None):
    """Find all elements that support color properties"""
    detector = GUIDetector()
    return detector.find_modules_with_property_type('Color', modules)

def find_elements_by_property(property_type, modules=None):
    """Find all elements that have a specific property type"""
    detector = GUIDetector()
    return detector.get_graphical_classes_by_property(property_type, modules)

def get_capabilities_summary(modules=None):
    """Get a summary of graphical capabilities"""
    detector = GUIDetector()
    return detector.summarize_graphical_capabilities(modules)


# Testing
if __name__ == '__main__':
    print("=" * 60)
    print("PyTML GUI Detector Test")
    print("=" * 60)
    
    detector = GUIDetector()
    
    # Test installed packages
    print("\n📦 Installed Graphical Packages:")
    for pkg in detector.get_installed_graphical_packages():
        print(f"  {pkg['icon']} {pkg['name']} ({pkg['type']})")
    
    # Test property types
    print("\n🎨 Property Type Indicators:")
    for ptype in detector.get_all_property_types():
        print(f"  {ptype['icon']} {ptype['name']}: {ptype['description']}")
    
    # Test tkinter detection
    print("\n🔍 Testing tkinter.Button detection:")
    try:
        import tkinter as tk
        result = detector.detect_class(tk.Button)
        print(f"  Is Graphical: {result['is_graphical']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Element Type: {result['element_type']}")
        print(f"  Property Types: {result['property_types_found']}")
        print(f"  Graphical Methods: {result['graphical_methods_found'][:5]}...")
        print(f"  Base Classes: {result['graphical_bases_found']}")
    except ImportError:
        print("  tkinter not available")
    
    # Test finding Color elements
    print("\n🎨 Modules with Color properties:")
    color_modules = detector.find_modules_with_property_type('Color')
    for mod in color_modules:
        print(f"  {mod['icon']} {mod['module']}: {mod['classes'][:3]}...")
    
    # Test capabilities summary
    print("\n📊 Graphical Capabilities Summary:")
    summary = detector.summarize_graphical_capabilities()
    for prop_type, info in summary.items():
        if info['total_classes'] > 0:
            print(f"  {info['icon']} {prop_type}: {info['total_classes']} classes in {info['total_modules']} modules")
    
    print("\n✅ GUI Detector ready!")
