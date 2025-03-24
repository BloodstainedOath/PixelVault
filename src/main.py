#!/usr/bin/env python3
import sys
import os
import gi

# Add parent directory to path for imports to work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from src.widgets.main_window import MainWindow
from src.widgets.preferences import PreferencesWindow

class PixelVaultApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.pixelvault",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        
        self.create_action("quit", self.on_quit_action)
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action)
        
        self.set_accels_for_action("app.quit", ["<primary>q"])
        self.set_accels_for_action("app.preferences", ["<primary>comma"])
        self.set_accels_for_action("win.refresh", ["<primary>r"])
        self.set_accels_for_action("win.search", ["<primary>f"])
        self.set_accels_for_action("win.favorite", ["<primary>d"])
        self.set_accels_for_action("win.fullscreen", ["F11"])
        
    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()
        
    def on_quit_action(self, action, param):
        self.quit()
        
    def on_about_action(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="PixelVault",
            application_icon="image-viewer",
            developer_name="PixelVault Team",
            version="1.0.0",
            developers=["PixelVault Team"],
            copyright="© 2023 PixelVault Team",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/pixelvault",
            issue_url="https://github.com/pixelvault/issues"
        )
        about.present()
        
    def on_preferences_action(self, action, param):
        preferences_window = PreferencesWindow(transient_for=self.props.active_window)
        preferences_window.present()
        
    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

def main():
    app = PixelVaultApplication()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main()) 