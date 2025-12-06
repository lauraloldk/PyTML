"""
PyTML - Python med HTML Syntax
Main launcher og runtime
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog

# Import compiler
from Compiler import compile_pytml


def run_pytml_file(filepath=None):
    """Kør en PyTML fil"""
    if filepath is None:
        # Opret midlertidig root for file dialog
        temp_root = tk.Tk()
        temp_root.withdraw()
        filepath = filedialog.askopenfilename(
            title="Vælg PyTML fil",
            defaultextension=".pytml",
            filetypes=[("PyTML files", "*.pytml"), ("All files", "*.*")]
        )
        temp_root.destroy()
    
    if filepath and os.path.exists(filepath):
        print(f"=== PyTML Runtime ===\n")
        print(f"Kører: {filepath}\n")
        print("--- Output ---\n")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            pytml_code = f.read()
        
        result = compile_pytml(pytml_code)
        
        print("\n--- Variabler efter kørsel ---")
        for name, var in result['variables'].variables.items():
            print(f"  {name} = {var.value}")


def open_editor():
    """Åbn PyTML Editor"""
    import subprocess
    subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "PyTML_Editor.py")])


def open_object_browser():
    """Åbn Object Browser"""
    import subprocess
    subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "Object_Browser.py")])


class PyTMLLauncher:
    """Hovedlauncher for PyTML"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PyTML Launcher")
        self.root.geometry("400x320")
        self.root.minsize(350, 300)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Opsæt UI"""
        # Center vindue
        self.root.eval('tk::PlaceWindow . center')
        
        # Header
        header = ttk.Label(self.root, text="🐍 PyTML", font=('Arial', 24, 'bold'))
        header.pack(pady=(30, 10))
        
        subtitle = ttk.Label(self.root, text="Python med HTML Syntax", font=('Arial', 10))
        subtitle.pack(pady=(0, 20))
        
        # Button frame
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20, fill=tk.X, padx=40)
        
        # Buttons
        ttk.Button(
            btn_frame, 
            text="▶  Åbn/Kør .pytml fil",
            command=self._run_file_and_close
        ).pack(pady=8, fill=tk.X, ipady=10)
        
        ttk.Button(
            btn_frame,
            text="📝  Åbn Editor",
            command=self._open_editor_and_close
        ).pack(pady=8, fill=tk.X, ipady=10)
        
        ttk.Button(
            btn_frame,
            text="🔍  Åbn Object Browser",
            command=self._open_browser_and_close
        ).pack(pady=8, fill=tk.X, ipady=10)
        
        # Footer
        ttk.Label(self.root, text="v1.0", font=('Arial', 8), foreground='gray').pack(side=tk.BOTTOM, pady=10)
    
    def _run_file_and_close(self):
        """Kør fil og luk dialog"""
        self.root.destroy()
        run_pytml_file()
    
    def _open_editor_and_close(self):
        """Åbn editor og luk dialog"""
        self.root.destroy()
        open_editor()
    
    def _open_browser_and_close(self):
        """Åbn browser og luk dialog"""
        self.root.destroy()
        open_object_browser()
    
    def run(self):
        """Start launcher"""
        self.root.mainloop()


# Main entry point
if __name__ == "__main__":
    # Tjek for fil argument - kør direkte uden dialog
    if len(sys.argv) > 1:
        run_pytml_file(sys.argv[1])
    else:
        # Vis launcher dialog
        launcher = PyTMLLauncher()
        launcher.run()
