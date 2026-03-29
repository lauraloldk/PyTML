"""
Plugin Registry - Auto-discover and load plugins from plugins/ folder

Each plugin can define a get_plugin_info() function to declare how it integrates:

def get_plugin_info():
    return {
        'name': 'MyPlugin',
        'panel_type': 'center_tab',  # 'left', 'right', 'center_tab'
        'panel_class': MyPanelClass,
        'panel_icon': '🔧',
        'callbacks': {
            'on_code_change': callback_func,
            'on_element_select': callback_func,
        },
        'menu_items': [
            {'menu': 'View', 'label': 'Toggle My Panel', 'command': 'toggle'}
        ]
    }
"""

import os
import importlib
import importlib.util
from typing import Dict, List, Any, Optional


class PluginInfo:
    """Holds information about a loaded plugin"""
    
    def __init__(self, name: str, module, info: Dict[str, Any]):
        self.name = name
        self.module = module
        self.panel_type = info.get('panel_type', 'center_tab')
        self.panel_class = info.get('panel_class')
        self.panel_icon = info.get('panel_icon', '📦')
        self.panel_name = info.get('panel_name', name)
        self.callbacks = info.get('callbacks', {})
        self.menu_items = info.get('menu_items', [])
        self.init_args = info.get('init_args', {})
        self.priority = info.get('priority', 100)  # Lower = earlier
        
        # Runtime state
        self.panel_instance = None
        self.enabled = True


class PluginRegistry:
    """Registry that auto-discovers and manages plugins"""
    
    def __init__(self, plugins_dir: str = None):
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugins_dir = plugins_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'plugins'
        )
    
    def discover_plugins(self) -> List[PluginInfo]:
        """Scan plugins directory and load all plugins with get_plugin_info()"""
        if not os.path.exists(self.plugins_dir):
            return []
        
        discovered = []
        
        for filename in os.listdir(self.plugins_dir):
            if not filename.endswith('.py'):
                continue
            if filename.startswith('_'):
                continue
            
            module_name = filename[:-3]
            plugin_path = os.path.join(self.plugins_dir, filename)
            
            try:
                plugin_info = self._load_plugin(module_name, plugin_path)
                if plugin_info:
                    self.plugins[module_name] = plugin_info
                    discovered.append(plugin_info)
            except Exception as e:
                print(f"Warning: Failed to load plugin {module_name}: {e}")
        
        # Sort by priority
        discovered.sort(key=lambda p: p.priority)
        return discovered
    
    def _load_plugin(self, module_name: str, plugin_path: str) -> Optional[PluginInfo]:
        """Load a single plugin module"""
        spec = importlib.util.spec_from_file_location(
            f"plugins.{module_name}", plugin_path
        )
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check if plugin defines get_plugin_info
        if not hasattr(module, 'get_plugin_info'):
            return None
        
        info = module.get_plugin_info()
        if not info:
            return None
        
        return PluginInfo(module_name, module, info)
    
    def get_plugins_by_type(self, panel_type: str) -> List[PluginInfo]:
        """Get all plugins of a specific panel type"""
        return [p for p in self.plugins.values() 
                if p.panel_type == panel_type and p.enabled]
    
    def get_left_panels(self) -> List[PluginInfo]:
        """Get plugins that go in the left panel"""
        return self.get_plugins_by_type('left')
    
    def get_right_panels(self) -> List[PluginInfo]:
        """Get plugins that go in the right panel"""
        return self.get_plugins_by_type('right')
    
    def get_center_tabs(self) -> List[PluginInfo]:
        """Get plugins that are center tabs"""
        return self.get_plugins_by_type('center_tab')
    
    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get a specific plugin by name"""
        return self.plugins.get(name)
    
    def create_panel(self, plugin: PluginInfo, parent, editor=None) -> Any:
        """Create a panel instance for a plugin"""
        if not plugin.panel_class:
            return None
        
        # Build init args
        kwargs = dict(plugin.init_args)
        
        # Add editor callbacks if plugin requests them
        if 'editor_callback' in plugin.callbacks:
            kwargs['editor_callback'] = plugin.callbacks['editor_callback']
        
        if 'on_code_change' in plugin.callbacks:
            kwargs['on_code_change'] = plugin.callbacks['on_code_change']
        
        if 'on_element_select' in plugin.callbacks:
            kwargs['on_element_select'] = plugin.callbacks['on_element_select']
        
        if 'on_property_change' in plugin.callbacks:
            kwargs['on_property_change'] = plugin.callbacks['on_property_change']
        
        try:
            panel = plugin.panel_class(parent, **kwargs)
            plugin.panel_instance = panel
            return panel
        except Exception as e:
            print(f"Warning: Failed to create panel for {plugin.name}: {e}")
            return None


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry"""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def discover_plugins() -> List[PluginInfo]:
    """Discover all plugins"""
    return get_registry().discover_plugins()
