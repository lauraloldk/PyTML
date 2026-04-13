# PyTML

**PyTML** (Python Template Markup Language) is a declarative markup language that compiles to Python/Tkinter applications. It combines the simplicity of HTML-like syntax with the power of Python, making GUI development intuitive and accessible.

## Features

- 🎨 **Declarative GUI** - Define windows, buttons, labels, and more with simple tags
- ⚡ **Event-Driven** - Handle clicks and user input with intuitive event syntax
- 🔢 **Built-in Math** - Support for inline math operations (`+=`, `-=`, `++`, `--`)
- 🔄 **Reactive Updates** - Dynamic property binding with variable references
- 📦 **Layout Containers** - `<vbox>` / `<hbox>` for automatic widget placement
- 🔍 **Lint + Quick Fixes** - Built-in static analysis with one-click fixes
- 🧩 **Extensible** - Plugin system and library editor for adding custom components

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/PyTML.git
cd PyTML
python Main.py
```

Requires Python 3.10+ with Tkinter (included in standard Python installation).

### Hello World

Create a file `hello.pytml`:

```xml
<gui>
<window title="Hello World" name="wnd" size="300","200">
<wnd_show>
<label text="Hello, PyTML!" name="lbl" parent="wnd" x="100" y="80">
</gui>
```

Run it:
```bash
python Main.py hello.pytml
```

## Syntax Overview

### Variables

```xml
<var name="counter" value="0">
<var name="message" value="Hello">
```

### Math Operations

```xml
<counter_value += 1>
<counter_value -= 1>
<counter_value++>
<counter_value-->
<math result="<a_value> + <b_value> * 2">
```

### GUI Components

```xml
<!-- Window -->
<window title="My App" name="wnd1" size="400","300">
<wnd1_show>

<!-- Button -->
<button text="Click Me" name="btn1" parent="wnd1" x="10" y="10">

<!-- Label -->
<label text="Status" name="lbl1" parent="wnd1" x="10" y="50">

<!-- Entry (text input) -->
<entry name="input1" parent="wnd1" x="10" y="90" width="200">
```

### Events

```xml
<forever interval="100">
    <if event="<btn1_click>">
        <!-- Handle button click -->
        <lbl1_text="Button was clicked!">
    </if>
</forever>
```

### Dynamic Property Updates

```xml
<!-- Update label text with variable value -->
<lbl1_text="<counter_value>">

<!-- Update window title -->
<wnd1_title="Count: <counter_value>">
```

## Example: Counter App

```xml
<noterminate>
<var name="counter" value="0">
<gui>
<window title="Counter: 0" name="wnd1" size="300","200">
<wnd1_show>
<button text="+" name="btn_plus" parent="wnd1" x="20" y="30">
<button text="-" name="btn_minus" parent="wnd1" x="180" y="30">
<button text="Exit" name="btn_exit" parent="wnd1" x="100" y="140">
<label text="0" name="lbl1" parent="wnd1" x="140" y="40">
</gui>
<forever interval="100">
    <if event="<btn_plus_click>">
        <counter_value += 1>
        <lbl1_text="<counter_value>">
        <wnd1_title="Counter: <counter_value>">
    </if>
    <if event="<btn_minus_click>">
        <counter_value -= 1>
        <lbl1_text="<counter_value>">
        <wnd1_title="Counter: <counter_value>">
    </if>
    <if event="<btn_exit_click>">
        <wnd1_exit>
    </if>
</forever>
```

## Project Structure

```
PyTML/
├── Main.py              # Entry point - runs .pytml files
├── Compiler.py          # Core compiler and AST nodes
├── PyTML_Editor.py      # Visual editor for PyTML
├── libs/                # Core library modules
│   ├── core.py          # Base classes (ActionNode, WidgetNode, etc.)
│   ├── registry.py      # Tag registry and semantic analyzer
│   ├── var.py           # Variables and math operations
│   ├── window.py        # Window widget
│   ├── button.py        # Button widget
│   ├── label.py         # Label widget
│   ├── entry.py         # Text entry widget
│   ├── layout.py        # Layout containers (VBox, HBox)
│   ├── input.py         # Console input
│   ├── output.py        # Console output
│   └── console_utils.py # Terminal utilities
└── plugins/             # Editor plugins
    ├── Objects.py       # Object browser panel
    ├── Properties.py    # Property editor panel
    ├── GUIEdit.py       # Visual GUI editor
    ├── LintFix.py       # Lint + Quick Fixes panel
    ├── references.py    # API reference browser
    └── LibEditor.py     # Python module browser (read-only)
```

## Available Tags

| Tag | Description | Example |
|-----|-------------|---------|
| `<var>` | Declare a variable | `<var name="x" value="10">` |
| `<window>` | Create a window | `<window title="App" name="w" size="400","300">` |
| `<button>` | Create a button | `<button text="OK" name="btn" parent="w" x="10" y="10">` |
| `<label>` | Create a label | `<label text="Hi" name="lbl" parent="w" x="10" y="50">` |
| `<entry>` | Create text input | `<entry name="inp" parent="w" x="10" y="90">` |
| `<vbox>` | Vertical layout box | `<vbox name="vb" parent="w" x="0" y="0" width="200" height="300">` |
| `<hbox>` | Horizontal layout box | `<hbox name="hb" parent="w" x="0" y="0" width="300" height="50">` |
| `<output>` | Print to console | `<output value="Hello">` |
| `<input>` | Read from console | `<input var="name" prompt="Enter name:">` |
| `<if>` | Conditional block | `<if condition="<x_value> > 5">` |
| `<forever>` | Event loop | `<forever interval="100">` |
| `<math>` | Math expression | `<math result="<a> + <b>">` |
| `<noterminate>` | Keep console open | `<noterminate>` |

### Layout Containers

`<vbox>` and `<hbox>` are layout containers that stack child widgets automatically
without requiring explicit `x`/`y` coordinates on each child.

**Supported properties:** `name`, `parent`, `x`, `y`, `width`, `height`,
`padding`, `spacing`, `align` (`start`/`center`/`end`), `fill` (`none`/`x`/`y`/`both`).

```xml
<gui>
<window name="wnd1" title="Layout Demo" size="300","400">
<wnd1_show>
<!-- Vertical stack inside the window -->
<vbox name="vbox1" parent="wnd1" x="10" y="10" width="280" height="380" padding="8" spacing="6">
<button text="Button A" name="btnA" parent="vbox1">
<button text="Button B" name="btnB" parent="vbox1">
<label  text="A label"  name="lbl1" parent="vbox1">
<entry  name="input1"               parent="vbox1">
</gui>
```

Horizontal stacking:

```xml
<hbox name="toolbar" parent="wnd1" x="0" y="0" width="400" height="40">
<button text="File" name="menuFile" parent="toolbar">
<button text="Edit" name="menuEdit" parent="toolbar">
<button text="View" name="menuView" parent="toolbar">
```

## Tools

### PyTML Editor
Visual drag-and-drop editor for creating PyTML applications:
```bash
python PyTML_Editor.py
```

The editor includes:
- **Objects panel** – browse all available tags and insert them
- **Properties panel** – edit element properties visually
- **Lint panel** – real-time static analysis with quick fixes

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with Python and Tkinter. Inspired by the simplicity of HTML and the power of Python.
