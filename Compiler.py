"""
PyTML Compiler
Håndterer parsing og kompilering af PyTML kode

Bruger:
- libs/core.py for base klasser
- libs/registry.py for tag metadata og semantisk analyse
"""

import re
from libs.var import VariableStore, VarNode
from libs.output import OutputNode
from libs.console_utils import NoTerminateNode, wait_for_close, reset as reset_console

# Import core og registry
from libs.core import ActionNode as CoreActionNode, resolve_value, resolve_attributes
from libs.registry import TagRegistry, SemanticAnalyzer, TagCategory


class ActionNode:
    """Base klasse for alle actions i PyTML action tree"""
    
    def __init__(self, tag_name, attributes=None):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.children = []
        self.parent = None
        self._ready = False
        self._executed = False
    
    def add_child(self, child):
        """Tilføj et child - parent venter altid på children"""
        child.parent = self
        self.children.append(child)
        return child
    
    def children_ready(self):
        """Tjek om alle children er klar"""
        return all(child.is_ready() for child in self.children)
    
    def is_ready(self):
        """En node er klar når den selv og alle children er færdige"""
        return self._ready and self.children_ready()
    
    def execute(self, context):
        """Udfør denne action - override i subklasser"""
        self._ready = True
        self._executed = True


class BlockNode(ActionNode):
    """Block node: <block> - grupperer actions"""
    
    def execute(self, context):
        # Udfør alle children sekventielt
        for child in self.children:
            child.execute(context)
        
        self._ready = True
        self._executed = True


class IfNode(ActionNode):
    """Conditional node: <if condition="...">"""
    
    def execute(self, context):
        condition = self.attributes.get('condition', 'false')
        
        # Evaluer condition
        result = self._evaluate_condition(condition, context)
        
        if result:
            for child in self.children:
                child.execute(context)
        
        self._ready = True
        self._executed = True
    
    def _evaluate_condition(self, condition, context):
        """Evaluer en simpel condition"""
        # Erstat <x_value> referencer med variabel værdier
        pattern_tag = r'<(\w+)_value>'
        
        def replace_tag_var(match):
            var_name = match.group(1)
            value = context['variables'].get_value(var_name)
            if isinstance(value, str):
                return f'"{value}"'
            return str(value) if value is not None else 'None'
        
        condition = re.sub(pattern_tag, replace_tag_var, condition)
        
        # Erstat også $variabel referencer (for bagudkompatibilitet)
        pattern_dollar = r'\$(\w+)'
        
        def replace_dollar_var(match):
            var_name = match.group(1)
            value = context['variables'].get_value(var_name)
            if isinstance(value, str):
                return f'"{value}"'
            return str(value) if value is not None else 'None'
        
        condition = re.sub(pattern_dollar, replace_dollar_var, condition)
        
        try:
            return eval(condition)
        except Exception as e:
            print(f"Condition error: {e} in '{condition}'")
            return False


class LoopNode(ActionNode):
    """Loop node: <loop count="n"> eller <loop from="x" to="y">"""
    
    def execute(self, context):
        count = self.attributes.get('count')
        from_val = self.attributes.get('from', '0')
        to_val = self.attributes.get('to')
        var_name = self.attributes.get('var', 'i')
        
        if count:
            iterations = int(count)
            for i in range(iterations):
                context['variables'].set(var_name, i)
                for child in self.children:
                    child.execute(context)
        elif to_val:
            start = int(from_val)
            end = int(to_val)
            for i in range(start, end + 1):
                context['variables'].set(var_name, i)
                for child in self.children:
                    child.execute(context)
        
        self._ready = True
        self._executed = True


class ForeverNode(ActionNode):
    """Forever loop node: <forever> - kører indtil programmet lukkes
    Bruges typisk sammen med GUI event loops.
    
    Registrerer sig selv i context['forever_loops'] så flere loops kan køre.
    Interval kan justeres med 'interval' attribut (default 100ms).
    """
    
    def execute(self, context):
        import tkinter as tk
        
        # Hent interval fra attributter (default 100ms)
        interval = int(self.attributes.get('interval', 100))
        
        # Registrer denne loop i context
        if 'forever_loops' not in context:
            context['forever_loops'] = []
        context['forever_loops'].append(self)
        
        # Hent tkinter root hvis det findes
        root = None
        if 'windows' in context:
            windows = context['windows']
            if hasattr(windows, '_tk_root') and windows._tk_root:
                root = windows._tk_root
        
        if root:
            # GUI mode: Brug tkinter event loop med after()
            # VIGTIGT: Kald IKKE mainloop() her - lad compileren håndtere det
            def loop_iteration():
                try:
                    # Tjek om root stadig eksisterer
                    if not root.winfo_exists():
                        return
                    for child in self.children:
                        child.execute(context)
                    # Schedule næste iteration
                    root.after(interval, loop_iteration)
                except tk.TclError:
                    # Vindue lukket
                    pass
            
            # Start loop (non-blocking)
            loop_iteration()
        else:
            # Terminal mode: Simpel uendelig loop
            try:
                while True:
                    for child in self.children:
                        child.execute(context)
                    # Lille pause for at undgå 100% CPU
                    import time
                    time.sleep(interval / 1000.0)
            except KeyboardInterrupt:
                pass
        
        self._ready = True
        self._executed = True


class EventIfNode(ActionNode):
    """Event-based if node: <if event="<btn_click>">
    Tjekker om et event er sket og udfører children hvis ja."""
    
    def execute(self, context):
        event = self.attributes.get('event', '')
        
        # Parse event: <elementname_eventtype>
        import re
        match = re.match(r'<(\w+)_(\w+)>', event)
        if match:
            element_name = match.group(1)
            event_type = match.group(2)
            
            # Tjek om eventet er trigget
            if self._check_event(element_name, event_type, context):
                for child in self.children:
                    child.execute(context)
                # Clear eventet efter håndtering
                self._clear_event(element_name, event_type, context)
        
        self._ready = True
        self._executed = True
    
    def _check_event(self, element_name, event_type, context):
        """Tjek om et event er sket"""
        events = context.get('events', {})
        event_key = f"{element_name}_{event_type}"
        return events.get(event_key, False)
    
    def _clear_event(self, element_name, event_type, context):
        """Clear et event efter håndtering"""
        if 'events' in context:
            event_key = f"{element_name}_{event_type}"
            context['events'][event_key] = False


class DynamicActionNode(ActionNode):
    """
    Dynamisk action node der bruger registry til at forstå elementer.
    
    Håndterer patterns som:
    - <element_action> (f.eks. <wnd1_show>, <btn1_click>)
    - <element_property="value"> (f.eks. <wnd1_title="Test">, <btn1_text="OK">)
    
    Bruger TagRegistry til at inferere element type og finde korrekt handler.
    """
    
    def __init__(self, tag_name, attributes=None):
        super().__init__(tag_name, attributes)
        self.element_name = attributes.get('element_name')
        self.action = attributes.get('action')
        self.property_name = attributes.get('property')
        self.value = attributes.get('value')
    
    def execute(self, context):
        registry = TagRegistry.instance()
        
        # Inferer element type
        tag_def = registry.infer_element_type(self.element_name)
        
        if self.action:
            self._execute_action(context, tag_def)
        elif self.property_name:
            self._execute_property(context, tag_def)
        
        self._ready = True
        self._executed = True
    
    def _execute_action(self, context, tag_def):
        """Udfør en action på et element"""
        # Find element i context
        element = self._find_element(context)
        if not element:
            return
        
        # Kald metoden hvis den findes
        if hasattr(element, self.action):
            method = getattr(element, self.action)
            if callable(method):
                if self.value is not None:
                    resolved_value = resolve_value(self.value, context)
                    method(resolved_value)
                else:
                    method()
    
    def _execute_property(self, context, tag_def):
        """Sæt en property på et element"""
        element = self._find_element(context)
        if not element:
            return
        
        resolved_value = resolve_value(self.value, context)
        
        # Prøv setter metode først (f.eks. set_title, set_text)
        setter_name = f"set_{self.property_name}"
        if hasattr(element, setter_name):
            getattr(element, setter_name)(resolved_value)
        elif hasattr(element, self.property_name):
            # Direkte property assignment
            setattr(element, self.property_name, resolved_value)
    
    def _find_element(self, context):
        """Find element i context baseret på navn og type"""
        registry = TagRegistry.instance()
        tag_def = registry.infer_element_type(self.element_name)
        
        if not tag_def:
            return None
        
        # Find i den rigtige store baseret på tag category
        if tag_def.category == TagCategory.GUI_CONTAINER:
            if 'windows' in context:
                return context['windows'].get(self.element_name)
        elif tag_def.category == TagCategory.GUI_WIDGET:
            # Tjek flere stores
            for store_name in ['buttons', 'entries', 'labels']:
                if store_name in context:
                    element = context[store_name].get(self.element_name)
                    if element:
                        return element
        
        return None


class WidgetTextNode(ActionNode):
    """
    Generisk node for <widget_text="value"> actions.
    Finder automatisk om det er button, label, etc. ved runtime.
    """
    
    def execute(self, context):
        from libs.var import resolve_as_string
        
        widget_name = self.attributes.get('widget_name')
        raw_value = self.attributes.get('value', '')
        
        # Resolve value som string (så tal vises som tekst)
        text_value = resolve_as_string(raw_value, context)
        
        # Søg efter widget i alle stores
        widget = None
        widget_type = None
        
        # Tjek buttons
        if 'buttons' in context:
            btn = context['buttons'].get(widget_name)
            if btn:
                widget = btn
                widget_type = 'button'
        
        # Tjek labels
        if not widget and 'labels' in context:
            lbl = context['labels'].get(widget_name)
            if lbl:
                widget = lbl
                widget_type = 'label'
        
        # Tjek entries
        if not widget and 'entries' in context:
            ent = context['entries'].get(widget_name)
            if ent:
                widget = ent
                widget_type = 'entry'
        
        # Sæt tekst hvis widget fundet
        if widget and hasattr(widget, 'set_text'):
            widget.set_text(text_value)
        
        self._ready = True
        self._executed = True


class PyTMLCompiler:
    """Compiler til PyTML syntax"""
    
    def __init__(self):
        self.variables = VariableStore()
        self.root = BlockNode('root')
        self.named_objects = {}  # Gem alle navngivne objekter (if, loop, block)
        self._node_types = self._register_node_types()
        self._line_parsers = self._register_line_parsers()
    
    def _register_node_types(self):
        """Registrer alle node typer fra libs"""
        node_types = {
            # Base nodes
            'block': BlockNode,
            'if': IfNode,
            'loop': LoopNode,
            # Fra libs
            'var': VarNode,
            'output': OutputNode,
            'noterminate': NoTerminateNode,
            'noquit': NoTerminateNode,
        }
        return node_types
    
    def _register_line_parsers(self):
        """Registrer alle linje parsere - libs kan tilføje deres egne"""
        parsers = []
        
        # Importer parsere fra libs
        from libs.var import get_line_parsers as var_parsers
        from libs.output import get_line_parsers as output_parsers
        from libs.console_utils import get_line_parsers as console_parsers
        from libs.window import get_line_parsers as window_parsers
        from libs.button import get_line_parsers as button_parsers
        from libs.label import get_line_parsers as label_parsers
        from libs.entry import get_line_parsers as entry_parsers
        from libs.input import get_line_parsers as input_parsers
        from libs.random import get_line_parsers as random_parsers
        
        parsers.extend(var_parsers())
        parsers.extend(output_parsers())
        parsers.extend(console_parsers())
        parsers.extend(window_parsers())
        parsers.extend(button_parsers())
        parsers.extend(label_parsers())
        parsers.extend(entry_parsers())
        parsers.extend(input_parsers())
        parsers.extend(random_parsers())
        
        # Tilføj base parsere - VIGTIGT: object definitions først!
        parsers.extend(self._get_base_parsers())
        
        return parsers
    
    def _get_base_parsers(self):
        """Base parsere for grundlæggende syntax"""
        return [
            # Object definitions (navngivne konstruktioner) - SKAL VÆRE FØRST
            (r'<if_name="(\w+)">', self._parse_if_definition),
            (r'<loop_name="(\w+)">', self._parse_loop_definition),
            (r'<block_name="(\w+)">', self._parse_block_definition),
            
            # Named object usage (brug navngivet objekt)
            (r'<(\w+)\s+condition="([^"]*)">', self._parse_named_if_open),
            (r'</(\w+)>', self._parse_named_close),
            
            # Forever loop (event loop)
            (r'<forever\s+interval="(\d+)">', self._parse_forever_interval),
            (r'<forever>', self._parse_forever),
            (r'</forever>', self._parse_close_forever),
            
            # Event-based if: <if event="<btn_click>">
            (r'<if\s+event="([^"]*)">', self._parse_if_event),
            
            # === GENERISK WIDGET ACTION PARSER ===
            # <name_text="value"> - router til korrekt widget type runtime
            (r'<(\w+)_text="([^"]*)">', self._parse_widget_text),
            
            # Legacy syntax (bagudkompatibel)
            (r'<loop\s+count="(\d+)"(?:\s+var="(\w+)")?>', self._parse_loop),
            (r'</loop>', self._parse_close_loop),
            (r'<block>', self._parse_block),
            (r'</block>', self._parse_close_block),
            # If med variabel condition (uden quotes): <if condition=<var_value>=='yes'>
            # Denne regex matcher alt indtil den sidste > på linjen
            (r'<if\s+condition=(.+)>$', self._parse_if_expr),
            # If med quoted condition: <if condition="...">
            (r'<if\s+condition="([^"]*)">', self._parse_if),
            (r'</if>', self._parse_close_if),
        ]
    
    def _parse_widget_text(self, match, current, context):
        """
        Generisk parser for <name_text="value">
        Router til korrekt widget type (button, label, etc.) ved execution
        """
        widget_name = match.group(1)
        text_value = match.group(2)
        
        # Opret en generisk WidgetTextNode der finder widget ved runtime
        node = WidgetTextNode('widget_text', {
            'widget_name': widget_name,
            'value': text_value
        })
        current.add_child(node)
        return None
    
    # === Object Definition Parsers ===
    
    def _parse_if_definition(self, match, current, context):
        """Parse <if_name="navn"> - definerer et if-objekt"""
        name = match.group(1)
        self.named_objects[name] = {
            'type': 'if',
            'node_class': IfNode,
            'defined': True
        }
        return None  # Forbliv på samme level
    
    def _parse_loop_definition(self, match, current, context):
        """Parse <loop_name="navn"> - definerer et loop-objekt"""
        name = match.group(1)
        self.named_objects[name] = {
            'type': 'loop',
            'node_class': LoopNode,
            'defined': True
        }
        return None
    
    def _parse_block_definition(self, match, current, context):
        """Parse <block_name="navn"> - definerer et block-objekt"""
        name = match.group(1)
        self.named_objects[name] = {
            'type': 'block',
            'node_class': BlockNode,
            'defined': True
        }
        return None
    
    # === Named Object Usage Parsers ===
    
    def _parse_named_if_open(self, match, current, context):
        """Parse <navngivet_if condition="..."> - åbn navngivet if"""
        name = match.group(1)
        condition = match.group(2)
        
        # Tjek om dette navn er defineret som et objekt
        if name in self.named_objects:
            obj_info = self.named_objects[name]
            if obj_info['type'] == 'if':
                node = IfNode(name, {'condition': condition, 'name': name})
                current.add_child(node)
                self.named_objects[name]['node'] = node
                return node
        
        return None  # Ikke genkendt
    
    def _parse_named_close(self, match, current, context):
        """Parse </navngivet_objekt> - luk navngivet objekt"""
        name = match.group(1)
        
        # Tjek standard close tags først
        if name in ['if', 'loop', 'block']:
            if current.parent:
                return current.parent
            return current
        
        # Tjek om dette er et navngivet objekt
        if name in self.named_objects:
            if current.parent:
                return current.parent
        
        return current
    
    # === Legacy Parsers (bagudkompatibel) ===
    
    def _parse_loop(self, match, current, context):
        count = match.group(1)
        var_name = match.group(2) or 'i'
        node = LoopNode('loop', {'count': count, 'var': var_name})
        current.add_child(node)
        return node
    
    def _parse_close_loop(self, match, current, context):
        if current.parent:
            return current.parent
        return current
    
    def _parse_block(self, match, current, context):
        node = BlockNode('block')
        current.add_child(node)
        return node
    
    def _parse_close_block(self, match, current, context):
        if current.parent:
            return current.parent
        return current
    
    def _parse_if(self, match, current, context):
        condition = match.group(1)
        node = IfNode('if', {'condition': condition})
        current.add_child(node)
        return node
    
    def _parse_if_expr(self, match, current, context):
        """Parse <if condition=expression> uden quotes"""
        condition = match.group(1).strip()
        node = IfNode('if', {'condition': condition})
        current.add_child(node)
        return node
    
    def _parse_if_event(self, match, current, context):
        """Parse <if event="<btn_click>">"""
        event = match.group(1)
        node = EventIfNode('if_event', {'event': event})
        current.add_child(node)
        return node
    
    def _parse_forever(self, match, current, context):
        """Parse <forever>"""
        node = ForeverNode('forever', {'interval': 100})
        current.add_child(node)
        return node
    
    def _parse_forever_interval(self, match, current, context):
        """Parse <forever interval="200">"""
        interval = int(match.group(1))
        node = ForeverNode('forever', {'interval': interval})
        current.add_child(node)
        return node
    
    def _parse_close_forever(self, match, current, context):
        """Parse </forever>"""
        if current.parent:
            return current.parent
        return current
    
    def _parse_close_if(self, match, current, context):
        if current.parent:
            return current.parent
        return current
    
    def _parse_dynamic_action(self, line, current, context):
        """
        Fallback parser der bruger SemanticAnalyzer til at forstå ukendte patterns.
        
        Håndterer dynamisk:
        - <element_action> patterns (f.eks. <btn1_show>)
        - <element_property="value"> patterns (f.eks. <lbl1_text="Hello">)
        """
        analyzer = SemanticAnalyzer()
        analysis = analyzer.analyze_line(line, context)
        
        if analysis['element_name'] and (analysis['action'] or analysis['property']):
            node = DynamicActionNode('dynamic_action', {
                'element_name': analysis['element_name'],
                'action': analysis['action'],
                'property': analysis['property'],
                'value': analysis['value'],
            })
            current.add_child(node)
            return True
        
        return False
    
    def parse(self, code):
        """Parse PyTML kode og byg action tree"""
        self.root = BlockNode('root')
        self.named_objects = {}  # Reset navngivne objekter
        current = self.root
        
        lines = code.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Prøv hver parser
            parsed = False
            for pattern, handler in self._line_parsers:
                match = re.match(pattern, line)
                if match:
                    result = handler(match, current, {
                        'variables': self.variables,
                        'named_objects': self.named_objects
                    })
                    if result is not None:
                        current = result
                    parsed = True
                    break
            
            # Hvis ingen parser matchede, prøv dynamisk parsing via registry
            if not parsed:
                parsed = self._parse_dynamic_action(line, current, {
                    'variables': self.variables,
                    'named_objects': self.named_objects
                })
            
            # Stadig ikke parsed - ignorer eller log
            if not parsed:
                pass  # Kunne logge ukendte linjer
        
        return self.root
    
    def execute(self, gui_mode=False):
        """Udfør det parsede PyTML program
        
        Args:
            gui_mode: Hvis True, start IKKE mainloop (editor kører sin egen)
        """
        from libs.window import WindowStore
        
        context = {
            'variables': self.variables,
            'named_objects': self.named_objects,
            'windows': WindowStore(),
        }
        
        self.root.execute(context)
        
        # Hvis der er forever loops og vinduer, start mainloop
        # MEN kun hvis vi IKKE er i gui_mode (editor har sin egen mainloop)
        if not gui_mode and context.get('forever_loops') and context.get('windows'):
            windows = context['windows']
            if hasattr(windows, '_tk_root') and windows._tk_root:
                try:
                    windows._tk_root.mainloop()
                except Exception:
                    pass
        
        return context


def compile_pytml(code, gui_mode=False):
    """Kompiler og kør PyTML kode
    
    Args:
        code: PyTML kildekode
        gui_mode: Hvis True, spring wait_for_close og mainloop over (undgå at blokere GUI)
    """
    # Reset console utils før hver kørsel
    reset_console()
    
    compiler = PyTMLCompiler()
    compiler.parse(code)
    result = compiler.execute(gui_mode=gui_mode)
    
    # Vent på bruger input hvis noterminate er aktiv (kun i terminal mode)
    if not gui_mode:
        wait_for_close()
    
    return result


# Eksporter nødvendige klasser
__all__ = [
    'ActionNode',
    'BlockNode', 
    'IfNode',
    'LoopNode',
    'PyTMLCompiler',
    'compile_pytml'
]
