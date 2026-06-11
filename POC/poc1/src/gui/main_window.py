"""
Main GUI Window Module - Basic LM Studio Chat Interface

This module implements the main application window with basic LM Studio
communication and chat interface.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from threading import Thread

from src.config import Config
from src.lm_studio_client import LMStudioClient
from src.gui.styles import *


class MainWindow:
    """Main application window with LM Studio chat interface."""
    
    def __init__(self, root: tk.Tk):
        """Initialize the main window.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Discord Bot - LM Studio POC")
        self.root.geometry("700x550")
        self.root.configure(bg=BG_COLOR)
        
        # Initialize config and client
        self.config = Config()
        self.client = LMStudioClient(
            self.config.lm_studio_hostname,
            self.config.lm_studio_port
        )
        
        # Chat history (for LM Studio context)
        self.chat_history = []
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the user interface."""
        # --- Title ---
        title_label = tk.Label(
            self.root,
            text="LM Studio Chat POC",
            font=HEADING_FONT,
            fg=ACCENT_COLOR,
            bg=BG_COLOR
        )
        title_label.pack(pady=(15, 5))
        
        # --- Connection Section ---
        conn_frame = tk.Frame(self.root, bg=BG_COLOR)
        conn_frame.pack(fill=tk.X, padx=MARGIN, pady=5)
        
        tk.Label(
            conn_frame,
            text="LM Studio:",
            fg=FG_COLOR,
            bg=BG_COLOR,
            font=(FONT_FAMILY, 10)
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.host_var = tk.StringVar(value=self.config.lm_studio_hostname)
        self.port_var = tk.StringVar(value=str(self.config.lm_studio_port))
        
        host_entry = tk.Entry(
            conn_frame,
            textvariable=self.host_var,
            width=ENTRY_WIDTH,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=FG_COLOR
        )
        host_entry.pack(side=tk.LEFT, padx=(0, 3))
        
        tk.Label(
            conn_frame,
            text=":",
            fg=FG_COLOR,
            bg=BG_COLOR
        ).pack(side=tk.LEFT)
        
        port_entry = tk.Entry(
            conn_frame,
            textvariable=self.port_var,
            width=8,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=FG_COLOR
        )
        port_entry.pack(side=tk.LEFT, padx=(3, 3))
        
        self.connect_btn = tk.Button(
            conn_frame,
            text="Connect",
            command=self._on_connect,
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            font=BUTTON_FONT,
            width=BUTTON_WIDTH,
            cursor="hand2"
        )
        self.connect_btn.pack(side=tk.LEFT, padx=3)
        
        self.status_label = tk.Label(
            self.root,
            text="Status: Disconnected",
            fg=STATUS_DISCONNECTED,
            bg=BG_COLOR,
            font=(FONT_FAMILY, 10)
        )
        self.status_label.pack(pady=3)
        
        # --- Chat Section ---
        chat_frame = tk.Frame(self.root, bg=BG_COLOR)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=MARGIN, pady=10)
        
        # Messages display
        self.messages_text = scrolledtext.ScrolledText(
            chat_frame,
            height=18,
            width=LOG_WIDTH,
            bg=LOG_BG,
            fg=LOG_FG,
            font=(FONT_SIZE_LOG, FONT_FAMILY),
            insertbackground=FG_COLOR,
            state=tk.DISABLED,
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0
        )
        self.messages_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # User input
        input_frame = tk.Frame(chat_frame, bg=BG_COLOR)
        input_frame.pack(fill=tk.X)
        
        self.user_input = tk.Entry(
            input_frame,
            width=70,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=FG_COLOR,
            font=(FONT_SIZE, FONT_FAMILY)
        )
        self.user_input.pack(side=tk.LEFT, padx=(0, 5))
        self.user_input.bind("<Return>", lambda e: self._on_send())
        
        send_btn = tk.Button(
            input_frame,
            text="Send",
            command=self._on_send,
            bg=ACCENT_COLOR,
            fg=BG_COLOR,
            font=BUTTON_FONT,
            cursor="hand2"
        )
        send_btn.pack(side=tk.LEFT)
        
        # Model info label
        self.model_label = tk.Label(
            self.root,
            text="Model: Not connected",
            fg=FG_COLOR,
            bg=BG_COLOR,
            font=(FONT_FAMILY, 9)
        )
        self.model_label.pack(pady=(3, 0))
    
    def _append_message(self, role: str, text: str) -> None:
        """Append a message to the chat display.
        
        Args:
            role: Message role ('You' or 'LM Studio')
            text: Message text
        """
        self.messages_text.config(state=tk.NORMAL)
        prefix = f"[{role}] " if role == "You" else "> "
        self.messages_text.insert(tk.END, f"{prefix}{text}\n\n")
        self.messages_text.see(tk.END)
        self.messages_text.config(state=tk.DISABLED)
    
    def _log(self, text: str) -> None:
        """Append text to the chat display as a system log.
        
        Args:
            text: Log text
        """
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.insert(tk.END, f"[System] {text}\n")
        self.messages_text.see(tk.END)
        self.messages_text.config(state=tk.DISABLED)
    
    def _on_connect(self) -> None:
        """Handle connect button click."""
        # Update client with current values
        host = self.host_var.get().strip()
        port_str = self.port_var.get().strip()
        
        if not port_str.isdigit():
            self._log("Error: Port must be a number.")
            return
        
        port = int(port_str)
        self.client.hostname = host
        self.client.port = port
        self.client.base_url = f"http://{host}:{port}/v1"
        self.client.chat_url = f"{self.client.base_url}/chat/completions"
        
        # Connect in a background thread to not block GUI
        self.connect_btn.config(state=tk.DISABLED, text="Connecting...")
        Thread(target=self._connect_worker, args=(host, port), daemon=True).start()
    
    def _connect_worker(self, host: str, port: int) -> None:
        """Worker thread for connecting to LM Studio.
        
        Args:
            host: LM Studio hostname
            port: LM Studio port
        """
        success = self.client.connect()
        
        if success:
            models = self.client.get_models()
            model_name = models[0] if models else "unknown"
            
            self.root.after(0, self._on_connected, True, model_name)
        else:
            self.root.after(0, self._on_connected, False, "")
    
    def _on_connected(self, success: bool, model: str) -> None:
        """Handle connection result (called in GUI thread).
        
        Args:
            success: Whether connection was successful
            model: Model name if connected
        """
        self.connect_btn.config(state=tk.NORMAL, text="Connect")
        
        if success:
            self.status_label.config(text="Status: Connected", fg=STATUS_CONNECTED)
            self.model_label.config(text=f"Model: {model}")
            self.config.lm_studio_hostname = self.client.hostname
            self.config.lm_studio_port = self.client.port
            self.config.save()
            self._log(f"Connected to LM Studio at {self.client.hostname}:{self.client.port}")
            self._append_message("System", f"Connected! Using model: {model}")
        else:
            self.status_label.config(text="Status: Connection Failed", fg=ERROR_COLOR)
            self.model_label.config(text="Model: Not connected")
            self._log(f"Failed to connect to {self.client.hostname}:{self.client.port}")
    
    def _on_send(self) -> None:
        """Handle send button click."""
        message = self.user_input.get().strip()
        if not message:
            return
        
        # Clear input
        self.user_input.delete(0, tk.END)
        
        # Display user message
        self._append_message("You", message)
        
        # Add to chat history
        self.chat_history.append({"role": "user", "content": message})
        
        # Get response in background thread
        self.user_input.config(state=tk.DISABLED)
        Thread(target=self._get_response, args=(message,), daemon=True).start()
    
    def _get_response(self, user_message: str) -> None:
        """Get response from LM Studio in background thread.
        
        Args:
            user_message: The user's message
        """
        try:
            self._log("Waiting for response...")
            
            response = self.client.chat(
                messages=self.chat_history,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            # Extract response text
            choices = response.get("choices", [])
            if choices:
                assistant_message = choices[0].get("message", {}).get("content", "")
            else:
                assistant_message = "(No response)"
            
            # Add to chat history
            self.chat_history.append({"role": "assistant", "content": assistant_message})
            
            # Update GUI
            self.root.after(0, self._on_response, assistant_message)
            
        except ConnectionError as e:
            self.root.after(0, self._on_error, f"Connection error: {e}")
        except Exception as e:
            self.root.after(0, self._on_error, f"Error: {e}")
    
    def _on_response(self, response: str) -> None:
        """Handle received response (called in GUI thread).
        
        Args:
            response: Assistant's response text
        """
        self._append_message("LM Studio", response)
        self.user_input.config(state=tk.NORMAL)
    
    def _on_error(self, error: str) -> None:
        """Handle error (called in GUI thread).
        
        Args:
            error: Error message
        """
        self._log(error)
        self.user_input.config(state=tk.NORMAL)