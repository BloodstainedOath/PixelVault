#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

class TestWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("GTK4 Test")
        self.set_default_size(300, 200)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        
        label = Gtk.Label(label="GTK4 is working!")
        button = Gtk.Button(label="Close")
        button.connect("clicked", lambda x: app.quit())
        
        box.append(label)
        box.append(button)
        self.set_child(box)

class TestApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.gtk4test")
        
    def do_activate(self):
        win = TestWindow(application=self)
        win.present()

app = TestApp()
app.run(None) 