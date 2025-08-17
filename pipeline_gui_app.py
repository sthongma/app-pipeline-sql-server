# Standard library imports
import logging
import os

# Third-party imports
try:
    import customtkinter as ctk
except ImportError as e:
    raise SystemExit(
        "The 'customtkinter' library is required for the UI.\n"
        "Install with: pip install customtkinter"
    ) from e

# Local imports
from ui.login_window import LoginWindow
from utils.logger import setup_logging

def main():
    # Set working directory to the location of this file
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Set appearance mode and theme (minimal tone)
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("dark-blue")
    # Adjust default scaling for balance
    try:
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
    except Exception:
        pass
    
    # Set up standard logging
    setup_logging(level=logging.INFO)
    
    # Create login window
    login_window = LoginWindow()
    
    login_window.mainloop()

if __name__ == '__main__':
    main()