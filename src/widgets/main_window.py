import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from src.widgets.image_grid import ImageGrid
from src.widgets.source_switcher import SourceSwitcher
from src.widgets.sidebar import Sidebar
from src.widgets.image_view_overlay import ImageViewOverlay
from src.widgets.tag_filter import TagFilter
from src.widgets.settings_manager import SettingsManager

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize settings manager
        self.settings = SettingsManager()
        
        # Set window properties
        self.set_default_size(1200, 800)
        self.set_title("PixelVault")
        
        # Create action for toggling sidebar
        self.create_action("toggle_sidebar", self.on_toggle_sidebar_action)
        self.create_action("refresh", self.on_refresh_action)
        self.create_action("search", self.on_search_action)
        self.create_action("favorite", self.on_favorite_action)
        self.create_action("fullscreen", self.on_fullscreen_action)
        
        # Load auto caching setting
        self.auto_cache_enabled = self.settings.get("auto_cache")
        
        # Main layout
        self.main_layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        # Split pane with sidebar
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.sidebar = Sidebar()
        self.sidebar.connect("favorite-selected", self.on_favorite_selected)
        self.sidebar.connect("history-selected", self.on_history_selected)
        self.sidebar.connect("favorites-changed", self.on_favorites_changed)
        self.content_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Source switcher
        self.source_switcher = SourceSwitcher()
        self.source_switcher.connect("source-changed", self.on_source_changed)
        
        # Search bar
        self.search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_box.add_css_class("search-container")
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activated)
        
        self.refresh_button = Gtk.Button()
        self.refresh_button.set_icon_name("view-refresh-symbolic")
        self.refresh_button.set_tooltip_text("Refresh")
        self.refresh_button.connect("clicked", self.on_refresh_clicked)
        
        self.search_box.append(self.search_entry)
        self.search_box.append(self.refresh_button)
        
        # Tag filtering
        self.tag_filter = TagFilter()
        self.tag_filter.connect("tag-selected", self.on_tag_selected)
        
        # Header bar
        self.header = Adw.HeaderBar()
        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        
        self.header.pack_end(self.menu_button)
        
        # Toggle sidebar button
        self.sidebar_button = Gtk.ToggleButton()
        self.sidebar_button.set_icon_name("sidebar-show-symbolic")
        self.sidebar_button.set_tooltip_text("Toggle Sidebar")
        self.sidebar_button.set_active(True)
        self.sidebar_button.connect("toggled", self.on_sidebar_toggled)
        self.header.pack_start(self.sidebar_button)
        
        # Build menu
        self.build_menu()
        
        # Image grid
        self.image_grid = ImageGrid()
        self.image_grid.connect("image-clicked", self.on_image_clicked)
        
        # Image overlay view
        self.image_overlay = ImageViewOverlay(self)
        
        # Scrolled window for the grid
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_vexpand(True)
        self.scrolled_window.set_child(self.image_grid)
        self.scrolled_window.connect("edge-reached", self.on_edge_reached)
        
        # Add widgets to the content area
        self.toolbar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.toolbar_box.add_css_class("toolbar-container")
        self.toolbar_box.append(self.source_switcher)
        self.toolbar_box.append(self.search_box)
        self.toolbar_box.append(self.tag_filter)
        
        self.content_area.append(self.header)
        self.content_area.append(self.toolbar_box)
        self.content_area.append(self.scrolled_window)
        
        # Set up the paned container
        self.paned.set_start_child(self.sidebar)
        self.paned.set_end_child(self.content_area)
        self.paned.set_position(250)  # Initial sidebar width
        
        self.main_layout.append(self.paned)
        
        # Set window content using content property (for AdwApplicationWindow)
        self.set_content(self.main_layout)
        
        # Apply CSS
        self.apply_css()
        
        # Get initial images
        GLib.idle_add(self.load_initial_images)
        
        # Initialize search timeout ID
        self.search_timeout_id = None
        self.last_search_term = ""
    
    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("resources/css/style.css")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), 
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def load_initial_images(self):
        # Get the last active source from settings
        last_source = self.settings.get("last_source")
        
        # Activate the last source in the source switcher
        if last_source:
            self.source_switcher.set_active_source(last_source)
        else:
            self.image_grid.load_images_from_source(self.source_switcher.get_active_source())
        
        # Make sure image grid has the correct auto_cache setting
        self.image_grid.set_auto_cache(self.auto_cache_enabled)
        
        return False
    
    def build_menu(self):
        # Create menu model
        menu = Gio.Menu.new()
        
        # App section
        app_section = Gio.Menu.new()
        app_section.append("Preferences", "app.preferences")
        app_section.append("About PixelVault", "app.about")
        app_section.append("Quit", "app.quit")
        menu.append_section(None, app_section)
        
        # Cache section
        cache_section = Gio.Menu.new()
        cache_section.append("Enable Auto-Caching", "win.auto_cache")
        cache_section.append("Clear Cache", "win.clear_cache")
        menu.append_section("Cache", cache_section)
        
        # Theme section
        theme_section = Gio.Menu.new()
        theme_section.append("Light Theme", "win.theme::light")
        theme_section.append("Dark Theme", "win.theme::dark")
        menu.append_section("Theme", theme_section)
        
        # Set menu
        self.menu_button.set_menu_model(menu)
        
        # Theme action - load from settings
        theme_value = self.settings.get("theme", "dark")
        theme_action = Gio.SimpleAction.new_stateful(
            "theme", 
            GLib.VariantType.new("s"), 
            GLib.Variant.new_string(theme_value)
        )
        theme_action.connect("activate", self.on_theme_changed)
        self.add_action(theme_action)
        
        # Apply theme on startup
        style_manager = Adw.StyleManager.get_default()
        if theme_value == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        
        # Cache actions - load from settings
        self.auto_cache_action = Gio.SimpleAction.new_stateful(
            "auto_cache", 
            None,
            GLib.Variant.new_boolean(self.auto_cache_enabled)
        )
        self.auto_cache_action.connect("change-state", self.on_auto_cache_changed)
        self.add_action(self.auto_cache_action)
        
        clear_cache_action = Gio.SimpleAction.new("clear_cache", None)
        clear_cache_action.connect("activate", self.on_clear_cache)
        self.add_action(clear_cache_action)
    
    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
    
    def on_theme_changed(self, action, variant):
        theme = variant.get_string()
        action.set_state(variant)
        
        # Save theme setting
        self.settings.set("theme", theme)
        
        style_manager = Adw.StyleManager.get_default()
        if theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    
    def on_sidebar_toggled(self, button):
        self.sidebar.set_visible(button.get_active())
        if button.get_active():
            button.set_icon_name("sidebar-show-symbolic")
        else:
            button.set_icon_name("sidebar-hide-symbolic")
    
    def on_toggle_sidebar_action(self, action, param):
        self.sidebar_button.set_active(not self.sidebar_button.get_active())
    
    def on_refresh_action(self, action, param):
        self.on_refresh_clicked(None)
    
    def on_refresh_clicked(self, button):
        # Get the current source
        current_source = self.source_switcher.get_active_source()
        
        # Clear the search entry
        self.search_entry.set_text("")
        
        # Reset tag filter
        self.tag_filter.reset_selection()
        
        # Reload images
        self.image_grid.load_images_from_source(current_source)
    
    def on_search_action(self, action, param):
        self.search_entry.grab_focus()
    
    def _on_search_changed(self, entry):
        # Cancel any pending search
        if self.search_timeout_id:
            GLib.source_remove(self.search_timeout_id)
            self.search_timeout_id = None
            
        # Schedule a new search with a short delay (300ms)
        search_term = entry.get_text().strip()
        
        # Only search if the term is different from last search
        if search_term != self.last_search_term:
            self.search_timeout_id = GLib.timeout_add(300, self._perform_search, search_term)
    
    def _perform_search(self, search_term):
        self.search_timeout_id = None
        self.last_search_term = search_term
        
        # Log the search action
        print(f"Performing search for: '{search_term}'")
        
        # Apply the search filter to the grid
        self.image_grid.filter_images(search_term)
        return False  # Don't repeat the timeout
    
    def _on_search_activated(self, entry):
        # Force immediate search on Enter key
        if self.search_timeout_id:
            GLib.source_remove(self.search_timeout_id)
            self.search_timeout_id = None
            
        search_term = entry.get_text().strip()
        self._perform_search(search_term)
    
    def on_source_changed(self, source_switcher, source_name):
        print(f"Source changed to: {source_name}")
        
        # Save the selected source to settings
        self.settings.set("last_source", source_name)
        
        # Update the tag filter for the new source
        self.tag_filter.update_tags_for_source(source_name)
        
        # Clear search text when changing sources
        self.search_entry.set_text("")
        
        # Reset the UI state
        self.current_source = source_name
        
        # Add a delay before loading images to ensure clean switch
        GLib.timeout_add(500, self._delayed_load_images, source_name)
    
    def _delayed_load_images(self, source_name):
        # Make sure we're still on the same source
        if self.current_source == source_name:
            # Load images for the source
            self.image_grid.load_images_from_source(source_name)
        return False  # Don't repeat the timeout
    
    def on_tag_selected(self, tag_filter, tag):
        # Get the current source
        current_source = self.source_switcher.get_active_source()
        
        # Store the current tag
        current_tag = getattr(self, 'current_tag', None)
        self.current_tag = tag
        
        # Only filter if the tag actually changed
        if current_tag != tag:
            print(f"Tag changed from '{current_tag}' to '{tag}', applying filter")
            self.image_grid.filter_by_tag(tag, current_source)
        else:
            print(f"Tag unchanged ('{tag}'), not reapplying filter")
    
    def on_image_clicked(self, image_grid, image_data):
        self.image_overlay.show_image(image_data)
    
    def on_favorite_action(self, action, param):
        if self.image_overlay.is_visible():
            self.image_overlay.toggle_favorite()
    
    def on_edge_reached(self, scrolled_window, position):
        if position == Gtk.PositionType.BOTTOM:
            current_source = self.source_switcher.get_active_source()
            self.image_grid.load_more_images(current_source)
    
    def on_fullscreen_action(self, action, param):
        is_fullscreen = self.is_fullscreen()
        if is_fullscreen:
            self.unfullscreen()
        else:
            self.fullscreen()
    
    def on_auto_cache_changed(self, action, value):
        self.auto_cache_enabled = value.get_boolean()
        action.set_state(value)
        
        # Save auto-cache setting
        self.settings.set("auto_cache", self.auto_cache_enabled)
        
        # Update image grid
        self.image_grid.set_auto_cache(self.auto_cache_enabled)
    
    def on_clear_cache(self, action, param):
        dialog = Adw.MessageDialog.new(
            self,
            "Clear Image Cache?",
            "This will delete all cached images. This won't affect your downloaded or favorited images."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear Cache")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_clear_cache_response)
        dialog.present()
    
    def _on_clear_cache_response(self, dialog, response):
        if response == "clear":
            self.image_grid.clear_cache()
    
    def on_favorite_selected(self, sidebar, image_data):
        """Handle when a favorite image is selected from the sidebar"""
        if image_data:
            # Show the selected image
            self.image_overlay.show_image(image_data)
    
    def on_history_selected(self, sidebar, image_data):
        """Handle when a history item is selected from the sidebar"""
        if image_data:
            # Show the selected image
            self.image_overlay.show_image(image_data)
    
    def on_favorites_changed(self, sidebar):
        """Handle when favorites are changed in the sidebar"""
        # Update the favorite status in the image overlay if it's visible
        if self.image_overlay.is_visible() and self.image_overlay.current_image_data:
            # Check if the current image is in favorites
            is_favorite = sidebar.is_in_favorites(self.image_overlay.current_image_data)
            
            # Update the favorite button state without triggering the toggle event
            with self.image_overlay.favorite_button.freeze_notify():
                self.image_overlay.favorite_button.set_active(is_favorite) 