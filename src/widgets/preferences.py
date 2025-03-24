import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Gio, GLib

class PreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title("Preferences")
        self.set_default_size(600, 400)
        
        # Create appearance page
        appearance_page = Adw.PreferencesPage()
        appearance_page.set_title("Appearance")
        appearance_page.set_icon_name("applications-graphics-symbolic")
        
        # Theme group
        theme_group = Adw.PreferencesGroup()
        theme_group.set_title("Theme")
        
        # Theme mode
        theme_row = Adw.ActionRow()
        theme_row.set_title("Theme Mode")
        theme_row.set_subtitle("Choose between light and dark theme")
        
        theme_switch = Gtk.Switch()
        theme_switch.set_valign(Gtk.Align.CENTER)
        theme_switch.set_active(self._is_dark_mode_active())
        theme_switch.connect("notify::active", self._on_theme_switched)
        
        theme_row.add_suffix(theme_switch)
        theme_group.add(theme_row)
        
        # Grid view group
        grid_group = Adw.PreferencesGroup()
        grid_group.set_title("Grid View")
        
        # Columns adjustment
        columns_row = Adw.ActionRow()
        columns_row.set_title("Number of Columns")
        
        columns_adjustment = Gtk.Adjustment(
            value=4, lower=2, upper=8, step_increment=1
        )
        columns_spin = Gtk.SpinButton()
        columns_spin.set_adjustment(columns_adjustment)
        columns_spin.set_valign(Gtk.Align.CENTER)
        
        columns_row.add_suffix(columns_spin)
        grid_group.add(columns_row)
        
        # Image size adjustment
        size_row = Adw.ActionRow()
        size_row.set_title("Thumbnail Size")
        
        size_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 100, 300, 25
        )
        size_scale.set_size_request(200, -1)
        size_scale.set_value(200)
        size_scale.set_valign(Gtk.Align.CENTER)
        size_scale.set_draw_value(True)
        size_scale.add_mark(100, Gtk.PositionType.BOTTOM, "Small")
        size_scale.add_mark(200, Gtk.PositionType.BOTTOM, "Medium")
        size_scale.add_mark(300, Gtk.PositionType.BOTTOM, "Large")
        
        size_row.add_suffix(size_scale)
        grid_group.add(size_row)
        
        # Add groups to appearance page
        appearance_page.add(theme_group)
        appearance_page.add(grid_group)
        
        # Create network page
        network_page = Adw.PreferencesPage()
        network_page.set_title("Network")
        network_page.set_icon_name("network-wireless-symbolic")
        
        # Cache group
        cache_group = Adw.PreferencesGroup()
        cache_group.set_title("Cache")
        
        # Cache size
        cache_size_row = Adw.ActionRow()
        cache_size_row.set_title("Cache Size")
        cache_size_row.set_subtitle("Maximum size for the image cache")
        
        cache_adjustment = Gtk.Adjustment(
            value=500, lower=100, upper=2000, step_increment=100
        )
        cache_spin = Gtk.SpinButton()
        cache_spin.set_adjustment(cache_adjustment)
        cache_spin.set_valign(Gtk.Align.CENTER)
        
        cache_size_label = Gtk.Label(label="MB")
        cache_size_label.set_margin_start(6)
        
        cache_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        cache_box.append(cache_spin)
        cache_box.append(cache_size_label)
        
        cache_size_row.add_suffix(cache_box)
        cache_group.add(cache_size_row)
        
        # Clear cache button
        clear_cache_row = Adw.ActionRow()
        clear_cache_row.set_title("Clear Image Cache")
        clear_cache_row.set_subtitle("Delete all cached images")
        
        clear_button = Gtk.Button(label="Clear Cache")
        clear_button.add_css_class("destructive-action")
        clear_button.set_valign(Gtk.Align.CENTER)
        
        clear_cache_row.add_suffix(clear_button)
        cache_group.add(clear_cache_row)
        
        # Add groups to network page
        network_page.add(cache_group)
        
        # Add pages to window
        self.add(appearance_page)
        self.add(network_page)
        
        # Connect signals for various settings
        columns_spin.connect("value-changed", self._on_columns_changed)
        size_scale.connect("value-changed", self._on_thumbnail_size_changed)
        cache_spin.connect("value-changed", self._on_cache_size_changed)
        clear_button.connect("clicked", self._on_clear_cache_clicked)
    
    def _is_dark_mode_active(self):
        style_manager = Adw.StyleManager.get_default()
        return style_manager.get_dark()
    
    def _on_theme_switched(self, switch, pspec):
        style_manager = Adw.StyleManager.get_default()
        if switch.get_active():
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    
    def _on_columns_changed(self, spin_button):
        # In a real app, we would save this setting
        pass
    
    def _on_thumbnail_size_changed(self, scale):
        # In a real app, we would save this setting
        pass
    
    def _on_cache_size_changed(self, spin_button):
        # In a real app, we would save this setting
        pass
    
    def _on_clear_cache_clicked(self, button):
        # In a real app, we would clear the cache directory
        # Also, show a confirmation dialog before doing so
        dialog = Adw.MessageDialog.new(
            self,
            "Clear Cache",
            "Are you sure you want to clear the image cache? This cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear Cache")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_clear_cache_confirmed)
        dialog.present()
    
    def _on_clear_cache_confirmed(self, dialog, response):
        if response == "clear":
            # In a real app, we would clear the cache here
            pass 