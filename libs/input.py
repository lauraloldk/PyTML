"""
PyTML Input Module
Håndterer bruger input med HTML-lignende tags

Syntax:
    <input>                         -> Prompt for input, returner værdi
    <input prompt="Enter name:">    -> Prompt med besked
    <var name="x" value=<input>>    -> Gem input i variabel
"""


class ActionNode:
    """Base klasse for actions"""
    
    def __init__(self, tag_name, attributes=None):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.children = []
        self.parent = None
        self._ready = False
        self._executed = False
    
    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        return child
    
    def children_ready(self):
        return all(child.is_ready() for child in self.children)
    
    def is_ready(self):
        return self._ready and self.children_ready()
    
    def execute(self, context):
        self._ready = True
        self._executed = True


class InputNode(ActionNode):
    """
    Input node: <input> eller <input prompt="...">
    Prompter brugeren for input og returnerer værdien.
    """
    
    def execute(self, context):
        prompt = self.attributes.get('prompt', '')
        
        # Hent input fra brugeren
        if prompt:
            value = input(prompt + " ")
        else:
            value = input()
        
        # Gem resultatet så det kan bruges
        self.result = value
        
        self._ready = True
        self._executed = True
        return value


def get_line_parsers():
    """Returner linje parsere for input modulet"""
    return [
        # <input prompt="...">
        (r'<input\s+prompt="([^"]*)">', _parse_input_with_prompt),
        # <input>
        (r'<input>', _parse_input),
    ]


def _parse_input_with_prompt(match, current, context):
    """Parse <input prompt="...">"""
    prompt = match.group(1)
    node = InputNode('input', {'prompt': prompt})
    current.add_child(node)
    return None


def _parse_input(match, current, context):
    """Parse <input>"""
    node = InputNode('input', {})
    current.add_child(node)
    return None


# Eksporter
__all__ = ['InputNode', 'get_line_parsers']
