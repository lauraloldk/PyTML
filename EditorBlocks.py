"""
PyTML Editor Blocks
Definerer editor tilstande og blokke som <code> og <gui>
Bruges til at fortælle værktøjer hvilken del de skal arbejde med
"""

import re


class EditorBlock:
    """Base klasse for editor blokke"""
    
    def __init__(self, block_type, content=""):
        self.block_type = block_type  # 'code', 'gui', etc.
        self.content = content
        self.start_line = 0
        self.end_line = 0
        self.children = []
        self.parent = None
    
    def add_child(self, child):
        """Tilføj et child block"""
        child.parent = self
        self.children.append(child)
        return child
    
    def get_content(self):
        """Hent block indhold"""
        return self.content
    
    def set_content(self, content):
        """Sæt block indhold"""
        self.content = content
    
    def __repr__(self):
        return f"<{self.block_type}> ({self.end_line - self.start_line + 1} linjer)"


class CodeBlock(EditorBlock):
    """
    Code block: <code>...</code>
    Indeholder ren PyTML kode der skal kompileres
    """
    
    def __init__(self, content=""):
        super().__init__('code', content)


class GUIBlock(EditorBlock):
    """
    GUI block: <gui>...</gui>
    Indeholder GUI definitioner der kan redigeres visuelt
    """
    
    def __init__(self, content=""):
        super().__init__('gui', content)
        self.windows = []  # Liste af Window objekter i denne blok
        self.widgets = []  # Liste af widgets
    
    def add_window(self, window):
        """Tilføj et vindue til GUI blokken"""
        self.windows.append(window)
        return window


class EditorBlockParser:
    """Parser til at opdele PyTML fil i blokke"""
    
    def __init__(self):
        self.blocks = []
        self.current_mode = 'code'  # Default mode er code
    
    def parse(self, source):
        """Parse kildekode og opdel i blokke"""
        self.blocks = []
        lines = source.split('\n')
        
        current_block = None
        current_content = []
        current_start = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Tjek for block start tags
            if stripped == '<code>':
                # Gem forrige block hvis der er en
                if current_content:
                    self._save_block(current_block or 'code', current_content, current_start, i - 1)
                current_block = 'code'
                current_content = []
                current_start = i + 1
                continue
            
            elif stripped == '<gui>':
                if current_content:
                    self._save_block(current_block or 'code', current_content, current_start, i - 1)
                current_block = 'gui'
                current_content = []
                current_start = i + 1
                continue
            
            # Tjek for block end tags
            elif stripped == '</code>' or stripped == '</gui>':
                if current_content:
                    self._save_block(current_block or 'code', current_content, current_start, i - 1)
                current_block = None
                current_content = []
                current_start = i + 1
                continue
            
            # Tilføj linje til current content
            current_content.append(line)
        
        # Gem sidste block
        if current_content:
            self._save_block(current_block or 'code', current_content, current_start, len(lines) - 1)
        
        return self.blocks
    
    def _save_block(self, block_type, content, start, end):
        """Gem en block"""
        content_str = '\n'.join(content)
        
        if block_type == 'gui':
            block = GUIBlock(content_str)
        else:
            block = CodeBlock(content_str)
        
        block.start_line = start
        block.end_line = end
        self.blocks.append(block)
    
    def get_blocks_by_type(self, block_type):
        """Hent alle blokke af en bestemt type"""
        return [b for b in self.blocks if b.block_type == block_type]
    
    def get_code_blocks(self):
        """Hent alle code blokke"""
        return self.get_blocks_by_type('code')
    
    def get_gui_blocks(self):
        """Hent alle GUI blokke"""
        return self.get_blocks_by_type('gui')
    
    def get_block_at_line(self, line_number):
        """Find hvilken block en linje tilhører"""
        for block in self.blocks:
            if block.start_line <= line_number <= block.end_line:
                return block
        return None


class EditorState:
    """Holder styr på editor tilstand"""
    
    def __init__(self):
        self.current_mode = 'code'  # 'code' eller 'gui'
        self.blocks = []
        self.active_block = None
        self.cursor_line = 0
    
    def set_mode(self, mode):
        """Skift editor tilstand"""
        if mode in ('code', 'gui'):
            self.current_mode = mode
    
    def is_code_mode(self):
        """Er vi i code mode?"""
        return self.current_mode == 'code'
    
    def is_gui_mode(self):
        """Er vi i GUI mode?"""
        return self.current_mode == 'gui'
    
    def update_from_cursor(self, line_number, parser):
        """Opdater tilstand baseret på cursor position"""
        self.cursor_line = line_number
        block = parser.get_block_at_line(line_number)
        if block:
            self.active_block = block
            self.current_mode = block.block_type


# Eksporter
__all__ = [
    'EditorBlock',
    'CodeBlock', 
    'GUIBlock',
    'EditorBlockParser',
    'EditorState'
]
