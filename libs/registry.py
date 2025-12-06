"""
PyTML Registry Module
=====================
Central registrering af alle tags, properties, metoder og deres relationer.
Dette gør det muligt for compileren at forstå hvordan elementer arbejder sammen
UDEN hardkodning i hver lib.

Funktioner:
- Tag registrering med metadata
- Property og metode discovery
- Automatisk relation inference
- Semantisk analyse support
- Pattern matching for parsers
"""

import re
from typing import Any, Dict, List, Optional, Callable, Type, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto


class TagCategory(Enum):
    """Kategorier af tags"""
    VARIABLE = auto()      # var, variable
    CONTROL = auto()       # if, loop, forever, block
    GUI_CONTAINER = auto() # window, gui, frame
    GUI_WIDGET = auto()    # button, entry, label
    OUTPUT = auto()        # output, print
    INPUT = auto()         # input
    ACTION = auto()        # show, hide, click
    META = auto()          # noterminate, comment


class RelationType(Enum):
    """Typer af relationer mellem tags"""
    PARENT_OF = auto()     # window -> button (window kan være parent til button)
    CHILD_OF = auto()      # button -> window (button kan være child af window)
    REFERENCES = auto()    # output -> var (output kan referere til var)
    TRIGGERS = auto()      # button_click -> action
    MODIFIES = auto()      # action -> property


@dataclass
class TagDefinition:
    """
    Definition af et PyTML tag.
    
    Indeholder al metadata om tagget:
    - Navn og aliaser
    - Properties og metoder
    - Relationer til andre tags
    - Parser patterns
    """
    name: str
    category: TagCategory
    node_class: Type = None
    
    # Aliaser (f.eks. 'variable' er alias for 'var')
    aliases: List[str] = field(default_factory=list)
    
    # Properties dette tag understøtter
    properties: Dict[str, 'PropertyDefinition'] = field(default_factory=dict)
    
    # Metoder/actions dette tag understøtter
    methods: Dict[str, 'MethodDefinition'] = field(default_factory=dict)
    
    # Events dette tag kan trigge
    events: List[str] = field(default_factory=list)
    
    # Hvilke tags kan være parent
    valid_parents: Set[str] = field(default_factory=set)
    
    # Hvilke tags kan være children
    valid_children: Set[str] = field(default_factory=set)
    
    # Parser patterns (regex -> handler name)
    patterns: List[Tuple[str, str]] = field(default_factory=list)
    
    # Er dette et self-closing tag? (<tag> vs <tag></tag>)
    self_closing: bool = True
    
    # Beskrivelse
    description: str = ""
    
    def matches(self, tag_name: str) -> bool:
        """Tjek om et tag navn matcher denne definition"""
        return tag_name == self.name or tag_name in self.aliases


@dataclass
class PropertyDefinition:
    """Definition af en property"""
    name: str
    prop_type: Type
    default: Any = None
    required: bool = False
    interpolate: bool = True
    description: str = ""
    
    # Getter pattern: <name_property> eller <name_property="value">
    getter_pattern: str = None
    setter_pattern: str = None


@dataclass
class MethodDefinition:
    """Definition af en metode/action"""
    name: str
    params: List[str] = field(default_factory=list)
    returns: Type = None
    description: str = ""
    
    # Pattern: <name_method> eller <name_method="value">
    pattern: str = None


# =============================================================================
# GLOBAL REGISTRY
# =============================================================================

class TagRegistry:
    """
    Central registry for alle PyTML tags.
    
    Singleton pattern - der er kun én registry.
    
    Brug:
        registry = TagRegistry.instance()
        registry.register(tag_def)
        tag = registry.get('window')
    """
    
    _instance = None
    
    @classmethod
    def instance(cls) -> 'TagRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset registry (primært til tests)"""
        cls._instance = None
    
    def __init__(self):
        self.tags: Dict[str, TagDefinition] = {}
        self.aliases: Dict[str, str] = {}  # alias -> canonical name
        self._patterns_cache: List[Tuple[re.Pattern, str, TagDefinition]] = None
    
    def register(self, tag_def: TagDefinition):
        """Registrer et tag"""
        self.tags[tag_def.name] = tag_def
        
        # Registrer aliaser
        for alias in tag_def.aliases:
            self.aliases[alias] = tag_def.name
        
        # Invalidér pattern cache
        self._patterns_cache = None
    
    def get(self, name: str) -> Optional[TagDefinition]:
        """Hent et tag ved navn eller alias"""
        # Tjek direkte navn
        if name in self.tags:
            return self.tags[name]
        
        # Tjek aliaser
        if name in self.aliases:
            return self.tags[self.aliases[name]]
        
        return None
    
    def get_canonical_name(self, name: str) -> str:
        """Få det kanoniske navn for et tag"""
        if name in self.aliases:
            return self.aliases[name]
        return name
    
    def find_by_category(self, category: TagCategory) -> List[TagDefinition]:
        """Find alle tags i en kategori"""
        return [tag for tag in self.tags.values() if tag.category == category]
    
    def find_valid_children(self, parent_name: str) -> List[TagDefinition]:
        """Find alle tags der kan være children af et parent tag"""
        result = []
        for tag in self.tags.values():
            if not tag.valid_parents or parent_name in tag.valid_parents:
                result.append(tag)
        return result
    
    def can_be_child_of(self, child_name: str, parent_name: str) -> bool:
        """Tjek om et tag kan være child af et andet"""
        child_def = self.get(child_name)
        if not child_def:
            return True  # Ukendte tags tillades
        
        if not child_def.valid_parents:
            return True  # Ingen restriktioner
        
        return parent_name in child_def.valid_parents
    
    def get_all_patterns(self) -> List[Tuple[re.Pattern, str, TagDefinition]]:
        """
        Hent alle parser patterns fra alle registrerede tags.
        Cached for performance.
        """
        if self._patterns_cache is not None:
            return self._patterns_cache
        
        patterns = []
        for tag_def in self.tags.values():
            for pattern_str, handler_name in tag_def.patterns:
                try:
                    compiled = re.compile(pattern_str)
                    patterns.append((compiled, handler_name, tag_def))
                except re.error:
                    pass
        
        self._patterns_cache = patterns
        return patterns
    
    def infer_element_type(self, name: str) -> Optional[TagDefinition]:
        """
        Inferer element type fra et navn.
        
        F.eks. 'btn1' -> kunne være 'button' baseret på præfiks.
        'wnd1' -> kunne være 'window'.
        """
        # Tjek direkte match først
        tag_def = self.get(name)
        if tag_def:
            return tag_def
        
        # Prøv at matche præfiks
        prefixes = {
            'wnd': 'window',
            'win': 'window',
            'btn': 'button',
            'ent': 'entry',
            'txt': 'entry',
            'lbl': 'label',
            'frm': 'frame',
        }
        
        for prefix, tag_name in prefixes.items():
            if name.startswith(prefix):
                return self.get(tag_name)
        
        return None
    
    def get_property_for_element(self, element_name: str, property_name: str) -> Optional[PropertyDefinition]:
        """
        Hent property definition for et navngivet element.
        
        F.eks. get_property_for_element('btn1', 'text') 
        -> finder button tag og returnerer 'text' property
        """
        tag_def = self.infer_element_type(element_name)
        if tag_def:
            return tag_def.properties.get(property_name)
        return None
    
    def get_method_for_element(self, element_name: str, method_name: str) -> Optional[MethodDefinition]:
        """
        Hent method definition for et navngivet element.
        
        F.eks. get_method_for_element('wnd1', 'show')
        -> finder window tag og returnerer 'show' method
        """
        tag_def = self.infer_element_type(element_name)
        if tag_def:
            return tag_def.methods.get(method_name)
        return None
    
    def __repr__(self):
        return f"TagRegistry({len(self.tags)} tags)"


# =============================================================================
# SEMANTIC ANALYZER
# =============================================================================

class SemanticAnalyzer:
    """
    Analyserer PyTML kode semantisk.
    
    Funktioner:
    - Validerer tag brug
    - Resolver references mellem elementer
    - Inferrer typer og relationer
    - Giver fejlbeskeder
    """
    
    def __init__(self, registry: TagRegistry = None):
        self.registry = registry or TagRegistry.instance()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.symbols: Dict[str, Any] = {}  # Named elements
    
    def analyze_line(self, line: str, context: Dict = None) -> Dict:
        """
        Analyser en enkelt linje.
        
        Returns:
            Dict med:
            - 'tag': Tag navn (hvis fundet)
            - 'element_name': Element navn (f.eks. 'btn1')
            - 'action': Action/method (f.eks. 'show', 'click')
            - 'property': Property (f.eks. 'text', 'value')
            - 'value': Værdi (hvis sat)
            - 'references': Liste af refererede elementer
        """
        result = {
            'tag': None,
            'element_name': None,
            'action': None,
            'property': None,
            'value': None,
            'references': [],
        }
        
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            return result
        
        # Pattern 1: <element_action> eller <element_property="value">
        # Tjek denne FØRST da den er mere specifik
        action_match = re.match(r'<(\w+)_(\w+)(?:\s*=\s*"?([^">]*)"?)?>', line)
        if action_match:
            element_name = action_match.group(1)
            action_or_prop = action_match.group(2)
            value = action_match.group(3)
            
            result['element_name'] = element_name
            
            # Tjek om det er en action eller property
            tag_def = self.registry.infer_element_type(element_name)
            if tag_def:
                if action_or_prop in tag_def.methods:
                    result['action'] = action_or_prop
                elif action_or_prop in tag_def.properties:
                    result['property'] = action_or_prop
                elif action_or_prop in tag_def.events:
                    result['action'] = action_or_prop  # Events behandles som actions
                else:
                    # Ukendt - gæt baseret på om der er en værdi
                    if value is not None:
                        result['property'] = action_or_prop
                    else:
                        result['action'] = action_or_prop
            else:
                # Ukendt element type - prøv stadig at gætte
                if value is not None:
                    result['property'] = action_or_prop
                else:
                    result['action'] = action_or_prop
            
            result['value'] = value
            
            # Find references i værdi
            if value:
                for ref in re.findall(r'<(\w+)_value>', value):
                    result['references'].append(ref)
            
            return result
        
        # Pattern 2: <tag_name attr="value">
        tag_match = re.match(r'<(\w+)(?:\s+(.*))?>', line)
        if tag_match:
            tag_name = tag_match.group(1)
            attrs_str = tag_match.group(2) or ''
            
            result['tag'] = tag_name
            
            # Parse attributes
            for attr_match in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2)
                
                if attr_name == 'name':
                    result['element_name'] = attr_value
                    self.symbols[attr_value] = {'tag': tag_name, 'line': line}
                
                # Find references i værdier
                for ref in re.findall(r'<(\w+)_value>', attr_value):
                    result['references'].append(ref)
            
            return result
        
        return result
    
    def validate(self, ast_root) -> bool:
        """
        Valider et helt AST.
        
        Returns:
            True hvis valid, False hvis der er fejl
        """
        self.errors = []
        self.warnings = []
        self._validate_node(ast_root)
        return len(self.errors) == 0
    
    def _validate_node(self, node, parent=None):
        """Rekursiv validering af en node"""
        # Tjek parent-child relation
        if parent and hasattr(node, 'tag_name'):
            if not self.registry.can_be_child_of(node.tag_name, parent.tag_name):
                self.warnings.append(
                    f"'{node.tag_name}' er normalt ikke et child af '{parent.tag_name}'"
                )
        
        # Valider children
        if hasattr(node, 'children'):
            for child in node.children:
                self._validate_node(child, node)
    
    def get_completions(self, element_name: str) -> List[str]:
        """
        Få mulige completions for et element.
        
        F.eks. for 'btn1' returnerer ['click', 'text', 'enabled', ...]
        """
        completions = []
        tag_def = self.registry.infer_element_type(element_name)
        
        if tag_def:
            # Tilføj methods
            for method_name in tag_def.methods:
                completions.append(f"{element_name}_{method_name}")
            
            # Tilføj properties
            for prop_name in tag_def.properties:
                completions.append(f"{element_name}_{prop_name}")
            
            # Tilføj events
            for event in tag_def.events:
                completions.append(f"{element_name}_{event}")
        
        return completions


# =============================================================================
# REGISTRATION HELPERS
# =============================================================================

def register_builtin_tags():
    """Registrer alle indbyggede PyTML tags"""
    registry = TagRegistry.instance()
    
    # === VARIABLES ===
    registry.register(TagDefinition(
        name='var',
        category=TagCategory.VARIABLE,
        aliases=['variable'],
        properties={
            'name': PropertyDefinition('name', str, required=True),
            'value': PropertyDefinition('value', str, default=''),
        },
        patterns=[
            (r'<var\s+name="(\w+)"\s+value="([^"]*)">', 'parse_var_with_value'),
            (r'<var\s+name="(\w+)">', 'parse_var_declaration'),
            (r'<(\w+)_value="([^"]*)">', 'parse_var_set'),
        ],
        description="Variabel definition og manipulation"
    ))
    
    # === CONTROL FLOW ===
    registry.register(TagDefinition(
        name='if',
        category=TagCategory.CONTROL,
        self_closing=False,
        properties={
            'condition': PropertyDefinition('condition', str, required=True),
            'event': PropertyDefinition('event', str),
        },
        patterns=[
            (r'<if\s+condition="([^"]*)">', 'parse_if'),
            (r'<if\s+event="([^"]*)">', 'parse_if_event'),
            (r'</if>', 'parse_close_if'),
        ],
        description="Betinget udførelse"
    ))
    
    registry.register(TagDefinition(
        name='loop',
        category=TagCategory.CONTROL,
        self_closing=False,
        properties={
            'count': PropertyDefinition('count', int, required=True),
            'var': PropertyDefinition('var', str, default='i'),
        },
        patterns=[
            (r'<loop\s+count="(\d+)"(?:\s+var="(\w+)")?>', 'parse_loop'),
            (r'</loop>', 'parse_close_loop'),
        ],
        description="Gentag kode et antal gange"
    ))
    
    registry.register(TagDefinition(
        name='forever',
        category=TagCategory.CONTROL,
        self_closing=False,
        properties={
            'interval': PropertyDefinition('interval', int, default=100),
        },
        patterns=[
            (r'<forever\s+interval="(\d+)">', 'parse_forever_interval'),
            (r'<forever>', 'parse_forever'),
            (r'</forever>', 'parse_close_forever'),
        ],
        description="Uendelig event loop"
    ))
    
    # === GUI CONTAINERS ===
    registry.register(TagDefinition(
        name='window',
        category=TagCategory.GUI_CONTAINER,
        aliases=['wnd'],
        properties={
            'name': PropertyDefinition('name', str, required=True),
            'title': PropertyDefinition('title', str, default='PyTML Window'),
            'size': PropertyDefinition('size', list, default=[300, 300]),
        },
        methods={
            'show': MethodDefinition('show', description="Vis vinduet"),
            'hide': MethodDefinition('hide', description="Skjul vinduet"),
            'close': MethodDefinition('close', description="Luk vinduet"),
            'title': MethodDefinition('title', params=['value'], description="Sæt titel"),
            'size': MethodDefinition('size', params=['width', 'height'], description="Sæt størrelse"),
        },
        valid_children={'button', 'entry', 'label', 'frame'},
        patterns=[
            (r'<window\s+(.+)>', 'parse_window'),
            (r'<(\w+)_show>', 'parse_window_show'),
            (r'<(\w+)_hide>', 'parse_window_hide'),
            (r'<(\w+)_title\s*=\s*"([^"]*)">', 'parse_window_title'),
        ],
        description="GUI vindue container"
    ))
    
    # === GUI WIDGETS ===
    registry.register(TagDefinition(
        name='button',
        category=TagCategory.GUI_WIDGET,
        aliases=['btn'],
        properties={
            'name': PropertyDefinition('name', str, required=True),
            'text': PropertyDefinition('text', str, default='Button'),
            'parent': PropertyDefinition('parent', str),
            'x': PropertyDefinition('x', int, default=0),
            'y': PropertyDefinition('y', int, default=0),
            'width': PropertyDefinition('width', int, default=100),
            'height': PropertyDefinition('height', int, default=30),
            'enabled': PropertyDefinition('enabled', bool, default=True),
        },
        methods={
            'text': MethodDefinition('text', params=['value']),
            'enabled': MethodDefinition('enabled', params=['value']),
        },
        events=['click'],
        valid_parents={'window', 'frame', 'gui'},
        patterns=[
            (r'<button\s+(.+)>', 'parse_button'),
            (r'<(\w+)_text="([^"]*)">', 'parse_button_text'),
            (r'<(\w+)_click>', 'parse_button_click'),
        ],
        description="Klikbar knap"
    ))
    
    registry.register(TagDefinition(
        name='entry',
        category=TagCategory.GUI_WIDGET,
        aliases=['txt', 'textbox', 'input_field'],
        properties={
            'name': PropertyDefinition('name', str, required=True),
            'parent': PropertyDefinition('parent', str),
            'placeholder': PropertyDefinition('placeholder', str, default=''),
            'x': PropertyDefinition('x', int, default=0),
            'y': PropertyDefinition('y', int, default=0),
            'width': PropertyDefinition('width', int, default=150),
            'height': PropertyDefinition('height', int, default=25),
            'readonly': PropertyDefinition('readonly', bool, default=False),
        },
        methods={
            'value': MethodDefinition('value', params=['value']),
            'placeholder': MethodDefinition('placeholder', params=['value']),
            'readonly': MethodDefinition('readonly', params=['value']),
        },
        valid_parents={'window', 'frame', 'gui'},
        patterns=[
            (r'<entry\s+(.+)>', 'parse_entry'),
            (r'<(\w+)_value="([^"]*)">', 'parse_entry_value'),
        ],
        description="Tekstfelt til brugerinput"
    ))
    
    registry.register(TagDefinition(
        name='label',
        category=TagCategory.GUI_WIDGET,
        aliases=['lbl'],
        properties={
            'name': PropertyDefinition('name', str, required=True),
            'text': PropertyDefinition('text', str, default=''),
            'parent': PropertyDefinition('parent', str),
            'x': PropertyDefinition('x', int, default=0),
            'y': PropertyDefinition('y', int, default=0),
        },
        methods={
            'text': MethodDefinition('text', params=['value']),
        },
        valid_parents={'window', 'frame', 'gui'},
        patterns=[
            (r'<label\s+(.+)>', 'parse_label'),
            (r'<(\w+)_text="([^"]*)">', 'parse_label_text'),
        ],
        description="Tekst label"
    ))
    
    # === OUTPUT/INPUT ===
    registry.register(TagDefinition(
        name='output',
        category=TagCategory.OUTPUT,
        aliases=['print'],
        properties={
            'value': PropertyDefinition('value', str),
        },
        patterns=[
            (r'<output\s+"([^"]*)">', 'parse_output_literal'),
            (r'<output\s+<(\w+)_value>>', 'parse_output_var'),
        ],
        description="Output til konsol"
    ))
    
    registry.register(TagDefinition(
        name='input',
        category=TagCategory.INPUT,
        properties={
            'prompt': PropertyDefinition('prompt', str, default=''),
        },
        patterns=[
            (r'<input\s+prompt="([^"]*)">', 'parse_input_prompt'),
            (r'<input\s+"([^"]*)">', 'parse_input_inline'),
            (r'<input>', 'parse_input'),
        ],
        description="Brugerinput fra konsol"
    ))
    
    # === META ===
    registry.register(TagDefinition(
        name='noterminate',
        category=TagCategory.META,
        patterns=[
            (r'<noterminate>', 'parse_noterminate'),
        ],
        description="Forhindrer automatisk lukning"
    ))
    
    registry.register(TagDefinition(
        name='gui',
        category=TagCategory.GUI_CONTAINER,
        self_closing=False,
        valid_children={'window', 'button', 'entry', 'label', 'frame'},
        patterns=[
            (r'<gui>', 'parse_gui_open'),
            (r'</gui>', 'parse_gui_close'),
        ],
        description="GUI sektion container"
    ))


# Auto-registrer tags ved import
register_builtin_tags()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'TagCategory',
    'RelationType',
    'TagDefinition',
    'PropertyDefinition',
    'MethodDefinition',
    'TagRegistry',
    'SemanticAnalyzer',
    'register_builtin_tags',
]
