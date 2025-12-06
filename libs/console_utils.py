"""
PyTML Console Utils Module
Håndterer konsol-relaterede funktioner som noterminate/noquit
"""

# Global flag for om programmet skal vente på bruger input før lukning
_no_terminate = False


def set_no_terminate(value=True):
    """Sæt no-terminate flag - konsollen lukker ikke automatisk"""
    global _no_terminate
    _no_terminate = value


def get_no_terminate():
    """Hent no-terminate flag status"""
    global _no_terminate
    return _no_terminate


def wait_for_close():
    """Vent på at brugeren trykker Enter før programmet lukker"""
    global _no_terminate
    if _no_terminate:
        print("\n" + "=" * 40)
        print("Tryk Enter for at lukke...")
        input()


def reset():
    """Reset alle console-utils indstillinger"""
    global _no_terminate
    _no_terminate = False


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


class NoTerminateNode(ActionNode):
    """NoTerminate node: <noterminate> eller <noquit> - holder konsollen åben"""
    
    def __init__(self, tag_name='noterminate', attributes=None):
        super().__init__(tag_name, attributes)
    
    def execute(self, context=None):
        """Aktiver no-terminate mode"""
        set_no_terminate(True)
        
        # Udfør alle children
        for child in self.children:
            child.execute(context)
        
        self._ready = True
        self._executed = True
        return self
    
    def __repr__(self):
        return "<noterminate>"


def get_line_parsers():
    """Returner linje parsere for console_utils modulet"""
    return [
        # <noterminate>
        (r'<noterminate>', _parse_noterminate),
        # <noquit>
        (r'<noquit>', _parse_noterminate),
    ]


def _parse_noterminate(match, current, context):
    """Parse <noterminate> eller <noquit>"""
    node = NoTerminateNode('noterminate', {})
    current.add_child(node)
    return None


# Eksporter
__all__ = [
    'set_no_terminate',
    'get_no_terminate', 
    'wait_for_close',
    'reset',
    'NoTerminateNode',
    'get_line_parsers'
]
