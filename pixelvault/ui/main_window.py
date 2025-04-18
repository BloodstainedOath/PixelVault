import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, Gio, GLib
import os
import threading
import requests
from io import BytesIO
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image, PngImagePlugin

from ..api import SourceManager, ImageSource
from ..api.wallhaven import Category as WallhavenCategory, Purity as WallhavenPurity, Sorting as WallhavenSorting
from ..settings import settings
from .settings_dialog import SettingsDialog

class MainWindow(Gtk.Window):
    """Main window for the PixelVault application."""
    
    def __init__(self):
        """Initialize the main window."""
        Gtk.Window.__init__(self, title="PixelVault")
        self.set_default_size(1000, 700)
        self.connect("destroy", Gtk.main_quit)
        
        # Initialize API source manager
        self.source_manager = SourceManager()
        
        # Current images list
        self.images = []
        
        # Pagination state
        self.current_page = 1
        self.has_next_page = True
        self.is_loading = False
        
        # Search query
        self.search_query = ""
        
        # Additional filters for Wallhaven
        self.wallhaven_category = WallhavenCategory.from_list(settings.get("wallhaven_categories", ["general", "anime", "people"]))
        self.wallhaven_purity = WallhavenPurity.from_list(settings.get("wallhaven_purity", ["sfw"]))
        self.wallhaven_sorting = WallhavenSorting(settings.get("wallhaven_sorting", "date_added"))
        self.wallhaven_method = "latest"  # Default method for sorting
        
        # Create UI elements
        self._create_header_bar()
        self._create_layout()
        
        # Set initial UI state
        self._initialize_ui_state()
        
        # Load initial images
        self._load_images(reset=True)
    
    def _initialize_ui_state(self):
        """Initialize UI state variables."""
        # Initialize source manager
        self.source_manager = SourceManager()
        
        # Initialize wallhaven specific settings
        self.wallhaven_category = WallhavenCategory.from_list(settings.get("wallhaven_categories", ["general", "anime", "people"]))
        self.wallhaven_purity = WallhavenPurity.from_list(settings.get("wallhaven_purity", ["sfw"]))
        self.wallhaven_sorting = WallhavenSorting(settings.get("wallhaven_sorting", "date_added"))
        self.wallhaven_method = "latest"  # Default method for sorting
        
        # Initialize search state
        self.search_query = ""
        self.selected_tags = []
        self.selected_purity = ["sfw"]  # Default to SFW content
        
        # Initialize pagination state
        self.current_page = 1
        self.has_next_page = True
        self.is_loading = False
        
        # Initialize images list
        self.images = []
        
        # Set search bar visibility based on current source
        if self.source_manager.current_source == ImageSource.WALLHAVEN:
            self.wallhaven_search_box.show_all()
            self.sort_combo.set_sensitive(True)
        else:
            self.wallhaven_search_box.hide()
            self.sort_combo.set_sensitive(False)
    
    def _create_header_bar(self):
        """Create the header bar."""
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "PixelVault"
        
        # Create source selector
        source_store = Gtk.ListStore(str)
        source_store.append(["Wallhaven"])
        source_store.append(["Waifu.im"])
        source_store.append(["Waifu.pics"])
        
        self.source_combo = Gtk.ComboBox.new_with_model(source_store)
        renderer_text = Gtk.CellRendererText()
        self.source_combo.pack_start(renderer_text, True)
        self.source_combo.add_attribute(renderer_text, "text", 0)
        self.source_combo.set_active(0)  # Set Wallhaven as default
        self.source_combo.connect("changed", self._on_source_changed)
        
        # Create settings button
        settings_button = Gtk.Button()
        settings_icon = Gio.ThemedIcon(name="preferences-system-symbolic")
        settings_image = Gtk.Image.new_from_gicon(settings_icon, Gtk.IconSize.BUTTON)
        settings_button.add(settings_image)
        settings_button.connect("clicked", self._on_settings_clicked)
        
        # Add widgets to header
        header.pack_start(self.source_combo)
        header.pack_end(settings_button)
        
        self.set_titlebar(header)
        
        # Wallhaven search bar
        self.wallhaven_search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.wallhaven_search_entry = Gtk.SearchEntry()
        self.wallhaven_search_entry.set_placeholder_text("Search Wallhaven...")
        self.wallhaven_search_entry.set_width_chars(20)
        self.wallhaven_search_entry.connect("activate", self._on_wallhaven_search_activated)
        
        search_button = Gtk.Button.new_with_label("Search")
        search_button.connect("clicked", self._on_wallhaven_search_clicked)
        
        clear_button = Gtk.Button.new_with_label("Clear")
        clear_button.connect("clicked", self._on_wallhaven_clear_clicked)
        
        self.wallhaven_search_box.pack_start(self.wallhaven_search_entry, True, True, 0)
        self.wallhaven_search_box.pack_start(search_button, False, False, 0)
        self.wallhaven_search_box.pack_start(clear_button, False, False, 0)
        
        # Sort dropdown menu (for Wallhaven)
        sort_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.sort_combo = Gtk.ComboBoxText()
        self.sort_combo.append_text("Latest")
        self.sort_combo.append_text("Top")
        self.sort_combo.append_text("Random")
        self.sort_combo.set_active(0)  # Default to Latest
        self.sort_combo.connect("changed", self._on_sort_changed)
        self.sort_combo.set_sensitive(False)
        
        sort_box.pack_start(Gtk.Label.new("Sort:"), False, False, 0)
        sort_box.pack_start(self.sort_combo, False, False, 0)
        
        # Advanced Options button
        advanced_button = Gtk.Button.new_with_label("Advanced Options")
        advanced_button.connect("clicked", self._on_advanced_button_clicked)
        
        # Tag filter button
        tag_button = Gtk.Button.new_with_label("Select Tags")
        tag_button.connect("clicked", self._on_tag_button_clicked)
        
        # Refresh button
        refresh_button = Gtk.Button.new_with_label("Refresh Images")
        refresh_icon = Gio.ThemedIcon(name="view-refresh-symbolic")
        refresh_image = Gtk.Image.new_from_gicon(refresh_icon, Gtk.IconSize.BUTTON)
        refresh_button.set_image(refresh_image)
        refresh_button.connect("clicked", self._on_refresh_clicked)
        
        header.pack_start(self.wallhaven_search_box)
        header.pack_start(sort_box)
        header.pack_start(advanced_button)
        header.pack_start(tag_button)
        header.pack_end(refresh_button)
        
        # Initialize selected tags
        self.selected_tags = []
    
    def _create_layout(self):
        """Create the main layout."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)
        
        # Apply a modern dark theme if available
        screen = Gtk.Settings.get_default()
        if hasattr(screen, 'set_property'):
            screen.set_property("gtk-application-prefer-dark-theme", True)
        
        # Status bar with modern styling
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_margin_start(16)
        status_box.set_margin_end(16)
        status_box.set_margin_top(10)
        status_box.set_margin_bottom(10)
        
        self.status_label = Gtk.Label.new("Ready")
        self.status_label.set_markup("<span color='#888'>Ready</span>")
        status_box.pack_start(self.status_label, False, False, 0)
        
        # Add refresh hint with modern styling
        refresh_hint = Gtk.Label.new("Click refresh to see more images")
        refresh_hint.set_markup("<span color='#888'><i>Scroll down to load more images</i></span>")
        status_box.pack_end(refresh_hint, False, False, 0)
        
        main_box.pack_start(status_box, False, False, 0)
        
        # Add a separator for visual distinction
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_opacity(0.2)
        main_box.pack_start(separator, False, False, 0)
        
        # Scrolled window for the FlowBox
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        # Connect scroll event for infinite scrolling
        self.scrolled_window.get_vadjustment().connect("value-changed", self._on_scroll_changed)
        
        # FlowBox for displaying images with modern styling
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(3)  # Reduced from 4 to 3 for larger images
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_column_spacing(16)        # More generous spacing
        self.flowbox.set_row_spacing(16)           # More generous spacing
        self.flowbox.set_margin_start(16)
        self.flowbox.set_margin_end(16)
        self.flowbox.set_margin_top(16)
        self.flowbox.set_margin_bottom(16)
        self.flowbox.connect("child-activated", self._on_image_activated)
        
        # Set CSS styling for the flowbox
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            flowboxchild {
                border-radius: 8px;
                transition: all 200ms ease;
                background-color: alpha(#000, 0.0);
            }
            flowboxchild:hover {
                background-color: alpha(#fff, 0.05);
                box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            }
            flowboxchild:selected {
                background-color: alpha(#fff, 0.1);
                box-shadow: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
            }
        """)
        context = self.flowbox.get_style_context()
        context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.scrolled_window.add(self.flowbox)
        main_box.pack_start(self.scrolled_window, True, True, 0)
        
        # Loading indicator at the bottom with modern styling
        self.loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.loading_box.set_margin_start(16)
        self.loading_box.set_margin_end(16)
        self.loading_box.set_margin_top(10)
        self.loading_box.set_margin_bottom(10)
        
        self.loading_spinner = Gtk.Spinner()
        self.loading_label = Gtk.Label.new("Loading more images...")
        self.loading_label.set_markup("<span color='#888'>Loading more images...</span>")
        
        self.loading_box.pack_start(self.loading_spinner, False, False, 0)
        self.loading_box.pack_start(self.loading_label, False, False, 0)
        
        main_box.pack_start(self.loading_box, False, False, 0)
        
        # Hide loading indicator initially
        self.loading_box.hide()
    
    def _on_scroll_changed(self, adjustment):
        """Handle scroll events to implement infinite scrolling.
        
        Args:
            adjustment: The value adjustment that triggered the event
        """
        # If already loading more images, do nothing
        if self.is_loading:
            return
            
        # Check if we've scrolled near the bottom
        max_value = adjustment.get_upper() - adjustment.get_page_size()
        current_value = adjustment.get_value()
        
        # If we're near the bottom (within 200px) and there are more pages
        if current_value > max_value - 200 and self.has_next_page:
            self._load_more_images()
    
    def _load_more_images(self):
        """Load the next page of images."""
        # Show loading indicator
        self.loading_spinner.start()
        self.loading_box.show_all()
        
        # Set loading flag
        self.is_loading = True
        
        # Increment page number
        self.current_page += 1
        
        # Fetch next page in a background thread
        thread = threading.Thread(target=self._fetch_images, args=(False,))
        thread.daemon = True
        thread.start()
    
    def _on_source_changed(self, combo):
        """Handle source change event.
        
        Args:
            combo: The ComboBox widget
        """
        # Get the selected source
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            source_text = model[tree_iter][0]
            print(f"Selected source: {source_text}")
            
            # Map to enum
            if source_text == "Wallhaven":
                self.source_manager.set_source(ImageSource.WALLHAVEN)
                self.wallhaven_search_box.show_all()  # Show search bar for Wallhaven
                # Show sort options for Wallhaven
                self.sort_combo.set_sensitive(True)
            elif source_text == "Waifu.im":
                self.source_manager.set_source(ImageSource.WAIFUIM)
                self.wallhaven_search_box.hide()  # Hide search bar for other sources
                # Hide sort options for Waifu.im
                self.sort_combo.set_sensitive(False)
            elif source_text == "Waifu.pics":
                print("Setting source to Waifu.pics")
                self.source_manager.set_source(ImageSource.WAIFUPICS)
                self.wallhaven_search_box.hide()  # Hide search bar for Waifu.pics
                # Hide sort options for Waifu.pics
                self.sort_combo.set_sensitive(False)
            
            # Clear selected tags when changing source
            self.selected_tags = []
            
            # Clear search query when changing source
            self.search_query = ""
            self.wallhaven_search_entry.set_text("")
            
            # Reset pagination
            self.current_page = 1
            
            # Clear the current flowbox
            for child in self.flowbox.get_children():
                self.flowbox.remove(child)
            
            # Load images for the new source
            self._load_images(reset=True)
    
    def _on_advanced_button_clicked(self, button):
        """Handle advanced options button click.
        
        Args:
            button: The Button widget
        """
        # Create a dialog for advanced options
        dialog = Gtk.Dialog(
            title="Advanced Options",
            parent=self,
            flags=0,
            buttons=(
                "Cancel", Gtk.ResponseType.CANCEL,
                "Apply", Gtk.ResponseType.OK
            )
        )
        dialog.set_default_size(400, 300)
        
        # Get available features for the current source
        features = self.source_manager.get_source_features()
        
        # Create content area
        content_area = dialog.get_content_area()
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        content_area.set_spacing(10)
        
        # Create options based on available features
        if features.get("categories", False):
            # Add category selection for Wallhaven
            category_frame = Gtk.Frame(label="Categories")
            category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            category_box.set_margin_top(10)
            category_box.set_margin_bottom(10)
            category_box.set_margin_start(10)
            category_box.set_margin_end(10)
            
            # Category checkboxes
            self.general_check = Gtk.CheckButton.new_with_label("General")
            self.general_check.set_active(self.wallhaven_category.value[0] == "1")
            
            self.anime_check = Gtk.CheckButton.new_with_label("Anime")
            self.anime_check.set_active(self.wallhaven_category.value[1] == "1")
            
            self.people_check = Gtk.CheckButton.new_with_label("People")
            self.people_check.set_active(self.wallhaven_category.value[2] == "1")
            
            category_box.pack_start(self.general_check, False, False, 0)
            category_box.pack_start(self.anime_check, False, False, 0)
            category_box.pack_start(self.people_check, False, False, 0)
            
            category_frame.add(category_box)
            content_area.pack_start(category_frame, False, False, 0)
        
        if features.get("purity_levels", False):
            # Add purity selection for Wallhaven
            purity_frame = Gtk.Frame(label="Content Filter")
            purity_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            purity_box.set_margin_top(10)
            purity_box.set_margin_bottom(10)
            purity_box.set_margin_start(10)
            purity_box.set_margin_end(10)
            
            # Purity checkboxes
            self.sfw_check = Gtk.CheckButton.new_with_label("Safe For Work")
            self.sfw_check.set_active(self.wallhaven_purity.value[0] == "1")
            
            self.sketchy_check = Gtk.CheckButton.new_with_label("Sketchy")
            self.sketchy_check.set_active(self.wallhaven_purity.value[1] == "1")
            
            # Check if API key is needed for Sketchy content
            has_api_key = self.source_manager.wallhaven_api_key != ""
            if not has_api_key:
                self.sketchy_check.set_tooltip_text("API key required for Sketchy content")
            
            self.nsfw_check = Gtk.CheckButton.new_with_label("NSFW")
            self.nsfw_check.set_active(self.wallhaven_purity.value[2] == "1")
            
            # Connect handlers to show warnings when trying to deselect all options
            self.sfw_check.connect("toggled", self._on_purity_check_toggled)
            self.sketchy_check.connect("toggled", self._on_purity_check_toggled)
            self.nsfw_check.connect("toggled", self._on_purity_check_toggled)
            
            # Check if API key is needed for NSFW content
            if not has_api_key:
                self.nsfw_check.set_tooltip_text("API key required for NSFW content")
            
            # Add API key warning if needed
            if self.source_manager.current_source == ImageSource.WALLHAVEN and not has_api_key:
                api_key_warning = Gtk.Label()
                api_key_warning.set_markup(
                    "<span foreground='red'>⚠️ API key required for Sketchy/NSFW content</span>"
                )
                api_key_warning.set_line_wrap(True)
                api_key_warning.set_xalign(0)
                api_key_warning.set_margin_top(5)
                api_key_warning.set_margin_bottom(5)
                
                # Add button to open settings
                settings_button = Gtk.Button.new_with_label("Add API Key")
                settings_button.connect("clicked", self._on_api_key_button_clicked, dialog)
                
                api_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                api_box.pack_start(api_key_warning, True, True, 0)
                api_box.pack_start(settings_button, False, False, 0)
                
                purity_box.pack_start(self.sfw_check, False, False, 0)
                purity_box.pack_start(self.sketchy_check, False, False, 0)
                purity_box.pack_start(self.nsfw_check, False, False, 0)
                purity_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
                purity_box.pack_start(api_box, False, False, 0)
            else:
                purity_box.pack_start(self.sfw_check, False, False, 0)
                purity_box.pack_start(self.sketchy_check, False, False, 0)
                purity_box.pack_start(self.nsfw_check, False, False, 0)
            
            purity_frame.add(purity_box)
            content_area.pack_start(purity_frame, False, False, 0)
        
        if features.get("sorting_options", []):
            # Add sorting options
            sorting_frame = Gtk.Frame(label="Sorting")
            sorting_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            sorting_box.set_margin_top(10)
            sorting_box.set_margin_bottom(10)
            sorting_box.set_margin_start(10)
            sorting_box.set_margin_end(10)
            
            # Sorting combo box
            sorting_options = features.get("sorting_options", [])
            self.sorting_combo = Gtk.ComboBoxText()
            
            for option in sorting_options:
                self.sorting_combo.append_text(option["name"])
            
            # Set active sorting option
            current_sorting = self.wallhaven_sorting.value
            active_index = 0  # default to latest
            for i, option in enumerate(sorting_options):
                if option["id"] == current_sorting:
                    active_index = i
                    break
            
            self.sorting_combo.set_active(active_index)
            
            sorting_box.pack_start(self.sorting_combo, False, False, 0)
            sorting_frame.add(sorting_box)
            content_area.pack_start(sorting_frame, False, False, 0)
        
        # Show the dialog and handle response
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Apply settings
            if features.get("categories", False):
                general = "1" if self.general_check.get_active() else "0"
                anime = "1" if self.anime_check.get_active() else "0"
                people = "1" if self.people_check.get_active() else "0"
                
                # Make sure at least one category is selected
                if general == "0" and anime == "0" and people == "0":
                    general = "1"  # Default to general if none selected
                
                category_value = f"{general}{anime}{people}"
                
                # Set the corresponding enum value
                if category_value == "100":
                    self.wallhaven_category = WallhavenCategory.GENERAL
                elif category_value == "010":
                    self.wallhaven_category = WallhavenCategory.ANIME
                elif category_value == "001":
                    self.wallhaven_category = WallhavenCategory.PEOPLE
                elif category_value == "110":
                    self.wallhaven_category = WallhavenCategory.GENERAL_ANIME
                elif category_value == "101":
                    self.wallhaven_category = WallhavenCategory.GENERAL_PEOPLE
                elif category_value == "011":
                    self.wallhaven_category = WallhavenCategory.ANIME_PEOPLE
                else:
                    self.wallhaven_category = WallhavenCategory.ALL
            
            if features.get("purity_levels", False):
                sfw = "1" if self.sfw_check.get_active() else "0"
                sketchy = "1" if self.sketchy_check.get_active() else "0"
                nsfw = "1" if self.nsfw_check.get_active() else "0"
                
                # Make sure at least one purity level is selected
                if sfw == "0" and sketchy == "0" and nsfw == "0":
                    sfw = "1"  # Default to SFW if none selected
                
                purity_value = f"{sfw}{sketchy}{nsfw}"
                
                # Set the corresponding enum value based on the combination
                if purity_value == "100":
                    self.wallhaven_purity = WallhavenPurity.SFW
                elif purity_value == "010":
                    self.wallhaven_purity = WallhavenPurity.SKETCHY
                elif purity_value == "001":
                    self.wallhaven_purity = WallhavenPurity.NSFW
                elif purity_value == "110":
                    self.wallhaven_purity = WallhavenPurity.SFW_SKETCHY
                elif purity_value == "101":
                    self.wallhaven_purity = WallhavenPurity.SFW_NSFW
                elif purity_value == "011":
                    self.wallhaven_purity = WallhavenPurity.SKETCHY_NSFW
                elif purity_value == "111":
                    self.wallhaven_purity = WallhavenPurity.ALL
                else:
                    # This should never happen, but as a fallback
                    self.wallhaven_purity = WallhavenPurity.SFW
                
                print(f"Selected purity level: {purity_value} -> {self.wallhaven_purity.name}")
                
                # Show warning if NSFW/Sketchy selected without API key
                has_api_key = self.source_manager.wallhaven_api_key != ""
                if (sketchy == "1" or nsfw == "1") and not has_api_key:
                    dialog = Gtk.MessageDialog(
                        transient_for=self,
                        flags=0,
                        message_type=Gtk.MessageType.WARNING,
                        buttons=Gtk.ButtonsType.OK,
                        text="API Key Required"
                    )
                    dialog.format_secondary_text(
                        "You've selected Sketchy or NSFW content without having a Wallhaven API key set.\n\n"
                        "Your selection will be saved, but you may not see any results until you add an API key."
                    )
                    dialog.run()
                    dialog.destroy()
            
            if features.get("sorting_options", []):
                active_index = self.sorting_combo.get_active()
                sorting_options = features.get("sorting_options", [])
                
                if 0 <= active_index < len(sorting_options):
                    sorting_id = sorting_options[active_index]["id"]
                    
                    # Set the corresponding enum value
                    if sorting_id == "latest":
                        self.wallhaven_sorting = WallhavenSorting.DATE_ADDED
                    elif sorting_id == "toplist":
                        self.wallhaven_sorting = WallhavenSorting.TOPLIST
                    elif sorting_id == "random":
                        self.wallhaven_sorting = WallhavenSorting.RANDOM
                    elif sorting_id == "views":
                        self.wallhaven_sorting = WallhavenSorting.VIEWS
                    elif sorting_id == "favorites":
                        self.wallhaven_sorting = WallhavenSorting.FAVORITES
                    elif sorting_id == "relevance":
                        self.wallhaven_sorting = WallhavenSorting.RELEVANCE
            
            # Reset and load images with new settings
            self._load_images(reset=True)
        
        dialog.destroy()
    
    def _on_tag_button_clicked(self, button):
        """Handle tag selection button click.
        
        Args:
            button: The Button widget
        """
        # Create dialog for tag selection
        dialog = Gtk.Dialog(
            title="Select Tags",
            parent=self,
            flags=0,
            buttons=(
                "Cancel", Gtk.ResponseType.CANCEL,
                "Apply", Gtk.ResponseType.OK
            )
        )
        dialog.set_default_size(400, 400)
        
        # Get available tags for the current source
        available_tags = self.source_manager.get_available_tags()
        
        # Create scrolled window for the tag list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        # Create a list box for tags
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        
        # Create a dictionary to store references to check buttons
        check_buttons = {}
        
        # Group tags by category
        categories = {}
        for tag in available_tags:
            category = tag.get("category", "other")
            if category not in categories:
                categories[category] = []
            categories[category].append(tag)
        
        # Add tags to the list box, grouped by category
        for category, tags in categories.items():
            # Add category header
            category_label = Gtk.Label()
            category_label.set_markup(f"<b>{category.upper()}</b>")
            category_label.set_halign(Gtk.Align.START)
            category_label.set_margin_top(10)
            category_label.set_margin_bottom(5)
            category_label.set_margin_start(5)
            
            category_row = Gtk.ListBoxRow()
            category_row.add(category_label)
            category_row.set_selectable(False)
            list_box.add(category_row)
            
            # Add tags in this category
            for tag in tags:
                tag_name = tag.get("name", "")
                tag_description = tag.get("description", "")
                
                # Create a box for the tag
                tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                tag_box.set_margin_start(10)
                tag_box.set_margin_end(10)
                tag_box.set_margin_top(5)
                tag_box.set_margin_bottom(5)
                
                # Create a check button for the tag
                check_button = Gtk.CheckButton.new_with_label(tag_name)
                if tag_description:
                    check_button.set_tooltip_text(tag_description)
                
                # Set check button state based on selected tags
                if tag_name in self.selected_tags:
                    check_button.set_active(True)
                
                # Store reference to the check button
                check_buttons[tag_name] = check_button
                
                tag_box.pack_start(check_button, False, False, 0)
                
                tag_row = Gtk.ListBoxRow()
                tag_row.add(tag_box)
                list_box.add(tag_row)
        
        # Add "Clear selection" button
        clear_button = Gtk.Button.new_with_label("Clear Selection")
        clear_button.set_margin_top(10)
        
        def on_clear_button_clicked(button):
            """Handle clear button click.
            
            Args:
                button: The Button widget
            """
            for button in check_buttons.values():
                button.set_active(False)
        
        clear_button.connect("clicked", on_clear_button_clicked)
        
        # Add the list box to the scrolled window
        scrolled.add(list_box)
        
        # Add the scrolled window to the dialog
        box = dialog.get_content_area()
        box.pack_start(scrolled, True, True, 0)
        box.pack_start(clear_button, False, False, 0)
        
        # Show all widgets
        dialog.show_all()
        
        # Handle response
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            # Get selected tags
            self.selected_tags = []
            for tag_name, button in check_buttons.items():
                if button.get_active():
                    self.selected_tags.append(tag_name)
            
            # Refresh images with the selected tags (reset to page 1)
            self._load_images(reset=True)
        
        dialog.destroy()
    
    def _on_refresh_clicked(self, button):
        """Handle refresh button click.
        
        Args:
            button: The Button widget
        """
        self._load_images(reset=True)
    
    def _load_images(self, reset=False):
        """Load images from the selected source.
        
        Args:
            reset: Whether to reset to page 1 and clear existing images
        """
        # Reset page counter if needed
        if reset:
            self.current_page = 1
            
            # Clear the current flowbox
            for child in self.flowbox.get_children():
                self.flowbox.remove(child)
        
        # Show loading indicator
        self.status_label.set_text("Loading images...")
        
        # Start a thread to fetch images
        thread = threading.Thread(target=self._fetch_images, args=(reset,))
        thread.daemon = True
        thread.start()
    
    def _fetch_images(self, reset=False):
        """Fetch images from the current source.
        
        Args:
            reset: Whether to reset the view
        """
        # If there are no more pages, don't fetch
        if not reset and not self.has_next_page:
            self.is_loading = False
            return
        
        # Default parameters
        params = {}
        
        # Get source name
        source_name = self.source_manager.get_source_name()
        print(f"Fetching images from source: {source_name}")
        
        # Source-specific parameters
        if source_name == "Wallhaven":
            # Add Wallhaven-specific parameters
            params["categories"] = self.wallhaven_category
            params["purity"] = self.wallhaven_purity
            params["sorting"] = self.wallhaven_sorting
            params["method"] = self.wallhaven_method
            
            # Add search query if available
            if self.search_query:
                params["query"] = self.search_query
            
        elif source_name == "Waifu.im":
            # For Waifu.im, we need to specify whether to include NSFW content
            params["is_nsfw"] = "nsfw" in self.selected_purity
            
        elif source_name == "Waifu.pics":
            # For Waifu.pics, we need to specify whether to include NSFW content
            print(f"Fetching Waifu.pics images with tags: {self.selected_tags}")
            params["is_nsfw"] = "nsfw" in self.selected_purity
        
        # Get images based on parameters
        response = self.source_manager.get_images(
            tags=self.selected_tags, 
            page=self.current_page,
            reset_seed=reset,
            **params
        )

        try:
            # Get images and pagination info
            new_images = response.get("images", [])
            pagination = response.get("pagination", {})
            
            # Update pagination state
            self.has_next_page = pagination.get("has_next_page", False)
            
            # If this is a reset, replace the images list
            # Otherwise, append to the existing list
            if reset:
                self.images = new_images
            else:
                self.images.extend(new_images)
            
            # Update UI in the main thread
            GLib.idle_add(self._display_images, reset)
            
        except Exception as e:
            print(f"Error fetching images: {e}")
            GLib.idle_add(self._show_error, str(e))
        
        finally:
            # Clear loading flag
            self.is_loading = False
            
            # Hide loading indicator
            GLib.idle_add(lambda: self.loading_box.hide())
            
            # Stop spinner
            GLib.idle_add(lambda: self.loading_spinner.stop())
    
    def _display_images(self, reset=False):
        """Display fetched images in the UI.
        
        Args:
            reset: Whether this is a reset (new search) or pagination
        """
        if not self.images:
            self.status_label.set_text(f"No images found from {self.source_manager.get_source_name()}")
            
            # Hide loading indicator
            self.loading_box.hide()
            self.loading_spinner.stop()
            return
        
        # If this is a pagination (not reset), only add the new images
        start_index = 0 if reset else len(self.flowbox.get_children())
        
        # Get the new images to add
        images_to_add = self.images[start_index:]
        
        # Update status text
        pagination_text = f" (Page {self.current_page})" if self.has_next_page else ""
        self.status_label.set_text(
            f"Showing {len(self.images)} images from {self.source_manager.get_source_name()}{pagination_text}"
        )
        
        # Add images to the flowbox
        for image in images_to_add:
            self._add_image_thumbnail(image)
        
        # Show all widgets
        self.show_all()
        
        # Hide loading indicator
        self.loading_box.hide()
        self.loading_spinner.stop()
    
    def _show_error(self, error_message):
        """Show error message in the UI.
        
        Args:
            error_message: Error message to display
        """
        self.status_label.set_text(f"Error: {error_message}")
        
        # Hide loading indicator
        self.loading_box.hide()
        self.loading_spinner.stop()
        
        # Create a dialog to show the error
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error loading images"
        )
        dialog.format_secondary_text(error_message)
        dialog.run()
        dialog.destroy()
    
    def _add_image_thumbnail(self, image: Dict[str, Any]):
        """Add image thumbnail to the flowbox with modern styling.
        
        Args:
            image: Image data dictionary
        """
        # Create a wrapper for the thumbnail that includes padding
        thumbnail_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        thumbnail_container.set_margin_top(10)
        thumbnail_container.set_margin_bottom(10)
        thumbnail_container.set_margin_start(10)
        thumbnail_container.set_margin_end(10)
        
        # Set a fixed minimum size for consistency
        thumbnail_container.set_property("width-request", 200)
        thumbnail_container.set_property("height-request", 180)
        
        # Load image in background thread
        thread = threading.Thread(target=self._load_image_thumbnail, args=(image, thumbnail_container))
        thread.daemon = True
        thread.start()
        
        self.flowbox.add(thumbnail_container)
    
    def _load_image_thumbnail(self, image: Dict[str, Any], box: Gtk.Box):
        """Load image thumbnail from URL.
        
        Args:
            image: Image data dictionary
            box: Box to add the image to
        """
        # Create placeholder widgets first
        placeholder_label = Gtk.Label.new("Loading...")
        
        # Add placeholders to box immediately
        GLib.idle_add(lambda: box.pack_start(placeholder_label, True, True, 0) or box.show_all())
        
        try:
            if not image.get("preview"):
                raise ValueError("No preview URL available")
                
            # Use proper headers to ensure images load correctly
            headers = {'User-Agent': 'PixelVault Image Downloader'}
            response = requests.get(image["preview"], headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to load image: HTTP {response.status_code}")
                
            # Store response content directly
            data_bytes = response.content
            
            def update_ui(image_data, data):
                try:
                    # Remove placeholders
                    for child in box.get_children():
                        box.remove(child)
                    
                    try:
                        # Create pixbuf from data
                        loader = GdkPixbuf.PixbufLoader()
                        loader.write(data)
                        loader.close()
                        
                        pixbuf = loader.get_pixbuf()
                        
                        # Get actual dimensions from pixbuf
                        actual_width = pixbuf.get_width()
                        actual_height = pixbuf.get_height()
                        
                        # Update image data with actual dimensions if not present
                        if not image_data.get('width'):
                            image_data['width'] = actual_width
                        if not image_data.get('height'):
                            image_data['height'] = actual_height
                        
                        # Scale the pixbuf
                        max_width = 550
                        max_height = 400
                        width = pixbuf.get_width()
                        height = pixbuf.get_height()
                        
                        if width > height:
                            new_width = max_width
                            new_height = int(height * (max_width / width))
                        else:
                            new_height = max_height
                            new_width = int(width * (max_height / height))
                        
                        scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
                        
                        # Create image widget
                        image_widget = Gtk.Image.new_from_pixbuf(scaled_pixbuf)
                        
                        # Store the image data
                        setattr(image_widget, 'image_data', image_data)
                        
                        # Add the image
                        box.pack_start(image_widget, False, False, 0)
                        
                        # Create a box for metadata
                        meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                        
                        # Add provider
                        provider_label = Gtk.Label.new(image_data["provider"])
                        provider_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
                        meta_box.pack_start(provider_label, False, False, 0)
                        
                        # Add resolution if available
                        if image_data.get('width') and image_data.get('height'):
                            res_label = Gtk.Label.new(f"{image_data['width']}x{image_data['height']}")
                            res_label.set_ellipsize(3)
                            meta_box.pack_start(res_label, False, False, 0)
                        
                        # Add metadata box
                        box.pack_start(meta_box, False, False, 0)
                        box.show_all()
                    except Exception as e:
                        print(f"Error processing image data: {e}")
                        error_label = Gtk.Label.new(f"Error: {str(e)}")
                        box.pack_start(error_label, True, True, 0)
                        box.show_all()
                    
                    return False  # Remove idle callback
                except Exception as e:
                    print(f"Error in update_ui: {e}")
                    # Show error instead
                    error_label = Gtk.Label.new("Error")
                    box.pack_start(error_label, True, True, 0)
                    box.show_all()
                    return False  # Remove idle callback
            
            GLib.idle_add(update_ui, image, data_bytes)
            
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            
            def show_error():
                # Remove placeholders
                for child in box.get_children():
                    box.remove(child)
                
                error_label = Gtk.Label.new("Error loading image")
                box.pack_start(error_label, True, True, 0)
                box.show_all()
                return False  # Remove idle callback
            
            GLib.idle_add(show_error)
    
    def _on_image_activated(self, flowbox, child):
        """Handle image activation (click).
        
        Args:
            flowbox: The FlowBox widget
            child: The selected FlowBoxChild
        """
        try:
            # Get the box and then find the image widget with image_data
            box = child.get_child()
            
            # Find image widget with image_data
            image_data = None
            for widget in box.get_children():
                if isinstance(widget, Gtk.Image) and hasattr(widget, 'image_data'):
                    image_data = widget.image_data
                    break
            
            if not image_data:
                raise ValueError("Could not find image data")
            
            # Make sure required fields are present
            if not image_data.get('provider'):
                image_data['provider'] = "Unknown"
            
            # Ensure we have width/height (these might come from the preview)
            if not image_data.get('width') or not image_data.get('height'):
                print("Image dimensions not available, will be filled when loading preview")
            
            # Check if auto-download is enabled
            if settings.get("auto_download", False):
                # Auto-download the image
                self._auto_download_image(image_data)
            
            # Show the image dialog (passing auto-download status)
            self._show_image_dialog(image_data, settings.get("auto_download", False))
        
        except Exception as e:
            print(f"Error handling image activation: {e}")
            self.status_label.set_text(f"Error: {str(e)}")
    
    def _auto_download_image(self, image_data: Dict[str, Any]):
        """Automatically download the image to the configured directory.
        
        Args:
            image_data: Image data dictionary
            
        Returns:
            The path where the image was saved, or None if download failed
        """
        # Get download directory from settings
        download_dir = settings.get("download_directory", "")
        
        print(f"Auto-download requested for image {image_data.get('id')}")
        print(f"Auto-download setting: {settings.get('auto_download')}")
        print(f"Download directory: {download_dir}")
        
        if not download_dir:
            print("Download directory is empty, using default")
            download_dir = str(Path.home() / "Pictures" / "Pixelvault")
            settings.set("download_directory", download_dir)
        
        # Check if we should organize by source
        if settings.get("organize_by_source", True):
            # Get source name and create subdirectory
            source_name = image_data.get("provider", "").lower().replace(".", "_")
            if source_name:
                download_dir = os.path.join(download_dir, source_name)
                print(f"Using source subdirectory: {download_dir}")
        
        if not os.path.exists(download_dir):
            # Try to create the directory
            try:
                print(f"Creating download directory: {download_dir}")
                os.makedirs(download_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating download directory: {e}")
                GLib.idle_add(lambda: self.status_label.set_text(f"Error: Could not create download directory"))
                
                # Show error dialog
                def show_error_dialog():
                    dialog = Gtk.MessageDialog(
                        transient_for=self,
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Auto-download Failed"
                    )
                    dialog.format_secondary_text(
                        f"Could not create download directory: {download_dir}\n\n"
                        f"Error: {str(e)}\n\n"
                        f"Please check your auto-download settings."
                    )
                    dialog.run()
                    dialog.destroy()
                    
                    # Open settings dialog to fix the issue
                    settings_dialog = SettingsDialog(self)
                    settings_response = settings_dialog.run()
                    
                    if settings_response == Gtk.ResponseType.OK:
                        settings_dialog.save_settings()
                    
                    settings_dialog.destroy()
                
                GLib.idle_add(show_error_dialog)
                return None
        
        # Get image ID
        image_id = image_data.get("id", "image")
        
        # Get file extension from URL
        url = image_data.get("url", "")
        if url.lower().endswith(".jpg") or url.lower().endswith(".jpeg"):
            ext = ".jpg"
        elif url.lower().endswith(".png"):
            ext = ".png"
        else:
            ext = ".jpg"
        
        # Format filename according to settings
        filename_format = settings.get("filename_format", "original")
        provider = image_data.get("provider", "").lower()
        
        if filename_format == "source_id":
            # Format: provider_id.ext
            filename = f"{provider}_{image_id}{ext}"
        elif filename_format == "date_id":
            # Format: YYYYMMDD_id.ext
            import datetime
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            filename = f"{date_str}_{image_id}{ext}"
        else:
            # Default format: just the ID
            filename = f"{image_id}{ext}"
        
        # Create full path
        save_path = os.path.join(download_dir, filename)
        
        # Check if file already exists
        if os.path.exists(save_path):
            # Add a number to avoid overwriting
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(download_dir, f"{base}_{counter}{ext}")):
                counter += 1
            save_path = os.path.join(download_dir, f"{base}_{counter}{ext}")
        
        print(f"Auto-downloading image to: {save_path}")
        
        # Update status
        GLib.idle_add(lambda: self.status_label.set_text(f"Auto-downloading image to {os.path.basename(save_path)}..."))
        
        # Start download in a background thread
        thread = threading.Thread(target=self._download_image_task, args=(image_data, save_path, True))
        thread.daemon = True
        thread.start()
        
        # Return the path for reference
        return save_path
    
    def _show_image_dialog(self, image_data: Dict[str, Any], auto_download_enabled=False):
        """Show dialog with image details and options.
        
        Args:
            image_data: Image data dictionary
            auto_download_enabled: Whether auto-download is enabled
        """
        try:
            # Normalize tags - ensure they're strings
            if 'tags' in image_data:
                if isinstance(image_data['tags'], list):
                    # Check if tags are dictionaries or strings
                    normalized_tags = []
                    for tag in image_data['tags']:
                        if isinstance(tag, dict) and 'name' in tag:
                            normalized_tags.append(tag['name'])
                        elif isinstance(tag, str):
                            normalized_tags.append(tag)
                    image_data['tags'] = normalized_tags
                elif not image_data['tags']:
                    # If empty, use empty list
                    image_data['tags'] = []
            
            # Determine the buttons to show based on auto-download status
            if auto_download_enabled:
                # If auto-download is enabled, show Download, Open Folder and Wallpaper buttons
                buttons = (
                    "Cancel", Gtk.ResponseType.CANCEL,
                    "Open Folder", Gtk.ResponseType.HELP,
                    "Download Again", Gtk.ResponseType.APPLY,
                    "Set as Wallpaper", Gtk.ResponseType.OK
                )
            else:
                # Standard buttons when auto-download is disabled
                buttons = (
                    "Cancel", Gtk.ResponseType.CANCEL,
                    "Download", Gtk.ResponseType.APPLY,
                    "Set as Wallpaper", Gtk.ResponseType.OK
                )
                
            dialog = Gtk.Dialog(
                title="Image Details",
                parent=self,
                flags=0,
                buttons=buttons
            )
            dialog.set_default_size(600, 500)
            
            content_area = dialog.get_content_area()
            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            content_box.set_margin_top(12)
            content_box.set_margin_bottom(12)
            content_box.set_margin_start(12)
            content_box.set_margin_end(12)
            content_area.add(content_box)
            
            # Image preview
            thread = threading.Thread(target=self._load_preview_image, args=(image_data, content_box))
            thread.daemon = True
            thread.start()
            
            # Image details
            details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            
            # Create a scrolled window for metadata
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled_window.set_min_content_height(150)
            
            # Use a grid for metadata with better alignment
            metadata_grid = Gtk.Grid()
            metadata_grid.set_column_spacing(10)
            metadata_grid.set_row_spacing(6)
            
            # Add all available metadata
            row = 0
            
            # ID
            if image_data.get('id'):
                id_label = Gtk.Label.new("ID:")
                id_label.set_halign(Gtk.Align.START)
                id_value = Gtk.Label.new(str(image_data.get('id')))
                id_value.set_halign(Gtk.Align.START)
                id_value.set_selectable(True)
                metadata_grid.attach(id_label, 0, row, 1, 1)
                metadata_grid.attach(id_value, 1, row, 1, 1)
                row += 1
            
            # Provider
            provider_label = Gtk.Label.new("Provider:")
            provider_label.set_halign(Gtk.Align.START)
            provider_value = Gtk.Label.new(image_data.get('provider', 'Unknown'))
            provider_value.set_halign(Gtk.Align.START)
            provider_value.set_selectable(True)
            metadata_grid.attach(provider_label, 0, row, 1, 1)
            metadata_grid.attach(provider_value, 1, row, 1, 1)
            row += 1
            
            # Resolution
            if image_data.get('width') and image_data.get('height'):
                res_label = Gtk.Label.new("Resolution:")
                res_label.set_halign(Gtk.Align.START)
                res_value = Gtk.Label.new(f"{image_data.get('width')}x{image_data.get('height')}")
                res_value.set_halign(Gtk.Align.START)
                res_value.set_selectable(True)
                metadata_grid.attach(res_label, 0, row, 1, 1)
                metadata_grid.attach(res_value, 1, row, 1, 1)
                row += 1
            
            # Source
            if image_data.get('source'):
                source_label = Gtk.Label.new("Source:")
                source_label.set_halign(Gtk.Align.START)
                source_link = Gtk.LinkButton.new_with_label(image_data.get('source'), image_data.get('source'))
                source_link.set_halign(Gtk.Align.START)
                metadata_grid.attach(source_label, 0, row, 1, 1)
                metadata_grid.attach(source_link, 1, row, 1, 1)
                row += 1
            
            # Tags
            if image_data.get('tags') and len(image_data.get('tags', [])) > 0:
                tags_label = Gtk.Label.new("Tags:")
                tags_label.set_halign(Gtk.Align.START)
                
                # Join tags list into a string
                tags_text = ", ".join(image_data.get('tags', []))
                
                tags_value = Gtk.Label.new(tags_text)
                tags_value.set_halign(Gtk.Align.START)
                tags_value.set_line_wrap(True)
                tags_value.set_selectable(True)
                metadata_grid.attach(tags_label, 0, row, 1, 1)
                metadata_grid.attach(tags_value, 1, row, 1, 1)
                row += 1
            
            # Category
            if image_data.get('category'):
                cat_label = Gtk.Label.new("Category:")
                cat_label.set_halign(Gtk.Align.START)
                cat_value = Gtk.Label.new(image_data.get('category'))
                cat_value.set_halign(Gtk.Align.START)
                cat_value.set_selectable(True)
                metadata_grid.attach(cat_label, 0, row, 1, 1)
                metadata_grid.attach(cat_value, 1, row, 1, 1)
                row += 1
            
            # Add grid to scrolled window
            scrolled_window.add(metadata_grid)
            details_box.pack_start(scrolled_window, True, True, 0)
            
            # Add auto-download status indicator if enabled
            if auto_download_enabled:
                download_dir = settings.get("download_directory", "")
                auto_dl_label = Gtk.Label()
                auto_dl_label.set_markup(f"<i>Auto-downloading to {os.path.basename(download_dir)}/</i>")
                details_box.pack_start(auto_dl_label, False, False, 0)
            
            content_box.pack_start(details_box, True, True, 0)
            
            dialog.show_all()
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                self._set_as_wallpaper(image_data)
            elif response == Gtk.ResponseType.APPLY:
                self._download_image(image_data)
            elif response == Gtk.ResponseType.HELP:  # Open folder button
                self._open_download_folder()
            
            dialog.destroy()
        except Exception as e:
            print(f"Error in _show_image_dialog: {e}")
            self.status_label.set_text(f"Error showing image details: {str(e)}")
    
    def _open_download_folder(self):
        """Open the download folder in the file manager."""
        download_dir = settings.get("download_directory", "")
        if not download_dir or not os.path.exists(download_dir):
            # If download directory doesn't exist, show error
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Download directory not found"
            )
            dialog.format_secondary_text(f"The directory {download_dir} does not exist.")
            dialog.run()
            dialog.destroy()
            return
        
        # Try xdg-open first (most Linux distros)
        try:
            subprocess.Popen(["xdg-open", download_dir])
            return
        except:
            pass
        
        # Try nautilus (GNOME)
        try:
            subprocess.Popen(["nautilus", download_dir])
            return
        except:
            pass
        
        # Try thunar (XFCE)
        try:
            subprocess.Popen(["thunar", download_dir])
            return
        except:
            pass
        
        # Try dolphin (KDE)
        try:
            subprocess.Popen(["dolphin", download_dir])
            return
        except:
            pass
        
        # If we get here, none of the commands worked
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Could not open folder"
        )
        dialog.format_secondary_text("No compatible file manager found.")
        dialog.run()
        dialog.destroy()
    
    def _download_image(self, image_data: Dict[str, Any]):
        """Download the image to a user-selected location.
        
        Args:
            image_data: Image data dictionary
        """
        # Create file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title="Save Image",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(
                "Cancel", Gtk.ResponseType.CANCEL,
                "Save", Gtk.ResponseType.ACCEPT
            )
        )
        
        # Set suggested filename based on image id
        image_id = image_data.get("id", "image")
        # Add file extension based on URL
        url = image_data.get("url", "")
        if url.lower().endswith(".jpg") or url.lower().endswith(".jpeg"):
            dialog.set_current_name(f"{image_id}.jpg")
        elif url.lower().endswith(".png"):
            dialog.set_current_name(f"{image_id}.png")
        else:
            dialog.set_current_name(f"{image_id}.jpg")
        
        # Add filters for image types
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Image files")
        filter_images.add_mime_type("image/jpeg")
        filter_images.add_mime_type("image/png")
        dialog.add_filter(filter_images)
        
        # Show the dialog
        response = dialog.run()
        
        if response == Gtk.ResponseType.ACCEPT:
            save_path = dialog.get_filename()
            dialog.destroy()
            
            # Start download in a background thread
            thread = threading.Thread(target=self._download_image_task, args=(image_data, save_path))
            thread.daemon = True
            thread.start()
        else:
            dialog.destroy()
    
    def _download_image_task(self, image_data: Dict[str, Any], save_path: str, is_auto_download=False):
        """Background task to download and save the image.
        
        Args:
            image_data: Image data dictionary
            save_path: Path to save the image to
            is_auto_download: Whether this is an automatic download
        """
        try:
            # Update status if not auto-download (auto-download already updated status)
            if not is_auto_download:
                GLib.idle_add(lambda: self.status_label.set_text(f"Downloading image..."))
            
            # Download the full-size image with stream=True to avoid loading entire image in memory
            headers = {'User-Agent': 'PixelVault Image Downloader'}
            response = requests.get(image_data["url"], stream=True, headers=headers)
            response.raise_for_status()
            
            # Print debug info about the image being downloaded
            print(f"Downloading image: {image_data.get('id', 'unknown')} from {image_data.get('provider', 'unknown')}")
            print(f"URL: {image_data.get('url', 'unknown')}")
            print(f"Resolution: {image_data.get('width', 'unknown')}x{image_data.get('height', 'unknown')}")
            
            # Save to file preserving original quality
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Try to add metadata to image
            try:
                # Open image with PIL to update metadata
                img = Image.open(save_path)
                
                # Extract actual image dimensions from the file
                width, height = img.size
                
                # Update image_data with actual dimensions if they weren't set
                if not image_data.get('width') or not image_data.get('height'):
                    image_data['width'] = width
                    image_data['height'] = height
                    print(f"Updated dimensions from file: {width}x{height}")
                
                # Create metadata dictionary for PNG files
                metadata = PngImagePlugin.PngInfo() if save_path.lower().endswith('.png') else None
                
                # If PNG, we can add metadata
                if metadata:
                    # Normalize tags
                    tag_list = []
                    if 'tags' in image_data:
                        if isinstance(image_data['tags'], list):
                            for tag in image_data['tags']:
                                if isinstance(tag, dict) and 'name' in tag:
                                    tag_list.append(tag['name'])
                                elif isinstance(tag, str):
                                    tag_list.append(tag)
                        image_data['tags'] = tag_list
                    
                    # Add image information as metadata
                    if image_data.get('id'):
                        metadata.add_text("ID", str(image_data.get('id')))
                    if image_data.get('provider'):
                        metadata.add_text("Provider", str(image_data.get('provider')))
                    if image_data.get('source'):
                        metadata.add_text("Source", str(image_data.get('source')))
                    if image_data.get('width') and image_data.get('height'):
                        metadata.add_text("Resolution", f"{image_data.get('width')}x{image_data.get('height')}")
                    if tag_list:
                        metadata.add_text("Tags", ", ".join(tag_list))
                    
                    # Save the PNG with metadata
                    img.save(save_path, pnginfo=metadata)
                    print(f"Added metadata to PNG file")
                
                # Close the image
                img.close()
            except Exception as e:
                print(f"Error adding metadata to image: {e}")
                # Continue even if metadata addition fails
            
            # Show success message
            filename = os.path.basename(save_path)
            message = f"Image auto-downloaded to {filename}" if is_auto_download else f"Image downloaded to {filename}"
            GLib.idle_add(lambda: self.status_label.set_text(message))
            
            # Show notification of successful download
            def show_success_notification():
                notification_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=Gtk.DialogFlags.MODAL,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK_CANCEL,
                    text="Download Complete"
                )
                
                # Add secondary text showing the path and metadata
                if image_data.get('width') and image_data.get('height'):
                    notification_dialog.format_secondary_text(
                        f"Image saved to: {save_path}\n"
                        f"Resolution: {image_data.get('width')}x{image_data.get('height')}"
                    )
                else:
                    notification_dialog.format_secondary_text(f"Image saved to: {save_path}")
                
                # Add button to open folder
                notification_dialog.add_button("Open Folder", Gtk.ResponseType.HELP)
                
                # Show the dialog
                response = notification_dialog.run()
                
                if response == Gtk.ResponseType.HELP:
                    # Open the containing folder
                    self._open_download_folder()
                
                notification_dialog.destroy()
                return False  # Remove idle callback
            
            # Show notification for manual downloads, or if auto-download setting requests it
            if not is_auto_download or settings.get("show_auto_download_notification", True):
                GLib.idle_add(show_success_notification)
            
        except Exception as e:
            # Show error message
            GLib.idle_add(lambda: self.status_label.set_text(f"Error downloading image: {str(e)}"))
            
            # Show error dialog only if not auto-download
            if not is_auto_download:
                def show_error_dialog():
                    dialog = Gtk.MessageDialog(
                        transient_for=self,
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Error downloading image"
                    )
                    dialog.format_secondary_text(f"Error: {str(e)}\n\nURL: {image_data['url']}")
                    dialog.run()
                    dialog.destroy()
                
                GLib.idle_add(show_error_dialog)
    
    def _load_preview_image(self, image_data: Dict[str, Any], box: Gtk.Box):
        """Load preview image for the dialog.
        
        Args:
            image_data: Image data dictionary
            box: Box to add the image to
        """
        # Create placeholder
        placeholder_label = Gtk.Label.new("Loading preview...")
        
        # Add placeholder to UI immediately
        GLib.idle_add(lambda: box.pack_start(placeholder_label, False, False, 0) or box.reorder_child(placeholder_label, 0) or box.show_all())
        
        try:
            # Load the image in the background with headers
            headers = {'User-Agent': 'PixelVault Image Downloader'}
            response = requests.get(image_data["url"], headers=headers, stream=True)
            response.raise_for_status()
            
            # Read the data
            data_bytes = response.content
            
            # Update the image in the main thread
            def update_image(data, placeholder):
                try:
                    # Remove placeholders
                    for child in box.get_children():
                        if child == placeholder:
                            box.remove(child)
                    
                    try:
                        # Create pixbuf from data
                        loader = GdkPixbuf.PixbufLoader()
                        loader.write(data)
                        loader.close()
                        
                        pixbuf = loader.get_pixbuf()
                        
                        # Get actual dimensions from pixbuf
                        actual_width = pixbuf.get_width()
                        actual_height = pixbuf.get_height()
                        
                        # Update image data with actual dimensions if not present
                        if not image_data.get('width'):
                            image_data['width'] = actual_width
                        if not image_data.get('height'):
                            image_data['height'] = actual_height
                        
                        # Scale the pixbuf
                        max_width = 550
                        max_height = 400
                        width = pixbuf.get_width()
                        height = pixbuf.get_height()
                        
                        if width > height:
                            new_width = min(width, max_width)
                            new_height = int(height * (new_width / width))
                        else:
                            new_height = min(height, max_height)
                            new_width = int(width * (new_height / height))
                        
                        scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
                        
                        # Create and add image widget
                        image_widget = Gtk.Image.new_from_pixbuf(scaled_pixbuf)
                        box.pack_start(image_widget, False, False, 0)
                        box.reorder_child(image_widget, 0)
                        box.show_all()
                    except Exception as e:
                        print(f"Error processing preview image: {e}")
                        error_label = Gtk.Label.new(f"Error: {str(e)}")
                        box.pack_start(error_label, False, False, 0)
                        box.reorder_child(error_label, 0)
                        box.show_all()
                    
                    return False  # Remove idle callback
                except Exception as e:
                    print(f"Error in update_image: {e}")
                    error_label = Gtk.Label.new("Error loading full image")
                    box.pack_start(error_label, False, False, 0)
                    box.reorder_child(error_label, 0)
                    box.show_all()
                    return False  # Remove idle callback
            
            GLib.idle_add(update_image, data_bytes, placeholder_label)
            
        except Exception as e:
            print(f"Error loading preview image: {e}")
            
            def show_error():
                # Remove placeholders
                for child in box.get_children():
                    if child == placeholder_label:
                        box.remove(child)
                        
                error_label = Gtk.Label.new("Error loading full image")
                box.pack_start(error_label, False, False, 0)
                box.reorder_child(error_label, 0)
                box.show_all()
                return False  # Remove idle callback
            
            GLib.idle_add(show_error)
    
    def _set_as_wallpaper(self, image_data: Dict[str, Any]):
        """Set the image as desktop wallpaper.
        
        Args:
            image_data: Image data dictionary
        """
        try:
            # Download the image with stream=True to preserve quality
            headers = {'User-Agent': 'PixelVault Image Downloader'}
            response = requests.get(image_data["url"], stream=True, headers=headers)
            response.raise_for_status()
            
            # Determine appropriate file extension
            url = image_data["url"].lower()
            ext = ".jpg"  # Default extension
            if url.endswith(".png"):
                ext = ".png"
            elif url.endswith(".jpeg"):
                ext = ".jpg"
            
            # Save to a temporary file with correct extension
            temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(temp_fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Try to add metadata to wallpaper image
            try:
                # Get dimensions from the file
                img = Image.open(temp_path)
                width, height = img.size
                
                # Update image_data with actual dimensions if they weren't set
                if not image_data.get('width') or not image_data.get('height'):
                    image_data['width'] = width
                    image_data['height'] = height
                
                # Create metadata for PNG files
                if temp_path.lower().endswith('.png'):
                    metadata = PngImagePlugin.PngInfo()
                    
                    # Normalize tags
                    tag_list = []
                    if 'tags' in image_data:
                        if isinstance(image_data['tags'], list):
                            for tag in image_data['tags']:
                                if isinstance(tag, dict) and 'name' in tag:
                                    tag_list.append(tag['name'])
                                elif isinstance(tag, str):
                                    tag_list.append(tag)
                        image_data['tags'] = tag_list
                    
                    # Add image information as metadata
                    if image_data.get('id'):
                        metadata.add_text("ID", str(image_data.get('id')))
                    if image_data.get('provider'):
                        metadata.add_text("Provider", str(image_data.get('provider')))
                    if image_data.get('source'):
                        metadata.add_text("Source", str(image_data.get('source')))
                    if image_data.get('width') and image_data.get('height'):
                        metadata.add_text("Resolution", f"{image_data.get('width')}x{image_data.get('height')}")
                    if tag_list:
                        metadata.add_text("Tags", ", ".join(tag_list))
                    
                    # Save the PNG with metadata
                    img.save(temp_path, pnginfo=metadata)
                
                # Close the image
                img.close()
            except Exception as e:
                print(f"Error adding metadata to wallpaper image: {e}")
                # Continue even if metadata addition fails
            
            # Set as wallpaper using gsettings (GNOME)
            try:
                subprocess.call([
                    "gsettings", "set", "org.gnome.desktop.background",
                    "picture-uri", f"file://{temp_path}"
                ])
                self.status_label.set_text(f"Wallpaper set successfully")
                return
            except:
                pass
            
            # Try xfconf-query (XFCE)
            try:
                subprocess.call([
                    "xfconf-query", "-c", "xfce4-desktop", "-p",
                    "/backdrop/screen0/monitor0/workspace0/last-image", "-s", temp_path
                ])
                self.status_label.set_text(f"Wallpaper set successfully")
                return
            except:
                pass
            
            # Try feh (for minimal window managers)
            try:
                subprocess.call(["feh", "--bg-fill", temp_path])
                self.status_label.set_text(f"Wallpaper set successfully")
                return
            except:
                pass
            
            # Try nitrogen
            try:
                subprocess.call(["nitrogen", "--set-zoom-fill", temp_path])
                self.status_label.set_text(f"Wallpaper set successfully")
                return
            except:
                pass
                
            # If we got here, none of the wallpaper setters worked
            self.status_label.set_text("Failed to set wallpaper - no compatible wallpaper setter found")
            
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            self.status_label.set_text(f"Error setting wallpaper: {str(e)}")

    def _on_sort_changed(self, combo):
        """Handle sort method change.
        
        Args:
            combo: The ComboBox widget
        """
        # Only applies to Wallhaven source
        if self.source_manager.current_source != ImageSource.WALLHAVEN:
            return
            
        active = combo.get_active()
        
        # Update sorting based on selection
        if active == 0:  # Latest
            self.wallhaven_sorting = WallhavenSorting.DATE_ADDED
        elif active == 1:  # Top
            self.wallhaven_sorting = WallhavenSorting.TOPLIST
        elif active == 2:  # Random
            self.wallhaven_sorting = WallhavenSorting.RANDOM
        
        # Reset and load images with new sorting
        self._load_images(reset=True)

    def _on_settings_clicked(self, button):
        """Handle settings button click.
        
        Args:
            button: The Button widget
        """
        dialog = SettingsDialog(self)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Get the previous API key before saving
            previous_api_key = settings.get("wallhaven_api_key", "")
            
            # Save settings
            dialog.save_settings()
            
            # Check if Wallhaven API key changed
            new_api_key = settings.get("wallhaven_api_key", "")
            if new_api_key != previous_api_key:
                # Update the API client
                self.source_manager.update_wallhaven_api_key(new_api_key)
                
                # Refresh images if currently using Wallhaven
                if self.source_manager.current_source == ImageSource.WALLHAVEN:
                    self._load_images(reset=True)
                    
                    # Show a status message
                    if new_api_key:
                        self.status_label.set_text("Wallhaven API key updated. Refreshing images.")
                    else:
                        self.status_label.set_text("Wallhaven API key removed. Refreshing images.")
        
        dialog.destroy()

    def _on_api_key_button_clicked(self, button, parent_dialog):
        """Open the settings dialog to add an API key from the advanced options dialog.
        
        Args:
            button: The Button widget
            parent_dialog: The parent dialog to hide
        """
        # Hide the parent dialog temporarily
        parent_dialog.hide()
        
        # Open settings dialog
        settings_dialog = SettingsDialog(self)
        
        # Select the Wallhaven API tab (index 2)
        notebook = None
        for child in settings_dialog.get_content_area().get_children():
            if isinstance(child, Gtk.Notebook):
                notebook = child
                break
        
        if notebook:
            notebook.set_current_page(2)  # API tab is index 2
        
        response = settings_dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Get the previous API key before saving
            previous_api_key = settings.get("wallhaven_api_key", "")
            
            # Save settings
            settings_dialog.save_settings()
            
            # Check if Wallhaven API key changed
            new_api_key = settings.get("wallhaven_api_key", "")
            if new_api_key != previous_api_key:
                # Update the API client
                self.source_manager.update_wallhaven_api_key(new_api_key)
        
        settings_dialog.destroy()
        
        # Show the parent dialog again
        parent_dialog.show()

    def _on_purity_check_toggled(self, button):
        """Handle purity checkbox toggled to prevent all being unchecked.
        
        Args:
            button: The CheckButton that was toggled
        """
        # Check if all purity checkboxes would be unchecked
        if not self.sfw_check.get_active() and not self.sketchy_check.get_active() and not self.nsfw_check.get_active():
            # Revert the toggle that would lead to all being unchecked
            button.set_active(True)
            
            # Show a warning to the user
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="At least one content filter must be selected"
            )
            dialog.format_secondary_text("Please select at least one of: SFW, Sketchy, or NSFW")
            dialog.run()
            dialog.destroy()

    def _on_wallhaven_search_activated(self, entry):
        """Handle search entry activation.
        
        Args:
            entry: The SearchEntry widget
        """
        self.search_query = entry.get_text()
        self._load_images(reset=True)

    def _on_wallhaven_search_clicked(self, button):
        """Handle search button click.
        
        Args:
            button: The Button widget
        """
        self.search_query = self.wallhaven_search_entry.get_text()
        self._load_images(reset=True)

    def _on_wallhaven_clear_clicked(self, button):
        """Handle clear search button click.
        
        Args:
            button: The Button widget
        """
        self.wallhaven_search_entry.set_text("")
        self.search_query = ""
        self._load_images(reset=True)
