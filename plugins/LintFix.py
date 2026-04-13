"""
PyTML Editor Plugin: Lint + Quick Fixes
=========================================
Provides a panel that runs lightweight static analysis on PyTML code and
offers one-click quick fixes for common issues.

Integrates with the PyTML plugin system (core/plugin_registry.py) via the
standard ``get_plugin_info()`` function.

Checks performed on every code change:
- Unknown tags (not recognised by any lib parser or compiler)
- Missing required attributes (name / parent for GUI elements)
- Duplicate element names
- Dangling event references (<elem_click> without a matching <... name="elem"...>)
- GUI tags outside a <gui>...</gui> block

Quick fixes available:
- Add auto-generated ``name`` attribute
- Add ``parent`` attribute (uses first window found)
- Wrap orphaned GUI tags in ``<gui>...</gui>``

No external dependencies beyond the standard library.
"""

import re
import tkinter as tk
from tkinter import ttk
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ======================================================================= #
# Issue model                                                               #
# ======================================================================= #

class LintIssue:
    """Represents a single lint issue."""

    SEVERITY_ERROR   = 'error'
    SEVERITY_WARNING = 'warning'
    SEVERITY_INFO    = 'info'

    def __init__(self, line_no, message, severity=SEVERITY_WARNING,
                 fix_label=None, fix_fn=None):
        self.line_no   = line_no        # 1-based
        self.message   = message
        self.severity  = severity
        self.fix_label = fix_label      # None → no quick fix available
        self.fix_fn    = fix_fn         # callable(code: str) -> str

    def icon(self):
        return {'error': '🔴', 'warning': '🟡', 'info': '🔵'}.get(self.severity, '⚪')

    def __repr__(self):
        return f"LintIssue(line={self.line_no}, {self.severity}: {self.message})"


# ======================================================================= #
# Static checker                                                            #
# ======================================================================= #

# Tags that are known to the core compiler / base libs.
# Additional tags are discovered dynamically from lib parsers.
_CORE_TAGS = {
    'var', 'variable', 'output', 'noterminate', 'noquit',
    'window', 'button', 'label', 'entry', 'input',
    'vbox', 'hbox',
    'if', 'loop', 'forever', 'block', 'gui', 'math',
}

# Tags that require a ``name`` attribute
_TAGS_NEED_NAME = {'window', 'button', 'label', 'entry', 'vbox', 'hbox'}

# Tags that require a ``parent`` attribute
_TAGS_NEED_PARENT = {'button', 'label', 'entry', 'vbox', 'hbox'}

# Closing tags that must not be checked as opening tags
_CLOSE_TAGS = {'if', 'loop', 'forever', 'block'}

# GUI element tags that must live inside a <gui>…</gui> block
_GUI_ELEMENT_TAGS = {'window', 'button', 'label', 'entry', 'vbox', 'hbox'}

# Colour mapping for issue severities (used by LintIssue.icon and LintPanel)
_SEVERITY_COLORS = {
    LintIssue.SEVERITY_ERROR:   '#f44747',
    LintIssue.SEVERITY_WARNING: '#ce9178',
    LintIssue.SEVERITY_INFO:    '#9cdcfe',
}


def _discover_known_tags():
    """
    Dynamically discover extra known tags from lib ``get_line_parsers()``.
    Returns a set of tag-name strings.
    """
    tags = set(_CORE_TAGS)
    libs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
    if not os.path.isdir(libs_dir):
        return tags

    import importlib.util
    for fname in os.listdir(libs_dir):
        if not fname.endswith('.py') or fname.startswith('_'):
            continue
        fpath = os.path.join(libs_dir, fname)
        try:
            spec = importlib.util.spec_from_file_location(fname[:-3], fpath)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, 'get_line_parsers'):
                for pattern, _ in mod.get_line_parsers():
                    # Extract first word inside < … >
                    m = re.match(r'</?(\w+)', pattern.lstrip('^'))
                    if m:
                        tags.add(m.group(1).lower())
        except Exception:
            pass
    return tags


class LintChecker:
    """
    Runs a series of lightweight static checks on PyTML source text.
    Returns a list of LintIssue objects.
    """

    def __init__(self):
        self._known_tags = None

    def _get_known_tags(self):
        if self._known_tags is None:
            try:
                self._known_tags = _discover_known_tags()
            except Exception:
                self._known_tags = set(_CORE_TAGS)
        return self._known_tags

    # ------------------------------------------------------------------ #

    def check(self, code: str):
        """Run all checks and return a list of LintIssue."""
        issues = []
        lines  = code.splitlines()

        # Collect declared element names for cross-checks
        declared_names = {}   # name → line_no (1-based)
        windows_seen   = []   # names of declared windows

        inside_gui = False

        for i, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            # Track <gui> / </gui> blocks
            if re.match(r'^<gui>', line):
                inside_gui = True
                continue
            if re.match(r'^</gui>', line):
                inside_gui = False
                continue

            # Parse as opening tag: <tagname …>
            m = re.match(r'^<(/?)(\w+)(.*?)>$', line, re.DOTALL)
            if not m:
                continue

            closing  = m.group(1) == '/'
            tag_name = m.group(2).lower()
            attrs_str = m.group(3)

            if closing:
                continue

            # ── Check 1: Unknown tag ──────────────────────────────────
            known = self._get_known_tags()
            # Skip tags containing underscore – those are element action patterns
            # like <btn1_click> which are not structural tags in the registry.
            if tag_name not in known and '_' not in tag_name:
                issues.append(LintIssue(
                    i,
                    f"Unknown tag <{tag_name}> – not found in any lib",
                    LintIssue.SEVERITY_WARNING,
                ))

            # ── Check 2: Missing required attributes ──────────────────
            if tag_name in _TAGS_NEED_NAME:
                name_val = self._get_attr(attrs_str, 'name')
                if name_val is None:
                    auto_name = f"{tag_name}_{i}"
                    def _fix_add_name(code, _line=i, _aname=auto_name):
                        return _inject_attr(code, _line, 'name', _aname)
                    issues.append(LintIssue(
                        i,
                        f"<{tag_name}> is missing required attribute 'name'",
                        LintIssue.SEVERITY_ERROR,
                        fix_label=f'Add name="{auto_name}"',
                        fix_fn=_fix_add_name,
                    ))
                else:
                    # Track declared names
                    if name_val in declared_names:
                        prev = declared_names[name_val]
                        issues.append(LintIssue(
                            i,
                            f"Duplicate name '{name_val}' – already defined on line {prev}",
                            LintIssue.SEVERITY_ERROR,
                        ))
                    else:
                        declared_names[name_val] = i
                        if tag_name == 'window':
                            windows_seen.append(name_val)

            if tag_name in _TAGS_NEED_PARENT:
                parent_val = self._get_attr(attrs_str, 'parent')
                if parent_val is None:
                    def _fix_add_parent(code, _line=i, _wins=windows_seen):
                        first_win = _wins[0] if _wins else 'wnd1'
                        return _inject_attr(code, _line, 'parent', first_win)
                    issues.append(LintIssue(
                        i,
                        f"<{tag_name}> is missing required attribute 'parent'",
                        LintIssue.SEVERITY_ERROR,
                        fix_label="Add parent= (nearest window)",
                        fix_fn=_fix_add_parent,
                    ))

            # ── Check 3: GUI tags outside <gui> block ─────────────────
            if tag_name in _GUI_ELEMENT_TAGS and not inside_gui:
                def _fix_wrap_gui(code, _line=i):
                    return _wrap_in_gui(code, _line)
                issues.append(LintIssue(
                    i,
                    f"<{tag_name}> appears outside a <gui>…</gui> block",
                    LintIssue.SEVERITY_WARNING,
                    fix_label="Wrap GUI section in <gui>…</gui>",
                    fix_fn=_fix_wrap_gui,
                ))

        # ── Check 4: Dangling event refs ─────────────────────────────
        for i, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            # Pattern: <somename_click> or <somename_someaction>
            for m in re.finditer(r'<(\w+)_(click|press|release|change)>', line):
                elem_name = m.group(1)
                if elem_name not in declared_names:
                    issues.append(LintIssue(
                        i,
                        f"Event reference <{elem_name}_{m.group(2)}> but '{elem_name}' "
                        f"is not declared in this file",
                        LintIssue.SEVERITY_WARNING,
                    ))

        return issues

    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_attr(attrs_str, attr_name):
        """Extract a named attribute value from an attribute string."""
        m = re.search(rf'\b{attr_name}\s*=\s*"([^"]*)"', attrs_str)
        if m:
            return m.group(1)
        return None


# ======================================================================= #
# Quick-fix helpers                                                         #
# ======================================================================= #

def _inject_attr(code, line_no, attr, value):
    """
    Inject ``attr="value"`` into the tag on *line_no* (1-based), just
    before the closing ``>``.
    """
    # splitlines(True) preserves original line endings (\n or \r\n)
    lines = code.splitlines(True)
    idx = line_no - 1
    if 0 <= idx < len(lines):
        line = lines[idx]
        # Insert before the last >; keep the original line ending
        eol = ''
        stripped = line.rstrip('\r\n')
        if len(line) > len(stripped):
            eol = line[len(stripped):]
        pos = stripped.rfind('>')
        if pos != -1:
            lines[idx] = stripped[:pos] + f' {attr}="{value}"' + stripped[pos:] + eol
    return ''.join(lines)


def _wrap_in_gui(code, hint_line_no):
    """
    Wrap all consecutive GUI tags that are not already inside a <gui> block
    with ``<gui>`` / ``</gui>``.  Inserts tags on lines immediately before /
    after the first / last GUI tag run.
    """
    gui_tags = _GUI_ELEMENT_TAGS
    # Detect line separator used in the file
    sep = '\r\n' if '\r\n' in code else '\n'
    lines = code.splitlines()
    inside = False
    first_idx = None
    last_idx  = None

    for i, l in enumerate(lines):
        m = re.match(r'^\s*</?(\w+)', l)
        if not m:
            continue
        tag = m.group(1).lower()
        if tag == 'gui':
            inside = True
        if l.strip() == '</gui>':
            inside = False
        if tag in gui_tags and not inside:
            if first_idx is None:
                first_idx = i
            last_idx = i

    if first_idx is None:
        return code

    lines.insert(last_idx + 1, '</gui>')
    lines.insert(first_idx, '<gui>')
    return sep.join(lines)


# ======================================================================= #
# Panel UI                                                                  #
# ======================================================================= #

class LintPanel(ttk.Frame):
    """
    Editor panel that displays lint issues and offers quick fixes.

    Designed to be embedded in the PyTML editor as a right-panel plugin.
    Receives code changes via ``notify_code_change(code)``.
    """

    def __init__(self, parent, editor_callback=None):
        super().__init__(parent)
        self.editor_callback = editor_callback
        self._checker = LintChecker()
        self._issues  = []
        self._code    = ''
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI                                                                   #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        # Header
        hdr = ttk.Frame(self)
        hdr.pack(fill=tk.X, padx=4, pady=(4, 0))
        ttk.Label(hdr, text='🔍 Lint', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Button(hdr, text='↻', width=3,
                   command=self._recheck).pack(side=tk.RIGHT)

        self._count_lbl = ttk.Label(hdr, text='No issues', foreground='gray')
        self._count_lbl.pack(side=tk.RIGHT, padx=6)

        # Issue list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._listbox = tk.Listbox(
            list_frame,
            selectmode=tk.SINGLE,
            activestyle='none',
            bg='#1e1e1e', fg='#d4d4d4',
            selectbackground='#264f78',
            selectforeground='#ffffff',
            font=('Consolas', 9),
            relief=tk.FLAT,
            bd=0,
        )
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                           command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        self._listbox.grid(row=0, column=0, sticky='nsew')
        sb.grid(row=0, column=1, sticky='ns')
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self._listbox.bind('<<ListboxSelect>>', self._on_select)

        # Detail / fix area
        detail_frame = ttk.LabelFrame(self, text='Detail')
        detail_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

        self._detail_var = tk.StringVar(value='Select an issue above.')
        detail_lbl = ttk.Label(detail_frame, textvariable=self._detail_var,
                               wraplength=220, justify=tk.LEFT)
        detail_lbl.pack(fill=tk.X, padx=4, pady=2)

        self._fix_btn = ttk.Button(detail_frame, text='⚡ Apply Fix',
                                   state=tk.DISABLED,
                                   command=self._apply_fix)
        self._fix_btn.pack(pady=(0, 4))

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def notify_code_change(self, code: str):
        """Called by the editor whenever the code changes."""
        self._code = code
        self._recheck()

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _recheck(self):
        if not self._code:
            return
        self._issues = self._checker.check(self._code)
        self._populate_list()

    def _populate_list(self):
        self._listbox.delete(0, tk.END)
        for issue in self._issues:
            label = f"{issue.icon()}  L{issue.line_no}: {issue.message}"
            self._listbox.insert(tk.END, label)
            color = _SEVERITY_COLORS.get(issue.severity, '#d4d4d4')
            self._listbox.itemconfig(tk.END, fg=color)

        n = len(self._issues)
        errors   = sum(1 for i in self._issues if i.severity == LintIssue.SEVERITY_ERROR)
        warnings = sum(1 for i in self._issues if i.severity == LintIssue.SEVERITY_WARNING)
        if n == 0:
            self._count_lbl.config(text='✅ No issues', foreground='#4ec9b0')
        else:
            self._count_lbl.config(
                text=f'{errors}🔴 {warnings}🟡',
                foreground='#ce9178',
            )

        self._detail_var.set('Select an issue above.')
        self._fix_btn.config(state=tk.DISABLED)

    def _on_select(self, _event=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._issues):
            return
        issue = self._issues[idx]
        self._detail_var.set(
            f"Line {issue.line_no}  [{issue.severity.upper()}]\n{issue.message}"
        )
        if issue.fix_fn and issue.fix_label:
            self._fix_btn.config(state=tk.NORMAL,
                                  text=f'⚡ {issue.fix_label}')
        else:
            self._fix_btn.config(state=tk.DISABLED,
                                  text='⚡ Apply Fix')

    def _apply_fix(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._issues):
            return
        issue = self._issues[idx]
        if issue.fix_fn:
            try:
                new_code = issue.fix_fn(self._code)
                if new_code != self._code:
                    self._code = new_code
                    if self.editor_callback:
                        self.editor_callback(new_code)
                    self._recheck()
            except Exception as e:
                self._detail_var.set(f"Fix failed: {e}")


# ======================================================================= #
# Plugin registration                                                       #
# ======================================================================= #

def get_plugin_info():
    """Plugin registration for auto-discovery by core/plugin_registry.py."""
    return {
        'name': 'LintFix',
        'panel_type': 'right',
        'panel_class': LintPanel,
        'panel_icon': '🔍',
        'panel_name': 'Lint',
        'priority': 50,
        'callbacks': {
            'on_code_change': 'notify_code_change',
        },
        'menu_items': [
            {'menu': 'View', 'label': 'Toggle Lint Panel', 'command': 'toggle'},
        ],
    }


__all__ = ['LintIssue', 'LintChecker', 'LintPanel', 'get_plugin_info']
