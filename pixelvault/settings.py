import os
import json
from pathlib import Path

class Settings:
    """Manages application settings and user preferences."""
    
    def __init__(self):
        """Initialize settings with default values."""
        # Default settings
        self.defaults = {
            "auto_download": False,
            "download_directory": str(Path.home() / "Pictures" / "Pixelvault"),
            "show_auto_download_notification": True,
            "organize_by_source": True,
            "filename_format": "original",
            "wallhaven_api_key": "", 
            "wallhaven_categories": ["general", "anime", "people"],
            "wallhaven_purity": ["sfw"],
            "wallhaven_sorting": "date_added"
        }
        
        # Current settings (start with defaults)
        self.current = self.defaults.copy()
        
        # Create config directory if it doesn't exist
        self.config_dir = os.path.join(str(Path.home()), ".config", "pixelvault")
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Config file path
        self.config_file = os.path.join(self.config_dir, "settings.json")
        
        print(f"Settings initialized, config file: {self.config_file}")
        
        # Load existing settings
        self.load()
    
    def load(self):
        """Load settings from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    # Update current settings with loaded values
                    self.current.update(loaded)
                    print(f"Settings loaded: {self.current}")
            else:
                print(f"No settings file found, using defaults: {self.current}")
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save(self):
        """Save current settings to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.current, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk
            print(f"Settings saved: {self.current}")
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key, default=None):
        """Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            The setting value
        """
        value = self.current.get(key, default)
        return value
    
    def set(self, key, value):
        """Set a setting value and save settings.
        
        Args:
            key: Setting key
            value: Setting value
        """
        # Check if value changed
        old_value = self.current.get(key)
        if old_value != value:
            print(f"Setting '{key}' changed: {old_value} -> {value}")
            self.current[key] = value
            self.save()
        else:
            print(f"Setting '{key}' unchanged: {value}")
    
    def reset(self):
        """Reset settings to defaults."""
        print("Resetting all settings to defaults")
        self.current = self.defaults.copy()
        self.save()

# Singleton instance
settings = Settings() 