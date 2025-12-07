"""
PyTML Random Module
Provides random number generation with min/max range
Usage: <random name="rnd" min="0" max="10">
       <var name="a" value="<rnd_random>">
"""

import random as py_random
from libs.core import ActionNode, PropertyDescriptor, resolve_attributes


class RandomGenerator:
    """A random number generator with configurable min/max range"""
    
    def __init__(self, name, min_val=0, max_val=100, **kwargs):
        self.name = name
        self.min_val = int(min_val)
        self.max_val = int(max_val)
        self._seed = kwargs.get('seed', None)
        
        if self._seed is not None:
            py_random.seed(int(self._seed))
    
    def random(self):
        """Get a random integer between min and max (inclusive)"""
        return py_random.randint(self.min_val, self.max_val)
    
    def random_float(self):
        """Get a random float between min and max"""
        return py_random.uniform(self.min_val, self.max_val)
    
    def choice(self, items):
        """Pick a random item from a list"""
        if isinstance(items, str):
            items = [x.strip() for x in items.split(',')]
        return py_random.choice(items)
    
    def shuffle(self, items):
        """Shuffle a list and return it"""
        if isinstance(items, str):
            items = [x.strip() for x in items.split(',')]
        items = list(items)
        py_random.shuffle(items)
        return items


class RandomNode(ActionNode):
    """Node for creating a random generator"""
    tag_name = 'random'
    _properties = {
        'name': PropertyDescriptor('name', str, required=True),
        'min': PropertyDescriptor('min', int, default=0),
        'max': PropertyDescriptor('max', int, default=100),
        'seed': PropertyDescriptor('seed', int, default=None),
    }
    
    def execute(self, context):
        resolved = resolve_attributes(self.attributes, context)
        name = resolved.get('name')
        
        if name:
            min_val = resolved.get('min', 0)
            max_val = resolved.get('max', 100)
            seed = resolved.get('seed')
            
            # Create the random generator
            rng = RandomGenerator(name, min_val, max_val, seed=seed)
            
            # Store in context
            if 'randoms' not in context:
                context['randoms'] = {}
            context['randoms'][name] = rng
            
            # Register dynamic variable accessors
            # These allow <var name="x" value="<rndname_random>"> syntax
            context[f'{name}_random'] = lambda rng=rng: rng.random()
            context[f'{name}_float'] = lambda rng=rng: rng.random_float()
            
        self._ready = True


def get_line_parsers():
    """Return line parsers for random tags"""
    import re
    
    def parse_random(match, current, context):
        attrs = {m.group(1): m.group(2) for m in re.finditer(r'(\w+)="([^"]*)"', match.group(1))}
        current.add_child(RandomNode('random', attrs))
        return None
    
    return [(r'<random\s+(.+?)\s*/?>$', parse_random)]


def get_gui_info():
    """Return GUI metadata for the PyTML GUI Editor"""
    return {
        'type': 'console',
        'framework': 'python',
        'icon': '🎲',
        'display_name': 'Random Generator',
        'embed_method': 'none',
        'default_size': (0, 0),
        'is_graphical': False,
        'properties': [
            {'name': 'name', 'type': 'str', 'required': True},
            {'name': 'min', 'type': 'int', 'default': 0},
            {'name': 'max', 'type': 'int', 'default': 100},
            {'name': 'seed', 'type': 'int', 'default': None},
        ]
    }
