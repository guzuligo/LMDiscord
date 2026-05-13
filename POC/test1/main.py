"""
Application Entry Point - Launches the Flask web application.

Run this file to start the LM Studio Chat POC web interface.

Usage:
    python main.py
    
The web interface will be available at: http://localhost:5000
"""

import sys
from pathlib import Path

# Add the POC/test1 directory to the path so src can be imported
sys.path.insert(0, str(Path(__file__).parent))

from src.app import app


def main():
    """Main entry point."""
    print("=" * 50)
    print("LM Studio Chat POC")
    print("=" * 50)
    print("\nStarting web server...")
    print("Open your browser and go to: http://localhost:5000\n")
    
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()