"""
PyTML Editor
A simple editor for writing and running PyTML code
With integrated plugins: Objects, Properties and GUIEdit
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Compiler import PyTMLCompiler, compile_pytml
from plugins.Objects import ObjectsPanel
from plugins.Properties import PropertiesPanel, parse_line_to_element
from plugins.GUIEdit import GUIEditPanel
from plugins.references import ReferencesPanel
from EditorBlocks import EditorBlockParser, EditorState


class PyTMLEditor:
    """GUI Editor for PyTML files with plugins"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("PyTML Editor")
        self.root.geometry("1400x800")
        
        self.current_file = None
        self.parser = None
        self.editor_state = EditorState()
        self.block_parser = EditorBlockParser()
        
        self._setup_menu()
        self._setup_ui()
        self._setup_bindings()
        
        # Load default file if it exists
        default_file = os.path.join(os.path.dirname(__file__), "Main.pytml")
        if os.path.exists(default_file):
            self.load_file(default_file)
    
    def _setup_menu(self):
        """Setup the menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Run menu
        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run", command=self.run_code, accelerator="F5")
        run_menu.add_command(label="Step Through", command=self.step_through, accelerator="F10")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Objects Panel", command=self._toggle_objects_panel)
        view_menu.add_command(label="Toggle Properties Panel", command=self._toggle_properties_panel)
        view_menu.add_command(label="Toggle GUI Editor", command=self._toggle_gui_editor)
        view_menu.add_command(label="Show All References", command=self._show_references)
    
    def _setup_ui(self):
        """Setup UI components with plugins"""
        # Main paned window (horizontal)
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === LEFT PANEL: Objects Browser ===
        self.objects_frame = ttk.LabelFrame(self.main_paned, text="📦 Objects")
        self.main_paned.add(self.objects_frame, weight=1)
        
        self.objects_panel = ObjectsPanel(self.objects_frame, editor_callback=self._insert_from_objects)
        self.objects_panel.pack(fill=tk.BOTH, expand=True)
        
        # === CENTER PANEL: Editor + Output ===
        center_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(center_frame, weight=3)
        
        # Notebook for Code/GUI mode
        self.mode_notebook = ttk.Notebook(center_frame)
        self.mode_notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- Code Tab ---
        code_tab = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(code_tab, text="📝 Code")
        
        # Editor paned (code + output)
        editor_paned = ttk.PanedWindow(code_tab, orient=tk.VERTICAL)
        editor_paned.pack(fill=tk.BOTH, expand=True)
        
        # Code editor frame
        editor_frame = ttk.Frame(editor_paned)
        editor_paned.add(editor_frame, weight=3)
        
        # Editor label + mode indicator
        editor_header = ttk.Frame(editor_frame)
        editor_header.pack(fill=tk.X)
        ttk.Label(editor_header, text="PyTML Code:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.mode_label = ttk.Label(editor_header, text="[code mode]", foreground='#569cd6')
        self.mode_label.pack(side=tk.RIGHT, padx=5)
        
        # Code editor
        self.editor = scrolledtext.ScrolledText(
            editor_frame, 
            wrap=tk.NONE,
            font=('Consolas', 11),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white'
        )
        self.editor.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Horizontal scrollbar for editor
        h_scroll = ttk.Scrollbar(editor_frame, orient=tk.HORIZONTAL, command=self.editor.xview)
        h_scroll.pack(fill=tk.X)
        self.editor.config(xscrollcommand=h_scroll.set)
        
        # Output frame
        output_frame = ttk.Frame(editor_paned)
        editor_paned.add(output_frame, weight=1)
        
        ttk.Label(output_frame, text="Output:", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        self.output = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#0c0c0c',
            fg='#00ff00',
            state='disabled',
            height=8
        )
        self.output.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # --- GUI Tab ---
        gui_tab = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(gui_tab, text="🎨 GUI Editor")
        
        self.gui_editor = GUIEditPanel(gui_tab, on_code_change=self._on_gui_code_change)
        self.gui_editor.pack(fill=tk.BOTH, expand=True)
        
        # --- References Tab ---
        refs_tab = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(refs_tab, text="📚 References")
        
        self.references_panel = ReferencesPanel(refs_tab, editor_callback=self._insert_from_references)
        self.references_panel.pack(fill=tk.BOTH, expand=True)
        
        # Bind tab change event
        self.mode_notebook.bind('<<NotebookTabChanged>>', self._on_tab_change)
        
        # === RIGHT PANEL: Properties + Variables ===
        right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(right_frame, weight=1)
        
        # Properties panel
        self.properties_frame = ttk.LabelFrame(right_frame, text="⚙️ Properties")
        self.properties_frame.pack(fill=tk.BOTH, expand=True)
        
        self.properties_panel = PropertiesPanel(self.properties_frame, on_property_change=self._on_property_change)
        self.properties_panel.pack(fill=tk.BOTH, expand=True)
        
        # Variables panel
        var_frame = ttk.LabelFrame(right_frame, text="📊 Variables")
        var_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.var_tree = ttk.Treeview(var_frame, columns=('Value',), height=6)
        self.var_tree.heading('#0', text='Name')
        self.var_tree.heading('Value', text='Value')
        self.var_tree.column('#0', width=100)
        self.var_tree.column('Value', width=150)
        self.var_tree.pack(fill=tk.X, pady=5, padx=5)
        
        # Button frame
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(btn_frame, text="▶ Run (F5)", command=self.run_code).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="⏭ Step (F10)", command=self.step_through).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Clear", command=self.clear_output).pack(side=tk.LEFT, padx=2)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor='w')
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _setup_bindings(self):
        """Setup keyboard bindings"""
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<F5>', lambda e: self.run_code())
        self.root.bind('<F10>', lambda e: self.step_through())
        
        # Editor bindings for properties update
        self.editor.bind('<ButtonRelease-1>', self._on_editor_click)
        self.editor.bind('<KeyRelease>', self._on_editor_key)
    
    def _on_editor_click(self, event):
        """Update properties when clicking in the editor"""
        self._update_properties_from_cursor()
    
    def _on_editor_key(self, event):
        """Update properties on keyboard navigation"""
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return'):
            self._update_properties_from_cursor()
    
    def _update_properties_from_cursor(self):
        """Update properties panel based on cursor position"""
        try:
            # Get current line
            line_idx = self.editor.index(tk.INSERT).split('.')[0]
            line = self.editor.get(f"{line_idx}.0", f"{line_idx}.end")
            
            if line.strip():
                element = parse_line_to_element(line)
                if element:
                    self.properties_panel.load_element(element)
                    self.mode_label.config(text=f"[{element.element_type}]")
        except:
            pass
    
    def _insert_from_objects(self, syntax):
        """Callback from Objects panel - insert syntax in editor"""
        self.editor.insert(tk.INSERT, syntax + "\n")
        self.editor.see(tk.INSERT)
        self.status_var.set(f"Inserted: {syntax[:30]}...")
    
    def _insert_from_references(self, syntax):
        """Callback from References panel - insert syntax in editor"""
        # Switch to Code tab and insert
        self.mode_notebook.select(0)
        self.editor.insert(tk.INSERT, syntax + "\n")
        self.editor.see(tk.INSERT)
        self.status_var.set(f"Reference inserted: {syntax[:30]}...")
    
    def _on_property_change(self, element, prop):
        """Callback when a property changes"""
        if element:
            # Generate new PyTML code
            new_code = element.to_pytml()
            
            # Replace current line
            line_idx = self.editor.index(tk.INSERT).split('.')[0]
            self.editor.delete(f"{line_idx}.0", f"{line_idx}.end")
            self.editor.insert(f"{line_idx}.0", new_code.strip())
            
            self.status_var.set(f"Property updated: {prop.name}")
    
    def _on_gui_code_change(self, code, realtime=False):
        """Callback from GUI editor when code changes"""
        if code == "__REFRESH__":
            # Refresh GUI preview from current code
            current_code = self.editor.get('1.0', tk.END)
            self.gui_editor.load_from_code(current_code)
            self.status_var.set("GUI preview updated from code")
        elif realtime:
            # Realtime synchronization - replace all code
            cursor_pos = self.editor.index(tk.INSERT)
            self.editor.delete('1.0', tk.END)
            self.editor.insert('1.0', code)
            # Try to preserve cursor position
            try:
                self.editor.mark_set(tk.INSERT, cursor_pos)
                self.editor.see(tk.INSERT)
            except:
                pass
            self.status_var.set("🔄 GUI synchronized")
        else:
            # Legacy: Insert code (no longer used)
            self.editor.insert(tk.END, "\n" + code)
            self.mode_notebook.select(0)
            self.status_var.set("GUI code generated and inserted")
    
    def _toggle_objects_panel(self):
        """Show/hide Objects panel"""
        if self.objects_frame.winfo_viewable():
            self.main_paned.forget(self.objects_frame)
        else:
            self.main_paned.insert(0, self.objects_frame, weight=1)
    
    def _toggle_properties_panel(self):
        """Show/hide Properties panel"""
        if self.properties_frame.winfo_viewable():
            self.properties_frame.pack_forget()
        else:
            self.properties_frame.pack(fill=tk.BOTH, expand=True)
    
    def _toggle_gui_editor(self):
        """Switch to GUI editor tab"""
        self.mode_notebook.select(1)
    
    def _show_references(self):
        """Switch to References tab"""
        self.mode_notebook.select(2)
    
    def _on_tab_change(self, event):
        """Handle tab switch"""
        current_tab = self.mode_notebook.index(self.mode_notebook.select())
        if current_tab == 1:  # GUI Editor tab
            # Load current code into GUI preview
            current_code = self.editor.get('1.0', tk.END)
            self.gui_editor.load_from_code(current_code)
    
    def new_file(self):
        """Create new file"""
        self.editor.delete('1.0', tk.END)
        self.current_file = None
        self.root.title("PyTML Editor - New file")
        self.status_var.set("New file created")
    
    def open_file(self):
        """Open file dialog"""
        filepath = filedialog.askopenfilename(
            defaultextension=".pytml",
            filetypes=[("PyTML files", "*.pytml"), ("All files", "*.*")]
        )
        if filepath:
            self.load_file(filepath)
    
    def load_file(self, filepath):
        """Load a file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor.delete('1.0', tk.END)
            self.editor.insert('1.0', content)
            self.current_file = filepath
            self.root.title(f"PyTML Editor - {os.path.basename(filepath)}")
            self.status_var.set(f"Loaded: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def save_file(self):
        """Save file"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.save_file_as()
    
    def save_file_as(self):
        """Save file as..."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pytml",
            filetypes=[("PyTML files", "*.pytml"), ("All files", "*.*")]
        )
        if filepath:
            self._save_to_file(filepath)
            self.current_file = filepath
            self.root.title(f"PyTML Editor - {os.path.basename(filepath)}")
    
    def _save_to_file(self, filepath):
        """Save content to file"""
        try:
            content = self.editor.get('1.0', tk.END)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_var.set(f"Saved: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")
    
    def run_code(self):
        """Run PyTML code in a separate process"""
        code = self.editor.get('1.0', tk.END)
        self.clear_output()
        
        # Save code to a temporary file and run in separate process
        import tempfile
        import subprocess
        import os
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pytml', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
            
            # Run in separate process
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Create a runner script
            runner_script = os.path.join(script_dir, '_temp_runner.py')
            with open(runner_script, 'w', encoding='utf-8') as f:
                f.write(f'''import sys
sys.path.insert(0, r"{script_dir}")
from Compiler import compile_pytml
with open(r"{temp_file}", "r", encoding="utf-8") as f:
    code = f.read()
try:
    compile_pytml(code, gui_mode=False)
except Exception as e:
    print(f"ERROR: {{e}}")
    import traceback
    traceback.print_exc()
''')
            
            # Start subprocess WITHOUT pipes (so GUI works)
            process = subprocess.Popen(
                [sys.executable, runner_script],
                cwd=script_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            # Show info
            self.output.config(state='normal')
            self.output.insert(tk.END, "=== PyTML running in new window ===\n")
            self.output.insert(tk.END, f"Process ID: {process.pid}\n")
            self.output.config(state='disabled')
            
            self.status_var.set("Running in separate console...")
            
            # Cleanup temp files after process is done
            def cleanup():
                try:
                    if process.poll() is not None:  # Process is done
                        try:
                            os.unlink(temp_file)
                            os.unlink(runner_script)
                        except:
                            pass
                        self.status_var.set("Execution finished")
                    else:
                        # Check again in 1000ms
                        self.root.after(1000, cleanup)
                except:
                    pass
            
            self.root.after(1000, cleanup)
            
        except Exception as e:
            self.output.config(state='normal')
            self.output.insert(tk.END, f"ERROR: {e}\n")
            self.output.config(state='disabled')
            self.status_var.set(f"Error: {e}")
    
    def step_through(self):
        """Step through the code line by line"""
        # TODO: Implement step-by-step execution
        messagebox.showinfo("Step Through", "Step-through mode coming soon!\nUse Object Browser to see action tree.")
        self.status_var.set("Step through - not implemented yet")
    
    def clear_output(self):
        """Clear output"""
        self.output.config(state='normal')
        self.output.delete('1.0', tk.END)
        self.output.config(state='disabled')
        
        # Clear variable tree
        for item in self.var_tree.get_children():
            self.var_tree.delete(item)
    
    def update_var_tree(self, variable_store):
        """Update variable tree with current variables"""
        # Clear first
        for item in self.var_tree.get_children():
            self.var_tree.delete(item)
        
        # Add variables
        for name, var in variable_store.variables.items():
            self.var_tree.insert('', tk.END, text=name, values=(var.value,))


def main():
    """Start PyTML Editor"""
    root = tk.Tk()
    app = PyTMLEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
