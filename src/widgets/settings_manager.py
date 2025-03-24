import os
import json
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib

class SettingsManager:
    """Manages application settings and persists them to disk."""
    
    def __init__(self):
        # Define default settings
        self.defaults = {
            "auto_cache": True,
            "theme": "dark",
            "sidebar_width": 250,
            "thumbnail_size": 200,
            "grid_columns": 4,
            "cache_size_limit": 500,  # MB
            "last_source": "wallhaven"
        }
        
        # Set up paths
        self.config_dir = os.path.join(GLib.get_user_config_dir(), "pixelvault")
        self.settings_file = os.path.join(self.config_dir, "settings.json")
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load settings or create defaults
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Load settings from file or create default if file doesn't exist."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Merge with defaults to handle missing keys in saved settings
                merged_settings = self.defaults.copy()
                merged_settings.update(settings)
                return merged_settings
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        # If loading fails or file doesn't exist, return defaults
        return self.defaults.copy()
    
    def save_settings(self):
        """Save current settings to disk."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a setting value."""
        return self.settings.get(key, default if default is not None else self.defaults.get(key))
    
    def set(self, key, value):
        """Set a setting value and save to disk."""
        self.settings[key] = value
        return self.save_settings()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.settings = self.defaults.copy()
        return self.save_settings()