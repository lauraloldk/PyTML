"""
PyTML Layout Module
Håndterer layout-containers (VBox, HBox) med automatisk placement.

Syntax:
    <vbox name="vbox1" parent="wnd1" x="10" y="10" width="200" height="300">
    <hbox name="hbox1" parent="wnd1" x="10" y="10" width="300" height="50">

Properties:
    name     - Unikt navn (bruges som parent reference for widgets)
    parent   - Navn på parent vindue
    x, y     - Position i parent vindue
    width, height - Størrelse på container
    padding  - Indvendigt rum (pixels), default 5
    spacing  - Afstand mellem children (pixels), default 4
    align    - Justering: start/center/end, default start
    fill     - Fyld-retning for children: none/x/y/both, default none

Eksempel:
    <window name="wnd1" title="Demo" size="300","400">
    <wnd1_show>
    <vbox name="vbox1" parent="wnd1" x="10" y="10" width="280" height="380">
    <button text="Button A" name="btnA" parent="vbox1">
    <button text="Button B" name="btnB" parent="vbox1">
"""

import tkinter as tk

from libs.var import resolve_attributes
from libs.core import ActionNode


# Marker som GUI Node type
GUI_NODE_TYPE = "container"


class LayoutBox:
    """
    Base class for layout containers (VBox / HBox).

    Implements the same interface as Window so existing widget code can
    use a LayoutBox as a ``parent`` without modification.
    When a widget's parent is a LayoutBox, it uses ``pack()`` instead of
    ``place()`` for geometry management.
    """

    # Flag checked by widget create() methods
    is_layout_container = True

    # Overridden in VBox / HBox
    layout_direction = 'vertical'  # 'vertical' | 'horizontal'

    def __init__(self, name, padding=5, spacing=4, align='start', fill='none'):
        self.name = name
        self.padding = int(padding)
        self.spacing = int(spacing)
        self.align = align
        self.fill = fill
        self.parent_window = None
        self._tk_frame = None
        self._ready = False

    # ------------------------------------------------------------------ #
    # Properties consumed by widget create() methods                       #
    # ------------------------------------------------------------------ #

    @property
    def pack_side(self):
        """Pack side for child widgets."""
        return 'top' if self.layout_direction == 'vertical' else 'left'

    @property
    def pack_fill(self):
        """Pack fill for child widgets (perpendicular to layout axis)."""
        if self.fill == 'both':
            return 'both'
        if self.fill == 'x':
            return 'x'
        if self.fill == 'y':
            return 'y'
        # Default: fill perpendicular to layout direction
        return 'x' if self.layout_direction == 'vertical' else 'none'

    # ------------------------------------------------------------------ #
    # Window-compatible interface                                           #
    # ------------------------------------------------------------------ #

    def create(self, parent_window, x=0, y=0, width=200, height=200):
        """Create the tk.Frame inside *parent_window*."""
        self.parent_window = parent_window
        tk_win = parent_window.get_tk_window()
        if tk_win:
            self._tk_frame = tk.Frame(
                tk_win,
                padx=self.padding,
                pady=self.padding,
            )
            self._tk_frame.place(x=x, y=y, width=width, height=height)
        self._ready = True
        return self

    def get_tk_window(self):
        """Return the underlying tk.Frame (Window-compatible)."""
        return self._tk_frame

    def show(self):
        """Show the container (no-op if not yet placed)."""
        self._ready = True
        return self

    def hide(self):
        """Hide the container."""
        if self._tk_frame:
            self._tk_frame.place_forget()
        return self

    def close(self):
        """Destroy the container."""
        if self._tk_frame:
            self._tk_frame.destroy()
            self._tk_frame = None
        return self

    def is_ready(self):
        return self._ready

    def __repr__(self):
        tag = 'vbox' if self.layout_direction == 'vertical' else 'hbox'
        return f'<{tag} name="{self.name}">'


class VBox(LayoutBox):
    """Vertical box – stacks children top to bottom."""
    layout_direction = 'vertical'


class HBox(LayoutBox):
    """Horizontal box – places children left to right."""
    layout_direction = 'horizontal'


# ======================================================================= #
# Action nodes                                                              #
# ======================================================================= #

class _LayoutBoxNode(ActionNode):
    """Shared execution logic for VBoxNode and HBoxNode."""

    _box_class = VBox   # Override in subclasses

    is_gui_node = True
    gui_type = 'container'
    gui_category = 'layout'

    def execute(self, context):
        for child in self.children:
            child.execute(context)

        resolved = resolve_attributes(self.attributes, context)

        name = resolved.get('name')
        parent_name = resolved.get('parent')
        x = int(resolved.get('x', 0))
        y = int(resolved.get('y', 0))
        width = int(resolved.get('width', 200))
        height = int(resolved.get('height', 200))
        padding = int(resolved.get('padding', 5))
        spacing = int(resolved.get('spacing', 4))
        align = str(resolved.get('align', 'start'))
        fill = str(resolved.get('fill', 'none'))

        if not name:
            self._ready = True
            self._executed = True
            return

        box = self._box_class(
            name,
            padding=padding,
            spacing=spacing,
            align=align,
            fill=fill,
        )

        # Ensure windows store exists
        if 'windows' not in context:
            from libs.window import WindowStore
            context['windows'] = WindowStore()

        # Register in the windows store so widgets can reference it as parent
        context['windows'].windows[name] = box

        # Create the physical frame inside the parent window
        if parent_name:
            parent_window = context['windows'].get(parent_name)
            if parent_window and parent_window is not box:
                box.create(parent_window, x, y, width, height)

        self._ready = True
        self._executed = True


class VBoxNode(_LayoutBoxNode):
    """
    VBox layout container node.
    <vbox name="vbox1" parent="wnd1" x="10" y="10" width="200" height="300">
    """
    _box_class = VBox


class HBoxNode(_LayoutBoxNode):
    """
    HBox layout container node.
    <hbox name="hbox1" parent="wnd1" x="10" y="10" width="300" height="50">
    """
    _box_class = HBox


# ======================================================================= #
# Line parsers                                                              #
# ======================================================================= #

def get_line_parsers():
    """Return line parsers for the layout module."""
    return [
        (r'<vbox\s+(.+)>$', _parse_vbox_declaration),
        (r'<hbox\s+(.+)>$', _parse_hbox_declaration),
    ]


def _parse_attrs(attrs_str):
    """Parse key="value" and key=<ref_value> attributes from a string."""
    import re
    attributes = {}
    for m in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
        attributes[m.group(1)] = m.group(2)
    for m in re.finditer(r'(\w+)=(<\w+_value>)', attrs_str):
        attributes[m.group(1)] = m.group(2)
    return attributes


def _parse_vbox_declaration(match, current, context):
    """Parse <vbox name="..." parent="..." ...>"""
    node = VBoxNode('vbox', _parse_attrs(match.group(1)))
    current.add_child(node)
    return None


def _parse_hbox_declaration(match, current, context):
    """Parse <hbox name="..." parent="..." ...>"""
    node = HBoxNode('hbox', _parse_attrs(match.group(1)))
    current.add_child(node)
    return None


# ======================================================================= #
# GUI editor metadata                                                       #
# ======================================================================= #

def get_gui_info():
    """Return GUI editor information for layout containers (list of dicts)."""
    common_props = [
        {'name': 'name',    'type': 'string',  'required': True},
        {'name': 'parent',  'type': 'element_ref', 'required': True},
        {'name': 'x',       'type': 'int',     'default': 0},
        {'name': 'y',       'type': 'int',     'default': 0},
        {'name': 'width',   'type': 'int',     'default': 200},
        {'name': 'height',  'type': 'int',     'default': 200},
        {'name': 'padding', 'type': 'int',     'default': 5},
        {'name': 'spacing', 'type': 'int',     'default': 4},
        {'name': 'align',   'type': 'choice',  'choices': ['start', 'center', 'end'], 'default': 'start'},
        {'name': 'fill',    'type': 'choice',  'choices': ['none', 'x', 'y', 'both'], 'default': 'none'},
    ]
    return [
        {
            'type': 'container',
            'category': 'layout',
            'display_name': 'VBox',
            'icon': '⬛',
            'framework': 'tkinter',
            'default_size': (200, 200),
            'editor_colors': {'bg': '#264f78', 'border': '#4fc1ff', 'text': '#d4d4d4'},
            'properties': common_props,
            'syntax': '<vbox name="vbox1" parent="wnd1" x="0" y="0" width="200" height="200">',
            'description': 'Vertical box – stacks children top to bottom automatically',
        },
        {
            'type': 'container',
            'category': 'layout',
            'display_name': 'HBox',
            'icon': '▬',
            'framework': 'tkinter',
            'default_size': (300, 50),
            'editor_colors': {'bg': '#264f78', 'border': '#4ec9b0', 'text': '#d4d4d4'},
            'properties': common_props,
            'syntax': '<hbox name="hbox1" parent="wnd1" x="0" y="0" width="300" height="50">',
            'description': 'Horizontal box – places children left to right automatically',
        },
    ]


__all__ = [
    'LayoutBox',
    'VBox',
    'HBox',
    'VBoxNode',
    'HBoxNode',
    'get_line_parsers',
    'get_gui_info',
    'GUI_NODE_TYPE',
]
