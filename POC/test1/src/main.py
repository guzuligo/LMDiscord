"""
GUI Application Class

This module contains the main application class that initializes and runs
the tkinter GUI with LM Studio chat interface.
"""

import tkinter as tk
from tkinter import messagebox

from src.gui.main_window import MainWindow
from src.gui.styles import BG_COLOR


class Application:
    """Main application class that manages the GUI lifecycle."""
    
    def __init__(self):
        """Initialize the application."""
        self.root = tk.Tk()
        self.root.title("Discord Bot - LM Studio POC")
        self.root.configure(bg=BG_COLOR)
        
        # Set window icon and size
        window_width = 700
        window_height = 550
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(600, 450)
        
        # Create main window
        self.main_window = MainWindow(self.root)
    
    def run(self) -> None:
        """Start the application event loop."""
        self.root.mainloop()