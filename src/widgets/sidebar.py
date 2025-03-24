import gi
import uuid
import json
import os
import hashlib
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, GObject

class Sidebar(Gtk.Box):
    __gsignals__ = {
        'favorite-selected': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'history-selected': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'favorites-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.set_hexpand(False)
        self.add_css_class("sidebar")
        
        # Set up the data storage paths
        self.data_dir = os.path.join(GLib.get_user_data_dir(), "pixelvault")
        os.makedirs(self.data_dir, exist_ok=True)
        self.favorites_file = os.path.join(self.data_dir, "favorites.json")
        self.history_file = os.path.join(self.data_dir, "history.json")
        
        # Create the stack and stack switcher
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.stack_switcher.set_halign(Gtk.Align.CENTER)
        self.stack_switcher.add_css_class("sidebar-switcher")
        
        # Create favorites list
        self.favorites_list = ImageList()
        self.favorites_list.connect("item-activated", self.on_favorite_activated)
        self.favorites_scroller = Gtk.ScrolledWindow()
        self.favorites_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.favorites_scroller.set_child(self.favorites_list)
        
        # Create history list
        self.history_list = ImageList()
        self.history_list.connect("item-activated", self.on_history_activated)
        self.history_scroller = Gtk.ScrolledWindow()
        self.history_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.history_scroller.set_child(self.history_list)
        
        # Add pages to stack
        self.stack.add_titled(self.favorites_scroller, "favorites", "Favorites")
        self.stack.add_titled(self.history_scroller, "history", "History")
        
        # Add stack switcher and stack to sidebar
        self.append(self.stack_switcher)
        self.append(self.stack)
        
        # Load saved favorites and history
        GLib.idle_add(self.load_favorites)
        GLib.idle_add(self.load_history)
    
    def load_favorites(self):
        """Load favorites from saved file"""
        self.favorites_list.clear()
        
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r') as f:
                    favorites_data = json.load(f)
                    
                for item in favorites_data:
                    self.favorites_list.add_item(item)
                
                print(f"Loaded {len(favorites_data)} favorites from storage")
        except Exception as e:
            print(f"Error loading favorites: {e}")
        
        return False
    
    def save_favorites(self):
        """Save favorites to JSON file"""
        try:
            favorites_data = list(self.favorites_list.items.values())
            
            with open(self.favorites_file, 'w') as f:
                json.dump(favorites_data, f, indent=2)
                
            print(f"Saved {len(favorites_data)} favorites to storage")
            return True
        except Exception as e:
            print(f"Error saving favorites: {e}")
            return False
    
    def load_history(self):
        """Load history from saved file"""
        self.history_list.clear()
        
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history_data = json.load(f)
                    
                for item in history_data:
                    self.history_list.add_item(item)
                
                print(f"Loaded {len(history_data)} history items from storage")
        except Exception as e:
            print(f"Error loading history: {e}")
        
        return False
    
    def save_history(self):
        """Save history to JSON file"""
        try:
            history_data = list(self.history_list.items.values())
            
            with open(self.history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
            print(f"Saved {len(history_data)} history items to storage")
            return True
        except Exception as e:
            print(f"Error saving history: {e}")
            return False
    
    def add_to_favorites(self, image_data):
        # Make a deep copy to prevent reference issues
        image_copy = image_data.copy()
        
        # Ensure image has an ID
        if not image_copy.get("id"):
            image_copy["id"] = str(uuid.uuid4())
            
        self.favorites_list.add_item(image_copy)
        self.save_favorites()
        
        # Emit signal about favorites changing
        self.emit("favorites-changed")
    
    def remove_from_favorites(self, image_data):
        self.favorites_list.remove_item(image_data)
        self.save_favorites()
        
        # Emit signal about favorites changing
        self.emit("favorites-changed")
    
    def add_to_history(self, image_data):
        # Make a deep copy to prevent reference issues
        image_copy = image_data.copy()
        
        # Ensure image has an ID
        if not image_copy.get("id"):
            image_copy["id"] = str(uuid.uuid4())
            
        self.history_list.add_item(image_copy)
        self.save_history()
    
    def is_in_favorites(self, image_data):
        return self.favorites_list.contains_item(image_data)
    
    def on_favorite_activated(self, image_list, image_data):
        # Ensure we have all the required data
        if image_data:
            # Make sure essential fields are present
            if not image_data.get("id"):
                image_data["id"] = str(uuid.uuid4())
                
            if not image_data.get("url") and image_data.get("thumbnail"):
                image_data["url"] = image_data["thumbnail"]
                
            if not image_data.get("thumbnail") and image_data.get("url"):
                image_data["thumbnail"] = image_data["url"]
                
            # Now emit the signal with the properly formatted data
            self.emit("favorite-selected", image_data)
    
    def on_history_activated(self, image_list, image_data):
        # Similar check for history items
        if image_data:
            # Make sure essential fields are present
            if not image_data.get("id"):
                image_data["id"] = str(uuid.uuid4())
                
            if not image_data.get("url") and image_data.get("thumbnail"):
                image_data["url"] = image_data["thumbnail"]
                
            if not image_data.get("thumbnail") and image_data.get("url"):
                image_data["thumbnail"] = image_data["url"]
                
            # Now emit the signal with the properly formatted data
            self.emit("history-selected", image_data)

class ImageList(Gtk.ListView):
    __gsignals__ = {
        'item-activated': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    
    def __init__(self):
        # Create a list store
        self.store = Gtk.StringList()
        
        # Create a selection model
        self.selection_model = Gtk.SingleSelection.new(self.store)
        
        # Create a signal list item factory
        self.factory = Gtk.SignalListItemFactory()
        self.factory.connect("setup", self._on_factory_setup)
        self.factory.connect("bind", self._on_factory_bind)
        
        # Initialize ListView
        super().__init__(
            model=self.selection_model,
            factory=self.factory
        )
        
        self.connect("activate", self._on_item_activated)
        
        # Dictionary to store image data by ID
        self.items = {}
        
        # Create a temporary directory for thumbnails
        self.thumb_dir = os.path.join(GLib.get_user_cache_dir(), "pixelvault", "thumbnails")
        os.makedirs(self.thumb_dir, exist_ok=True)
    
    def _on_factory_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        
        image = Gtk.Image()
        image.set_size_request(50, 50)
        
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        
        box.append(image)
        box.append(label)
        
        list_item.set_child(box)
    
    def _on_factory_bind(self, factory, list_item):
        box = list_item.get_child()
        image = box.get_first_child()
        label = image.get_next_sibling()
        
        item_id = self.store.get_string(list_item.get_position())
        item_data = self.items.get(item_id)
        
        if item_data:
            # Set title with source info
            title = item_data.get("title", "Unknown")
            source = item_data.get("source", "unknown")
            source_display = self._get_source_display_name(source)
            label.set_text(f"{title} ({source_display})")
            
            # Try to load thumbnail if available
            thumbnail_url = item_data.get("thumbnail")
            if thumbnail_url:
                # Start a thread to load the thumbnail
                GLib.idle_add(self._load_thumbnail, thumbnail_url, image)
    
    def _get_source_display_name(self, source_id):
        """Convert source ID to a friendly display name."""
        source_names = {
            "wallhaven": "Wallhaven",
            "waifu_im": "Waifu.im",
            "waifu_pics": "Waifu.pics",
            "nekos_moe": "Nekos.moe"
        }
        return source_names.get(source_id, source_id.capitalize())
    
    def _load_thumbnail(self, url, image_widget):
        """Load a thumbnail from URL and set it to the image widget."""
        try:
            from gi.repository import GdkPixbuf
            import tempfile
            import threading
            import aiohttp
            import asyncio
            
            # Create a unique filename for this thumbnail
            filename = os.path.basename(url)
            cache_path = os.path.join(self.thumb_dir, filename)
            
            # Check if thumbnail is already cached
            if os.path.exists(cache_path):
                # Load from cache
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    cache_path, 50, 50, True
                )
                image_widget.set_from_pixbuf(pixbuf)
            else:
                # Need to download it
                def download_thread():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def download():
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as response:
                                    if response.status == 200:
                                        with tempfile.NamedTemporaryFile(delete=False) as temp:
                                            temp_path = temp.name
                                            temp.write(await response.read())
                                        
                                        # Now load the image and resize it
                                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                            temp_path, 50, 50, True
                                        )
                                        
                                        # Save to cache
                                        pixbuf.savev(cache_path, "png", [], [])
                                        
                                        # Update the UI
                                        GLib.idle_add(image_widget.set_from_pixbuf, pixbuf)
                                        
                                        # Clean up
                                        os.unlink(temp_path)
                        except Exception as e:
                            print(f"Error loading thumbnail: {e}")
                    
                    loop.run_until_complete(download())
                    loop.close()
                
                # Start download in a thread
                threading.Thread(target=download_thread, daemon=True).start()
                
        except Exception as e:
            print(f"Error setting up thumbnail: {e}")
        
        return False  # Don't repeat this idle callback
    
    def _on_item_activated(self, listview, position):
        """Handle item activation (double-click or Enter key)."""
        if position < 0 or position >= self.store.get_n_items():
            print(f"Invalid position: {position}")
            return False
            
        item_id = self.store.get_string(position)
        if not item_id:
            print(f"No item at position {position}")
            return False
            
        print(f"Activating item with ID: {item_id}")
        print(f"Available item IDs: {list(self.items.keys())}")
            
        image_data = self.items.get(item_id)
        if not image_data:
            print(f"No image data for item {item_id}")
            return False
            
        # Make sure we have all required fields
        if not image_data.get("id"):
            image_data["id"] = str(uuid.uuid4())
        
        if not image_data.get("url") and image_data.get("thumbnail"):
            image_data["url"] = image_data["thumbnail"]
        
        if not image_data.get("thumbnail") and image_data.get("url"):
            image_data["thumbnail"] = image_data["url"]
            
        # Emit the signal with the image data
        self.emit("item-activated", image_data)
        return True
    
    def add_item(self, image_data):
        if not image_data:
            return False
        
        # Ensure we have a copy to avoid reference issues
        image_data_copy = image_data.copy()
        
        # Create a unique ID for the image if it doesn't have one
        if "id" not in image_data_copy or not image_data_copy["id"]:
            # Generate a unique ID if none exists
            if "url" in image_data_copy:
                image_data_copy["id"] = hashlib.md5(image_data_copy["url"].encode()).hexdigest()
            else:
                # If no URL, create a random ID
                image_data_copy["id"] = str(uuid.uuid4())
        
        # Ensure ID is a string
        if not isinstance(image_data_copy["id"], str):
            image_data_copy["id"] = str(image_data_copy["id"])
        
        # Make sure thumbnail and URL fields exist
        if "thumbnail" not in image_data_copy or not image_data_copy["thumbnail"]:
            if "url" in image_data_copy:
                image_data_copy["thumbnail"] = image_data_copy["url"]
            else:
                return False  # Can't add without either thumbnail or URL
                
        if "url" not in image_data_copy or not image_data_copy["url"]:
            if "thumbnail" in image_data_copy:
                image_data_copy["url"] = image_data_copy["thumbnail"]
            else:
                return False  # Can't add without either URL or thumbnail
        
        # Create a row entry for the image
        if "title" in image_data_copy and image_data_copy["title"]:
            title = image_data_copy["title"]
        else:
            # Extract a title from the URL if none provided
            url_parts = image_data_copy["url"].split("/")
            title = url_parts[-1].split(".")[0]
            image_data_copy["title"] = title
        
        # Store the data and add to model
        self.items[image_data_copy["id"]] = image_data_copy
        self.store.append(image_data_copy["id"])
        
        return True
    
    def remove_item(self, image_data):
        # Try to get ID directly
        image_id = image_data.get("id")
        
        # If not found, try to match by URL
        if not image_id or image_id not in self.items:
            image_url = image_data.get("url")
            if image_url:
                # Look through all items for matching URL
                for id, data in self.items.items():
                    if data.get("url") == image_url:
                        image_id = id
                        break
        
        # If still not found, can't remove
        if not image_id or image_id not in self.items:
            return
        
        # Find the position in the model
        for i in range(self.store.get_n_items()):
            if self.store.get_string(i) == image_id:
                self.store.remove(i)
                break
        
        # Remove from the dictionary
        del self.items[image_id]
    
    def contains_item(self, image_data):
        # First try to match by ID
        image_id = image_data.get("id")
        if image_id and image_id in self.items:
            return True
            
        # If not found by ID, try to match by URL
        image_url = image_data.get("url")
        if image_url:
            for item in self.items.values():
                if item.get("url") == image_url:
                    return True
        
        return False
    
    def clear(self):
        self.items = {}
        while self.store.get_n_items() > 0:
            self.store.remove(0)

    def add_image(self, image_data):
        """
        Alternative name for add_item, for backwards compatibility.
        """
        return self.add_item(image_data) 