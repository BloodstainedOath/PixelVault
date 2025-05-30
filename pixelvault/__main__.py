#!/usr/bin/env python3
"""Main entry point for PixelVault."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from .ui.main_window import MainWindow


def main():
    """Run the application."""
    window = MainWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
