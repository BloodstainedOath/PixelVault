import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio
import os
from pathlib import Path
import subprocess
import threading

from ..settings import settings

class SettingsDialog(Gtk.Dialog):
    """Dialog for managing application settings."""
    
    def __init__(self, parent):
        """Initialize the settings dialog.
        
        Args:
            parent: Parent window
        """
        super().__init__(
            title="Settings",
            parent=parent,
            flags=0,
            buttons=(
                "Cancel", Gtk.ResponseType.CANCEL,
                "Save", Gtk.ResponseType.OK
            )
        )
        self.set_default_size(400, 250)
        self.set_resizable(True)
        
        # Create notebook for tabbed interface
        notebook = Gtk.Notebook()
        content_area = self.get_content_area()
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        content_area.add(notebook)
        
        # Create tabs
        self._create_general_tab(notebook)
        self._create_auto_download_tab(notebook)
        self._create_wallhaven_tab(notebook)
        
        self.show_all()
    
    def _create_general_tab(self, notebook):
        """Create the general settings tab.
        
        Args:
            notebook: Notebook widget to add the tab to
        """
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        
        # Reset button
        reset_button = Gtk.Button.new_with_label("Reset All Settings")
        reset_button.connect("clicked", self._on_reset_clicked)
        
        grid.attach(reset_button, 0, 0, 1, 1)
        
        # Create tab
        tab_label = Gtk.Label.new("General")
        notebook.append_page(grid, tab_label)
    
    def _create_auto_download_tab(self, notebook):
        """Create the auto download settings tab.
        
        Args:
            notebook: Notebook widget to add the tab to
        """
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        
        row = 0
        
        # Enable auto download
        self.auto_download_switch = Gtk.Switch()
        self.auto_download_switch.set_active(settings.get("auto_download", False))
        self.auto_download_switch.connect("notify::active", self._on_auto_download_toggled)
        
        auto_download_label = Gtk.Label.new("Automatically download images:")
        auto_download_label.set_halign(Gtk.Align.START)
        
        grid.attach(auto_download_label, 0, row, 1, 1)
        grid.attach(self.auto_download_switch, 1, row, 1, 1)
        
        row += 1
        
        # Download directory
        download_dir_label = Gtk.Label.new("Download directory:")
        download_dir_label.set_halign(Gtk.Align.START)
        
        self.download_dir_entry = Gtk.Entry()
        self.download_dir_entry.set_text(settings.get("download_directory", ""))
        self.download_dir_entry.set_hexpand(True)
        
        browse_button = Gtk.Button.new_with_label("Browse")
        browse_button.connect("clicked", self._on_browse_clicked)
        
        # Open folder button
        open_folder_button = Gtk.Button.new_with_label("Open")
        open_folder_button.connect("clicked", self._on_open_folder_clicked)
        open_folder_button.set_tooltip_text("Open the download folder")
        
        dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        dir_box.pack_start(self.download_dir_entry, True, True, 0)
        dir_box.pack_start(browse_button, False, False, 0)
        dir_box.pack_start(open_folder_button, False, False, 0)
        
        grid.attach(download_dir_label, 0, row, 1, 1)
        grid.attach(dir_box, 1, row, 2, 1)
        
        row += 1
        
        # Show notifications for auto-downloads
        notification_label = Gtk.Label.new("Show download notifications:")
        notification_label.set_halign(Gtk.Align.START)
        
        self.notification_switch = Gtk.Switch()
        self.notification_switch.set_active(settings.get("show_auto_download_notification", True))
        
        grid.attach(notification_label, 0, row, 1, 1)
        grid.attach(self.notification_switch, 1, row, 1, 1)
        
        row += 1
        
        # Organize downloads by source
        organize_label = Gtk.Label.new("Organize by source:")
        organize_label.set_halign(Gtk.Align.START)
        
        self.organize_switch = Gtk.Switch()
        self.organize_switch.set_active(settings.get("organize_by_source", True))
        self.organize_switch.set_tooltip_text("Create subdirectories for each source (Wallhaven, Waifu.im, etc.)")
        
        grid.attach(organize_label, 0, row, 1, 1)
        grid.attach(self.organize_switch, 1, row, 1, 1)
        
        row += 1
        
        # Filename format
        filename_label = Gtk.Label.new("Filename format:")
        filename_label.set_halign(Gtk.Align.START)
        
        self.filename_combo = Gtk.ComboBoxText()
        self.filename_combo.append_text("Original ID (e.g. abc123.jpg)")
        self.filename_combo.append_text("ID and Source (e.g. wallhaven_abc123.jpg)")
        self.filename_combo.append_text("Date and ID (e.g. 20230621_abc123.jpg)")
        
        filename_format = settings.get("filename_format", "original")
        if filename_format == "original":
            self.filename_combo.set_active(0)
        elif filename_format == "source_id":
            self.filename_combo.set_active(1)
        elif filename_format == "date_id":
            self.filename_combo.set_active(2)
        else:
            self.filename_combo.set_active(0)
        
        grid.attach(filename_label, 0, row, 1, 1)
        grid.attach(self.filename_combo, 1, row, 2, 1)
        
        row += 1
        
        # Create tab
        tab_label = Gtk.Label.new("Auto Download")
        notebook.append_page(grid, tab_label)
    
    def _create_wallhaven_tab(self, notebook):
        """Create the Wallhaven settings tab.
        
        Args:
            notebook: Notebook widget to add the tab to
        """
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        
        row = 0
        
        # Title/Header
        header_label = Gtk.Label()
        header_label.set_markup("<b>Wallhaven API Settings</b>")
        header_label.set_halign(Gtk.Align.START)
        grid.attach(header_label, 0, row, 2, 1)
        
        row += 1
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup(
            "Enter your Wallhaven API key to access:\n"
            "• Your personal collections\n"
            "• NSFW content (if enabled in your account)\n"
            "• Higher API rate limits\n\n"
            "Get your API key at: <a href='https://wallhaven.cc/settings/account'>https://wallhaven.cc/settings/account</a>"
        )
        info_label.set_line_wrap(True)
        info_label.set_xalign(0)
        info_label.set_margin_bottom(10)
        grid.attach(info_label, 0, row, 2, 1)
        
        row += 1
        
        # API Key input
        api_key_label = Gtk.Label.new("API Key:")
        api_key_label.set_halign(Gtk.Align.START)
        
        self.api_key_entry = Gtk.Entry()
        self.api_key_entry.set_text(settings.get("wallhaven_api_key", ""))
        self.api_key_entry.set_hexpand(True)
        self.api_key_entry.set_visibility(False)  # Hide the API key (like a password)
        self.api_key_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        
        # Show/Hide toggle button for API key
        show_button = Gtk.ToggleButton()
        show_icon = Gio.ThemedIcon(name="view-reveal-symbolic")
        show_image = Gtk.Image.new_from_gicon(show_icon, Gtk.IconSize.BUTTON)
        show_button.add(show_image)
        show_button.set_tooltip_text("Show/Hide API Key")
        show_button.connect("toggled", self._on_show_api_key_toggled)
        
        api_key_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        api_key_box.pack_start(self.api_key_entry, True, True, 0)
        api_key_box.pack_start(show_button, False, False, 0)
        
        grid.attach(api_key_label, 0, row, 1, 1)
        grid.attach(api_key_box, 1, row, 1, 1)
        
        row += 1
        
        # Test API Key button
        test_button = Gtk.Button.new_with_label("Test API Key")
        test_button.connect("clicked", self._on_test_api_key_clicked)
        test_button.set_margin_top(10)
        
        grid.attach(test_button, 1, row, 1, 1)
        
        row += 1
        
        # Status indicator
        self.api_status_label = Gtk.Label()
        self.api_status_label.set_markup("")
        self.api_status_label.set_halign(Gtk.Align.START)
        grid.attach(self.api_status_label, 0, row, 2, 1)
        
        # Create tab
        tab_label = Gtk.Label.new("Wallhaven API")
        notebook.append_page(grid, tab_label)
    
    def _on_auto_download_toggled(self, switch, gparam):
        """Handle auto download toggle.
        
        Args:
            switch: The Switch widget
            gparam: The parameter
        """
        if switch.get_active():
            # Check if download directory exists, create if not
            download_dir = self.download_dir_entry.get_text()
            if download_dir and not os.path.exists(download_dir):
                try:
                    os.makedirs(download_dir, exist_ok=True)
                except Exception as e:
                    # Show error
                    dialog = Gtk.MessageDialog(
                        transient_for=self,
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text=f"Could not create download directory: {e}"
                    )
                    dialog.run()
                    dialog.destroy()
                    
                    # Turn off the switch
                    switch.set_active(False)
    
    def _on_browse_clicked(self, button):
        """Handle browse button click.
        
        Args:
            button: The Button widget
        """
        dialog = Gtk.FileChooserDialog(
            title="Select Download Directory",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(
                "Cancel", Gtk.ResponseType.CANCEL,
                "Select", Gtk.ResponseType.ACCEPT
            )
        )
        
        # Set current folder
        current_dir = self.download_dir_entry.get_text()
        if current_dir and os.path.exists(current_dir):
            dialog.set_current_folder(current_dir)
        else:
            dialog.set_current_folder(str(Path.home() / "Pictures"))
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.ACCEPT:
            self.download_dir_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def _on_open_folder_clicked(self, button):
        """Open the download folder.
        
        Args:
            button: The Button widget
        """
        download_dir = self.download_dir_entry.get_text()
        if not download_dir or not os.path.exists(download_dir):
            # If directory doesn't exist, show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Directory does not exist"
            )
            dialog.format_secondary_text(f"The directory '{download_dir}' does not exist.")
            dialog.run()
            dialog.destroy()
            return
        
        # Try to open the directory using various file managers
        try:
            subprocess.Popen(["xdg-open", download_dir])
        except:
            try:
                subprocess.Popen(["nautilus", download_dir])
            except:
                try:
                    subprocess.Popen(["thunar", download_dir])
                except:
                    try:
                        subprocess.Popen(["dolphin", download_dir])
                    except:
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
    
    def _on_reset_clicked(self, button):
        """Handle reset button click.
        
        Args:
            button: The Button widget
        """
        # Confirm reset
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset all settings to defaults?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Reset settings
            settings.reset()
            
            # Update UI
            self.auto_download_switch.set_active(settings.get("auto_download", False))
            self.download_dir_entry.set_text(settings.get("download_directory", ""))
    
    def _on_show_api_key_toggled(self, button):
        """Toggle the visibility of the API key.
        
        Args:
            button: The ToggleButton widget
        """
        self.api_key_entry.set_visibility(button.get_active())
    
    def _on_test_api_key_clicked(self, button):
        """Test the Wallhaven API key.
        
        Args:
            button: The Button widget
        """
        api_key = self.api_key_entry.get_text().strip()
        if not api_key:
            self.api_status_label.set_markup("<span foreground='red'>Please enter an API key</span>")
            return
        
        # Disable button during test
        button.set_sensitive(False)
        self.api_status_label.set_markup("<span foreground='blue'>Testing API key...</span>")
        
        # Run the test in a background thread
        thread = threading.Thread(target=self._test_api_key, args=(api_key, button))
        thread.daemon = True
        thread.start()
    
    def _test_api_key(self, api_key, button):
        """Test the Wallhaven API key in a background thread.
        
        Args:
            api_key: The API key to test
            button: The button to re-enable after testing
        """
        from ..api.wallhaven import WallhavenAPI
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib
        
        try:
            # Create a new Wallhaven API client with the key
            api = WallhavenAPI(api_key=api_key)
            
            # Try to get user settings (only works with valid API key)
            user_settings = api.get_user_settings()
            
            # Check if settings were returned
            if "data" in user_settings:
                username = user_settings["data"].get("username", "User")
                GLib.idle_add(
                    lambda: self.api_status_label.set_markup(
                        f"<span foreground='green'>✓ Valid API key for user: {username}</span>"
                    )
                )
            else:
                GLib.idle_add(
                    lambda: self.api_status_label.set_markup(
                        "<span foreground='red'>❌ Invalid response from API</span>"
                    )
                )
        except Exception as e:
            GLib.idle_add(
                lambda: self.api_status_label.set_markup(
                    f"<span foreground='red'>❌ Error: {str(e)}</span>"
                )
            )
        finally:
            # Re-enable the button
            GLib.idle_add(lambda: button.set_sensitive(True))
    
    def save_settings(self):
        """Save settings from the dialog."""
        # Get previous auto-download setting to check if it changed
        previous_auto_download = settings.get("auto_download", False)
        
        # Auto download
        auto_download = self.auto_download_switch.get_active()
        settings.set("auto_download", auto_download)
        
        # Log the auto-download setting change for debugging
        print(f"Auto-download setting changed: {previous_auto_download} -> {auto_download}")
        
        # Download directory
        download_dir = self.download_dir_entry.get_text()
        if download_dir:
            # Create directory if it doesn't exist
            try:
                os.makedirs(download_dir, exist_ok=True)
                settings.set("download_directory", download_dir)
                print(f"Download directory set to: {download_dir}")
            except Exception as e:
                print(f"Error creating download directory: {e}")
                # Keep old value
                self.download_dir_entry.set_text(settings.get("download_directory", ""))
        
        # Show notifications
        settings.set("show_auto_download_notification", self.notification_switch.get_active())
        
        # Organize by source
        settings.set("organize_by_source", self.organize_switch.get_active())
        
        # Filename format
        active_format = self.filename_combo.get_active()
        if active_format == 0:
            settings.set("filename_format", "original")
        elif active_format == 1:
            settings.set("filename_format", "source_id")
        elif active_format == 2:
            settings.set("filename_format", "date_id")
        
        # Wallhaven API key
        api_key = self.api_key_entry.get_text().strip()
        settings.set("wallhaven_api_key", api_key)
        
        # Force save the settings to ensure they're written to disk
        settings.save() 