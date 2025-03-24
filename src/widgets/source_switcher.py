import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Gdk

class SourceSwitcher(Gtk.Box):
    __gsignals__ = {
        'source-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        # Source definitions with more specific icons
        self.sources = [
            {
                "id": "wallhaven", 
                "name": "Wallhaven", 
                "icon": "photo-album-symbolic",
                "tooltip": "Wallhaven - General wallpapers and art from wallhaven.cc"
            },
            {
                "id": "waifu_im", 
                "name": "Waifu.im", 
                "icon": "emblem-favorite-symbolic",
                "tooltip": "Waifu.im - Anime-style character images"
            },
            {
                "id": "waifu_pics", 
                "name": "Waifu.pics", 
                "icon": "weather-clear-night-symbolic",
                "tooltip": "Waifu.pics - Curated anime illustrations"
            },
            {
                "id": "nekos_moe", 
                "name": "Nekos.moe", 
                "icon": "face-smile-symbolic",
                "tooltip": "Nekos.moe - Community-driven anime character images"
            }
        ]
        
        self.add_css_class("source-switcher")
        self.set_hexpand(True)
        
        # Create a button box with a more modern look
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.button_box.set_halign(Gtk.Align.CENTER)
        self.button_box.set_hexpand(True)
        self.button_box.add_css_class("linked")
        self.button_box.add_css_class("source-buttons")
        
        # Track active button for styling
        self.active_button = None
        self.buttons = {}
        
        # Create buttons for each source
        for source in self.sources:
            button = self._create_source_button(source)
            self.button_box.append(button)
            self.buttons[source["id"]] = button
            
        # Add the button box to the source switcher
        self.append(self.button_box)
        
        # Set default active source to the first one
        self._set_active_button(self.sources[0]["id"])
    
    def _create_source_button(self, source):
        # Create a button with icon and label
        button = Gtk.Button()
        button.set_has_frame(True)
        
        # Add tooltip
        button.set_tooltip_text(source["tooltip"])
        
        # Create box for icon and label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        
        # Add icon
        icon = Gtk.Image.new_from_icon_name(source["icon"])
        
        # Add label
        label = Gtk.Label(label=source["name"])
        
        # Add to box
        box.append(icon)
        box.append(label)
        
        # Set as button child
        button.set_child(box)
        
        # Connect click handler
        button.connect("clicked", self._on_button_clicked, source["id"])
        
        # Store source ID
        button.source_id = source["id"]
        
        return button
    
    def _on_button_clicked(self, button, source_id):
        # Set as active
        self._set_active_button(source_id)
        
        # Emit signal
        self.emit("source-changed", source_id)
    
    def _set_active_button(self, source_id):
        # Remove active class from previous button
        if self.active_button and self.active_button in self.buttons.values():
            self.active_button.remove_css_class("suggested-action")
        
        # Set new active button
        if source_id in self.buttons:
            self.active_button = self.buttons[source_id]
            self.active_button.add_css_class("suggested-action")
    
    def get_active_source(self):
        if self.active_button:
            return self.active_button.source_id
        return self.sources[0]["id"]
    
    def set_active_source(self, source_id):
        """Set the active source programmatically."""
        if source_id in self.buttons:
            # Set as active
            self._set_active_button(source_id)
            
            # Emit signal
            self.emit("source-changed", source_id)
            return True
        return False