"""
PyTML Output Module
Håndterer output med HTML-lignende tags
Understøtter variabel-interpolation.
"""

from libs.var import resolve_value


class ActionNode:
    """Base klasse for actions - importeret her for at undgå circular imports"""
    
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


class OutputAction:
    """Repræsenterer en output action i PyTML"""
    
    def __init__(self, content=None):
        self.content = content
        self.children = []
        self.parent = None
        self._executed = False
    
    def add_child(self, child):
        """Tilføj et child element"""
        child.parent = self
        self.children.append(child)
        return child
    
    def is_ready(self):
        """Tjek om alle children er klar"""
        return all(child.is_ready() for child in self.children)
    
    def execute(self, variable_store=None):
        """Udfør output action - vent på alle children først"""
        # Vent på alle children er klar
        for child in self.children:
            if hasattr(child, 'execute'):
                child.execute(variable_store)
        
        # Nu udfør denne action
        if self.content is not None:
            output_value = self.content
            
            # Hvis content er en variabel reference, hent værdien
            if variable_store and isinstance(self.content, str):
                if self.content.startswith('$'):
                    var_name = self.content[1:]  # Fjern $
                    output_value = variable_store.get_value(var_name)
                elif variable_store.exists(self.content):
                    output_value = variable_store.get_value(self.content)
            
            print(output_value)
        
        self._executed = True
        return self
    
    def __repr__(self):
        return f"<output content=\"{self.content}\">"


class OutputNode(ActionNode):
    """Output node: <output <x_value>> eller <output "literal">"""
    
    def execute(self, context):
        # Først udfør alle children
        for child in self.children:
            child.execute(context)
        
        value = self.attributes.get('value')
        
        # Brug resolve_value for variabel-interpolation
        value = resolve_value(value, context)
        
        if value is not None:
            print(value)
        
        self._ready = True
        self._executed = True


def output(content, variable_store=None):
    """Simpel output funktion til brug i PyTML"""
    action = OutputAction(content)
    action.execute(variable_store)
    return action


def get_line_parsers():
    """Returner linje parsere for output modulet"""
    return [
        # <output <x_value>>
        (r'<output\s+<(\w+)_value>>', _parse_output_var),
        # <output "literal string">
        (r'<output\s+"([^"]*)">', _parse_output_literal),
    ]


def _parse_output_var(match, current, context):
    """Parse <output <x_value>>"""
    var_name = match.group(1)
    node = OutputNode('output', {'value': f'${var_name}'})
    current.add_child(node)
    return None


def _parse_output_literal(match, current, context):
    """Parse <output "literal string">"""
    value = match.group(1)
    node = OutputNode('output', {'value': value})
    current.add_child(node)
    return None


# Eksporter
__all__ = ['OutputAction', 'OutputNode', 'output', 'get_line_parsers']
