import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GObject, GLib, GdkPixbuf, Gdk, Gio

import threading
import asyncio
import aiohttp
import aiofiles
import os
import io
import json
import tempfile
from PIL import Image as PILImage
from urllib.parse import urlparse, quote_plus

from src.widgets.api_clients import (
    WallhavenClient,
    WaifuImClient,
    WaifuPicsClient,
    NekosMoeClient
)

class ImageGrid(Gtk.GridView):
    __gsignals__ = {
        'image-clicked': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    
    def __init__(self):
        # Create a store and factory for the grid items
        self.store = Gio.ListStore.new(GridItem)
        
        # For this demo we'll use a signal factory instead of builder factory
        self.factory = Gtk.SignalListItemFactory()
        self.factory.connect("setup", self._on_factory_setup)
        self.factory.connect("bind", self._on_factory_bind)
        
        # Create selection model
        self.selection_model = Gtk.NoSelection.new(self.store)
        
        # Initialize GridView
        super().__init__(
            model=self.selection_model,
            factory=self.factory,
            min_columns=2,
            max_columns=6
        )
        
        # Set properties
        self.set_valign(Gtk.Align.START)
        
        # Connect signals
        self.connect("activate", self._on_item_activated)
        
        # Initialize API clients
        self.clients = {
            "wallhaven": WallhavenClient(),
            "waifu_im": WaifuImClient(),
            "waifu_pics": WaifuPicsClient(),
            "nekos_moe": NekosMoeClient()
        }
        
        # Create cache directory
        self.cache_dir = os.path.expanduser("~/.cache/pixelvault")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Properties to track current state
        self.current_source = None
        self.current_page = 1
        self.current_search = ""
        self.current_tag = ""
        self.is_loading = False
        self.auto_cache_enabled = True
        
        # Set minimum size for each item
        self.set_min_columns(2)
    
    def _on_factory_setup(self, factory, list_item):
        # Create a box to hold the image and label
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_halign(Gtk.Align.FILL)
        box.set_valign(Gtk.Align.FILL)
        
        # Create image widget
        image = Gtk.Picture()
        image.set_size_request(200, 200)
        image.set_content_fit(Gtk.ContentFit.COVER)
        
        # Create label for title/metadata
        label = Gtk.Label()
        label.set_ellipsize(True)
        label.set_max_width_chars(20)
        label.set_halign(Gtk.Align.START)
        
        # Create an overlay for the image, to add a button to favorite it later
        overlay = Gtk.Overlay()
        overlay.set_child(image)
        
        # Add to box
        box.append(overlay)
        box.append(label)
        
        # Add gesture to make item clickable
        click_gesture = Gtk.GestureClick.new()
        click_gesture.connect("released", self._on_item_clicked, list_item)
        box.add_controller(click_gesture)
        
        list_item.set_child(box)
    
    def _on_factory_bind(self, factory, list_item):
        # Get the corresponding grid item
        item = list_item.get_item()
        
        # Get the child widgets
        box = list_item.get_child()
        overlay = box.get_first_child()
        image = overlay.get_child()
        label = box.get_last_child()
        
        # Update the image and label
        if item.thumbnail:
            image.set_paintable(item.thumbnail)
        
        if item.title:
            label.set_text(item.title)
    
    def _on_item_clicked(self, gesture, n_press, x, y, list_item):
        # Get the clicked item
        position = list_item.get_position()
        if position < 0 or position >= self.store.get_n_items():
            return
            
        item = self.store.get_item(position)
        if item and item.data:
            self.emit("image-clicked", item.data)
    
    def _on_item_activated(self, grid_view, position):
        # Get the activated item
        if position < 0 or position >= self.store.get_n_items():
            return
            
        item = self.store.get_item(position)
        if item and item.data:
            self.emit("image-clicked", item.data)
    
    def load_images_from_source(self, source_id):
        # Reset state for new source
        self.current_source = source_id
        self.current_page = 1
        self.current_search = ""
        self.current_tag = ""
        
        # Clear existing images
        self.store.remove_all()
        
        # Cancel any ongoing loading
        self.is_loading = False
        
        # Schedule loading with a short delay to ensure previous loads are stopped
        GLib.timeout_add(100, self._delayed_load_images)
    
    def _delayed_load_images(self):
        # This runs after a short delay to ensure clean switching
        self._load_images()
        return False  # Don't repeat the timeout
    
    def load_more_images(self, source_id):
        # Check if we're already at the right source
        if self.current_source != source_id or self.is_loading:
            return
        
        # Increment page and load more
        self.current_page += 1
        self._load_images()
    
    def filter_images(self, search_query):
        """
        Filter images based on a search query.
        """
        search_query = search_query.lower().strip()
        
        # Log filtering action for debugging
        print(f"Filtering images with query: '{search_query}'")
        
        # If no search query, update the current search to empty and return
        if not search_query:
            # Clear filter - revert to old behavior
            old_search = self.current_search
            self.current_search = ""
            
            # Only reload if search query actually changed
            if old_search != self.current_search:
                print("Clearing search filter")
                # Clear the store and reload
                self.store.remove_all()
                
                # Set loading to false to ensure we can start a new load
                self.is_loading = False
                
                # Load images with no filter
                self._load_images()
            return
        
        # Store old search for comparison
        old_search = self.current_search
        
        # Check for advanced search operators
        advanced_operators = {
            "ratio:", "width:", "height:", "resolution:", 
            "color:", "source:", "category:", "tag:", "date:",
            "view:", "favorite:", "size:"
        }
        
        has_advanced_query = any(op in search_query for op in advanced_operators)
        
        # Handle advanced search with special operators
        if has_advanced_query and self.store.get_n_items() > 0:
            print(f"Performing advanced filtering with query: '{search_query}'")
            self._advanced_filter(search_query)
            return
            
        # For very short searches (1-2 chars), do local filtering only
        elif len(search_query) <= 2 and self.store.get_n_items() > 0:
            print(f"Local filtering for short query: '{search_query}'")
            self._filter_locally(search_query)
            return
            
        # For slightly longer searches (3-4 chars), combine local and server-side
        elif len(search_query) <= 4 and self.store.get_n_items() > 0:
            # Try local filtering first
            local_results = self._filter_locally(search_query, count_only=True)
            # If we found enough results locally, don't make a server request
            if local_results >= 5:
                print(f"Using local filter results for '{search_query}': found {local_results} matches")
                self._filter_locally(search_query)
                return
        
        # For longer searches or if local filtering didn't find enough results,
        # do a server-side search for better results
        if old_search != search_query:
            # Update current search before reloading
            self.current_search = search_query
            
            # Log the change
            print(f"Changing search filter from '{old_search}' to '{self.current_search}'")
            
            # Clear the store and reload
            self.store.remove_all()
            
            # Set loading to false to ensure we can start a new load
            self.is_loading = False
            
            # Load images with the new filter
            self._load_images()
            
    def _advanced_filter(self, query):
        """
        Handle advanced filtering with special operators.
        
        Supported operators:
        - ratio:16:9 - filter by aspect ratio
        - width:>1920 - filter by width (>, <, =, >=, <= supported)
        - height:>1080 - filter by height
        - resolution:4k - filter by common resolution names
        - color:red - filter by dominant color
        - source:wallhaven - filter by source
        - category:anime - filter by category
        - tag:landscape - filter by specific tag
        - date:>2023-01-01 - filter by date
        - view:>1000 - filter by view count
        - favorite:>100 - filter by favorite count
        - size:>5mb - filter by file size
        """
        total = self.store.get_n_items()
        items_to_remove = []
        
        # Parse query into individual filter terms
        filter_terms = []
        current_term = ""
        in_quotes = False
        
        # Parse quoted terms correctly
        for char in query:
            if char == '"' or char == "'":
                in_quotes = not in_quotes
                current_term += char
            elif char == ' ' and not in_quotes:
                if current_term:
                    filter_terms.append(current_term.strip())
                    current_term = ""
            else:
                current_term += char
                
        # Add the last term if there is one
        if current_term:
            filter_terms.append(current_term.strip())
            
        print(f"Advanced filter terms: {filter_terms}")
        
        # Process each item against all filter terms
        for i in range(total):
            if i >= self.store.get_n_items():
                break
                
            item = self.store.get_item(i)
            if not item or not item.data:
                continue
                
            # Check if this item passes all filters
            matches = True
            
            for term in filter_terms:
                # Skip empty terms
                if not term:
                    continue
                    
                # Check if this is an operator term
                operator_match = False
                
                for op in ["ratio:", "width:", "height:", "resolution:", "color:", 
                           "source:", "category:", "tag:", "date:", "view:", 
                           "favorite:", "size:"]:
                    if term.startswith(op):
                        # Extract the value part
                        value = term[len(op):].strip('"\'')
                        
                        # Process based on operator type
                        if op == "ratio:":
                            # Handle aspect ratio filtering
                            if "ratio" in item.data:
                                item_ratio = item.data["ratio"]
                                if not item_ratio or value.lower() not in item_ratio.lower():
                                    matches = False
                            else:
                                # Calculate ratio from width/height if not already present
                                if "width" in item.data and "height" in item.data:
                                    width = item.data["width"]
                                    height = item.data["height"]
                                    # Simple ratio checks for common formats
                                    if value == "16:9":
                                        ratio = width / height if height else 0
                                        if not (1.7 <= ratio <= 1.8):  # Approximately 16:9
                                            matches = False
                                    elif value == "4:3":
                                        ratio = width / height if height else 0
                                        if not (1.3 <= ratio <= 1.4):  # Approximately 4:3
                                            matches = False
                                    elif value == "1:1":
                                        ratio = width / height if height else 0
                                        if not (0.95 <= ratio <= 1.05):  # Approximately 1:1
                                            matches = False
                                    elif value == "21:9":
                                        ratio = width / height if height else 0
                                        if not (2.3 <= ratio <= 2.4):  # Approximately 21:9
                                            matches = False
                                else:
                                    matches = False
                                    
                        elif op == "width:" or op == "height:":
                            # Handle dimension filtering with comparisons
                            dimension_key = "width" if op == "width:" else "height"
                            if dimension_key in item.data and item.data[dimension_key]:
                                item_dim = int(item.data[dimension_key])
                                
                                # Parse comparison operators
                                if value.startswith(">="): 
                                    target = int(value[2:])
                                    if not (item_dim >= target):
                                        matches = False
                                elif value.startswith("<="): 
                                    target = int(value[2:])
                                    if not (item_dim <= target):
                                        matches = False
                                elif value.startswith(">"): 
                                    target = int(value[1:])
                                    if not (item_dim > target):
                                        matches = False
                                elif value.startswith("<"): 
                                    target = int(value[1:])
                                    if not (item_dim < target):
                                        matches = False
                                elif value.startswith("="): 
                                    target = int(value[1:])
                                    if not (item_dim == target):
                                        matches = False
                                else:
                                    # Default to equality
                                    target = int(value)
                                    if not (item_dim == target):
                                        matches = False
                            else:
                                matches = False
                                
                        elif op == "resolution:":
                            # Handle common resolution names
                            if "width" in item.data and "height" in item.data:
                                width = int(item.data["width"]) if item.data["width"] else 0
                                height = int(item.data["height"]) if item.data["height"] else 0
                                
                                if value.lower() == "4k" or value.lower() == "uhd":
                                    if not (width >= 3840 and height >= 2160):
                                        matches = False
                                elif value.lower() == "1080p" or value.lower() == "fullhd":
                                    if not (1920 <= width <= 1921 and 1080 <= height <= 1081):
                                        matches = False
                                elif value.lower() == "1440p" or value.lower() == "2k":
                                    if not (2560 <= width <= 2561 and 1440 <= height <= 1441):
                                        matches = False
                                elif value.lower() == "720p" or value.lower() == "hd":
                                    if not (1280 <= width <= 1281 and 720 <= height <= 721):
                                        matches = False
                            else:
                                matches = False
                                
                        elif op == "color:":
                            # Handle color filtering
                            if "colors" in item.data and item.data["colors"]:
                                if not any(value.lower() in color.lower() for color in item.data["colors"]):
                                    matches = False
                            else:
                                matches = False
                                
                        elif op == "source:":
                            # Handle source filtering
                            if "source" in item.data:
                                source = item.data["source"].lower()
                                if value.lower() not in source:
                                    matches = False
                            else:
                                matches = False
                                
                        elif op == "category:":
                            # Handle category filtering
                            if "category" in item.data:
                                category = item.data["category"].lower() if item.data["category"] else ""
                                if value.lower() not in category:
                                    matches = False
                            else:
                                matches = False
                                
                        elif op == "tag:":
                            # Handle tag filtering
                            if "tags" in item.data and item.data["tags"]:
                                tags = [tag.lower() for tag in item.data["tags"]]
                                if not any(value.lower() in tag for tag in tags):
                                    matches = False
                            else:
                                matches = False
                        
                        # Mark that we processed an operator
                        operator_match = True
                        break
                
                # If this wasn't an operator term, treat as general search
                if not operator_match:
                    # Check general fields
                    general_match = False
                    
                    # Check title
                    if "title" in item.data and item.data["title"]:
                        if term.lower() in item.data["title"].lower():
                            general_match = True
                            
                    # Check tags
                    if not general_match and "tags" in item.data and item.data["tags"]:
                        tags = [tag.lower() for tag in item.data["tags"]]
                        if any(term.lower() in tag for tag in tags):
                            general_match = True
                            
                    # If no match found for this term, exclude the item
                    if not general_match:
                        matches = False
            
            # If item doesn't match all filters, mark for removal
            if not matches:
                items_to_remove.append(i)
                
        # Remove non-matching items in reverse order to avoid index issues
        for i in reversed(items_to_remove):
            if i < self.store.get_n_items():
                self.store.remove(i)
                
        print(f"Advanced filter results: {total - len(items_to_remove)}/{total} images match the query")
    
    def _filter_locally(self, search_query, count_only=False):
        """
        Apply a local filter to already loaded images.
        If count_only is True, just return the count without modifying the store.
        """
        count = 0
        total = self.store.get_n_items()
        items_to_remove = []
        
        # Prepare a set of search terms for better matching
        search_terms = set(search_query.lower().split())
        
        # Loop through all grid items 
        for i in range(total):
            if i >= self.store.get_n_items():
                break
                
            item = self.store.get_item(i)
            if not item or not item.data:
                continue
                
            # Check if this item matches the search
            matches = False
            
            # Check title with partial matching
            title = item.data.get("title", "").lower()
            if search_query in title:
                matches = True
            else:
                # Try matching individual terms
                title_words = set(title.split())
                if any(term in title for term in search_terms):
                    matches = True
                
            # Check tags with more flexible matching
            if not matches and "tags" in item.data:
                tags = item.data.get("tags", [])
                tag_text = " ".join(tag.lower() for tag in tags)
                
                # Try exact match first
                if search_query in tag_text:
                    matches = True
                else:
                    # Try partial matching for each tag
                    for tag in tags:
                        tag_lower = tag.lower()
                        # Check if any search term is in this tag
                        if any(term in tag_lower for term in search_terms):
                            matches = True
                            break
            
            # Check other metadata fields
            if not matches:
                # Check category
                if "category" in item.data and item.data["category"]:
                    category = item.data["category"].lower()
                    if search_query in category:
                        matches = True
                
                # Check aspect ratio
                if not matches and "ratio" in item.data and item.data["ratio"]:
                    ratio = item.data["ratio"].lower()
                    if search_query in ratio:
                        matches = True
                
                # Check source
                if not matches and "source" in item.data and item.data["source"]:
                    source = item.data["source"].lower()
                    if search_query in source:
                        matches = True
                
                # Check if it's a color search
                if not matches and "colors" in item.data and item.data["colors"]:
                    colors = [c.lower() for c in item.data["colors"]]
                    if any(search_query in c for c in colors):
                        matches = True
                        
            # Track matches
            if matches:
                count += 1
            elif not count_only:
                items_to_remove.append(i)
        
        # If we're only counting, return the count
        if count_only:
            print(f"Local filter count: {count}/{total} images match '{search_query}'")
            return count
                
        # Remove non-matching items in reverse order to avoid index issues
        for i in reversed(items_to_remove):
            if i < self.store.get_n_items():
                self.store.remove(i)
                
        print(f"Local filter results: {count}/{total} images match the query '{search_query}'")
        return count
    
    def filter_by_tag(self, tag, source_id):
        # Only filter if the source matches
        if self.current_source != source_id:
            print(f"Source mismatch in filter_by_tag: current={self.current_source}, requested={source_id}")
            return
        
        # Update tag and reset page
        tag_changed = self.current_tag != (tag.lower() if tag else "")
        self.current_tag = tag.lower() if tag else ""
        self.current_page = 1
        
        # Log the tag filter
        if tag:
            print(f"Filtering by tag '{tag}' in source: {source_id}")
        else:
            print(f"Clearing tag filter for source: {source_id}")
        
        # Only reload if tag actually changed
        if tag_changed:
            # Force stop any current loading
            self.is_loading = False
            
            # Clear and reload
            self.store.remove_all()
            self._load_images()
        else:
            print(f"Tag filter unchanged ('{self.current_tag}'), not reloading")
    
    def _load_images(self):
        if self.is_loading or not self.current_source:
            return
        
        # Set loading state
        self.is_loading = True
        
        # Log loading information
        source_id = self.current_source
        print(f"Loading images from source: {source_id}, page: {self.current_page}")
        
        # Get the appropriate client
        client = self.clients.get(source_id)
        if not client:
            print(f"Error: No client found for source {source_id}")
            self.is_loading = False
            return
        
        # If we're loading the first page, clear existing images
        if self.current_page == 1:
            self.store.remove_all()
        
        # Start a new thread for loading
        try:
            thread = threading.Thread(
                target=self._run_async_load,
                args=(client,),
                daemon=True
            )
            thread.start()
        except Exception as e:
            print(f"Error starting load thread: {e}")
            self.is_loading = False
    
    def _run_async_load(self, client):
        # Store the source we're loading for later verification
        source_id = self.current_source
        
        # Create and run async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                self._async_load_images(client, source_id)
            )
        finally:
            loop.close()
    
    async def _async_load_images(self, client, source_id):
        try:
            # Safety check - if the source has changed since we started, abort
            if source_id != self.current_source:
                print(f"Source changed during loading (was: {source_id}, now: {self.current_source}), aborting.")
                return
                
            # Fetch images from API
            images = await client.get_images(
                page=self.current_page,
                query=self.current_search,
                tag=self.current_tag
            )
            
            # For each image, create a grid item and add to store
            for image in images:
                # Double check that we're still on the same source
                if source_id != self.current_source:
                    print(f"Source changed during processing (was: {source_id}, now: {self.current_source}), aborting.")
                    return
                    
                # Strict verification that this image belongs to the correct source
                # The source must be an exact match with the source_id
                image_source = image.get("source", "")
                if image_source != source_id:
                    print(f"Skipping image from wrong source: '{image_source}' (expected: '{source_id}')")
                    continue
                    
                await self._add_image_to_grid(image)
                
        except Exception as e:
            print(f"Error loading images: {e}")
        
        finally:
            # Mark loading as complete
            GLib.idle_add(self._mark_loading_complete)
    
    def _mark_loading_complete(self):
        self.is_loading = False
        return False
    
    async def _add_image_to_grid(self, image_data):
        # Create a new grid item
        item = GridItem()
        item.data = image_data
        item.thumbnail = None
        
        # Check if there's a valid thumbnail URL
        thumbnail_url = image_data.get("thumbnail")
        if not thumbnail_url:
            # Try to use main image url if thumbnail not available
            thumbnail_url = image_data.get("url")
        
        # If the image has a valid URL, cache it
        if thumbnail_url:
            # Cache the thumbnail
            cached_path = await self._cache_image(thumbnail_url)
            
            if cached_path:
                # Load the thumbnail in a non-blocking way
                def do_load_thumbnail():
                    # Load thumbnail and get the texture
                    thumbnail = self._load_thumbnail(cached_path, item)
                    
                    # Add the loaded item to the grid from the main thread
                    def add_item_to_grid(thumbnail):
                        if thumbnail:
                            item.thumbnail = thumbnail
                        
                        # Add item to the store
                        self.store.append(item)
                        
                        # Force a refresh of the grid
                        self.queue_draw()
                    
                    # Schedule adding to the grid on the main thread
                    GLib.idle_add(add_item_to_grid, thumbnail)
                    
                # Start a thread to load the thumbnail
                thread = threading.Thread(target=do_load_thumbnail)
                thread.daemon = True
                thread.start()
            else:
                # Add without a thumbnail if caching failed
                self.store.append(item)
        else:
            # Add without a thumbnail if no URL
            self.store.append(item)
    
    def _load_thumbnail(self, local_path, item):
        """
        Load a thumbnail from a local file.
        """
        if not os.path.exists(local_path):
            print(f"Error: thumbnail file not found: {local_path}")
            return None
            
        try:
            # Load the image with PILImage first
            pil_image = PILImage.open(local_path)
            
            # Extract metadata from the image if available
            metadata = self._extract_metadata_from_image(pil_image, local_path)
            if metadata:
                # Update item data with metadata
                if item.data and isinstance(item.data, dict):
                    if "colors" not in item.data or not item.data["colors"]:
                        item.data["colors"] = metadata.get("colors", [])
                    if "width" not in item.data or not item.data["width"]:
                        item.data["width"] = metadata.get("width")
                    if "height" not in item.data or not item.data["height"]:
                        item.data["height"] = metadata.get("height")
                    if "ratio" not in item.data or not item.data["ratio"]:
                        item.data["ratio"] = metadata.get("ratio")
                    if "file_size" not in item.data:
                        item.data["file_size"] = metadata.get("file_size")
                
            # Convert to GdkPixbuf format for GTK
            width, height = pil_image.size
            has_alpha = pil_image.mode == 'RGBA'
            
            if pil_image.mode != 'RGBA' and pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                
            # Scale down large images to conserve memory
            max_size = 500
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                pil_image = pil_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                width, height = pil_image.size
            
            # Convert to bytes
            if has_alpha:
                pil_bytes = pil_image.tobytes()
                pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
                    GLib.Bytes.new(pil_bytes),
                    GdkPixbuf.Colorspace.RGB,
                    True,
                    8,
                    width,
                    height,
                    width * 4
                )
            else:
                pil_bytes = pil_image.tobytes()
                pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
                    GLib.Bytes.new(pil_bytes),
                    GdkPixbuf.Colorspace.RGB,
                    False,
                    8,
                    width,
                    height,
                    width * 3
                )
                
            # Create a texture from the pixbuf
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            return texture
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            return None
            
    def _extract_metadata_from_image(self, pil_image, file_path):
        """
        Extract useful metadata from an image file that can be used for filtering.
        
        Args:
            pil_image: PIL Image object
            file_path: Path to the image file
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        try:
            # Basic properties
            width, height = pil_image.size
            metadata["width"] = width
            metadata["height"] = height
            
            # Calculate aspect ratio
            def gcd(a, b):
                while b:
                    a, b = b, a % b
                return a
                
            divisor = gcd(width, height)
            if divisor > 0:
                ratio_w = width // divisor
                ratio_h = height // divisor
                
                # Handle common ratios
                if (ratio_w, ratio_h) == (16, 9):
                    metadata["ratio"] = "16:9"
                elif (ratio_w, ratio_h) == (4, 3):
                    metadata["ratio"] = "4:3"
                elif (ratio_w, ratio_h) == (21, 9):
                    metadata["ratio"] = "21:9"
                elif (ratio_w, ratio_h) == (1, 1):
                    metadata["ratio"] = "1:1"
                else:
                    metadata["ratio"] = f"{ratio_w}:{ratio_h}"
            
            # Get file size
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                # Convert to appropriate unit
                if file_size < 1024:
                    metadata["file_size"] = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    metadata["file_size"] = f"{file_size / 1024:.1f} KB"
                else:
                    metadata["file_size"] = f"{file_size / (1024 * 1024):.1f} MB"
                    
            # Extract dominant colors
            try:
                # Resize for faster processing
                img_for_colors = pil_image.copy()
                img_for_colors.thumbnail((100, 100))
                
                if img_for_colors.mode != 'RGB':
                    img_for_colors = img_for_colors.convert('RGB')
                
                # Get pixel data
                pixels = list(img_for_colors.getdata())
                
                # Count colors (simplistic approach)
                color_counts = {}
                for pixel in pixels:
                    if pixel in color_counts:
                        color_counts[pixel] += 1
                    else:
                        color_counts[pixel] = 1
                
                # Get most common colors
                common_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                # Map RGB values to color names (simplified)
                def get_color_name(rgb):
                    r, g, b = rgb
                    
                    # Simplified color mapping
                    if max(r, g, b) < 50:
                        return "black"
                    elif min(r, g, b) > 200:
                        return "white"
                    
                    if r > max(g, b) + 50:
                        return "red"
                    elif g > max(r, b) + 50:
                        return "green"
                    elif b > max(r, g) + 50:
                        return "blue"
                    elif r > 200 and g > 150 and b < 100:
                        return "yellow"
                    elif r > 200 and g < 100 and b > 150:
                        return "purple"
                    elif r > 200 and g < 150 and b < 100:
                        return "orange"
                    elif r > 150 and g < 100 and b < 100:
                        return "brown"
                    elif r > 200 and g > 100 and b > 150:
                        return "pink"
                    
                    return "gray"
                
                # Get color names
                metadata["colors"] = [get_color_name(rgb) for rgb, _ in common_colors]
                # Remove duplicates while preserving order
                metadata["colors"] = list(dict.fromkeys(metadata["colors"]))
                
            except Exception as e:
                print(f"Error extracting colors: {e}")
            
            return metadata
            
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return metadata
    
    async def _cache_image(self, url):
        if not url:
            return None
            
        # Generate a cache filename
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # If filename is empty or invalid, use a hash of the URL
        if not filename or len(filename) < 3:
            import hashlib
            filename = hashlib.md5(url.encode()).hexdigest() + ".jpg"
            
        cache_path = os.path.join(self.cache_dir, filename)
        
        # Check if already cached
        if os.path.exists(cache_path):
            return cache_path
        
        # If auto-caching is disabled, download to a temporary file instead
        if not self.auto_cache_enabled:
            try:
                # Create a temporary file
                temp_path = os.path.join(tempfile.gettempdir(), f"pixelvault_temp_{filename}")
                
                async with aiohttp.ClientSession() as session:
                    print(f"Loading image without caching: {url}")
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.read()
                            async with aiofiles.open(temp_path, "wb") as f:
                                await f.write(data)
                            print(f"Loaded image to temporary file: {temp_path}")
                            return temp_path
                        else:
                            print(f"Failed to load image {url}: Status {response.status}")
                            return None
            except Exception as e:
                print(f"Error loading image temporarily {url}: {e}")
                return None
            
        # Download and cache the image
        try:
            async with aiohttp.ClientSession() as session:
                print(f"Downloading image from: {url}")
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.read()
                        
                        # Validate image data
                        try:
                            # Write to a temporary file first to validate
                            temp_file = os.path.join(self.cache_dir, f"temp_{filename}")
                            async with aiofiles.open(temp_file, "wb") as f:
                                await f.write(data)
                            
                            # Try to load with PIL to validate it's an image
                            try:
                                with PILImage.open(temp_file) as img:
                                    # Save in the right format based on image type
                                    if img.format == "JPEG" or img.format == "JPG":
                                        img.save(cache_path, "JPEG")
                                    elif img.format == "PNG":
                                        img.save(cache_path, "PNG")
                                    elif img.format == "GIF":
                                        img.save(cache_path, "GIF")
                                    elif img.format == "WEBP":
                                        img.save(cache_path, "WEBP")
                                    else:
                                        # Default to JPEG for unknown formats
                                        img.save(cache_path, "JPEG")
                                
                                # Remove temp file if successful
                                os.remove(temp_file)
                                print(f"Successfully cached image to: {cache_path}")
                                return cache_path
                            except Exception as e:
                                print(f"Invalid image data from {url}: {e}")
                                # Clean up temp file
                                if os.path.exists(temp_file):
                                    os.remove(temp_file)
                                    
                                # As a fallback, try to save the raw data
                                try:
                                    async with aiofiles.open(cache_path, "wb") as f:
                                        await f.write(data)
                                    print(f"Saved raw data for {url} as fallback")
                                    return cache_path
                                except:
                                    return None
                                
                        except Exception as e:
                            print(f"Error processing image from {url}: {e}")
                            return None
                    else:
                        print(f"Failed to download image {url}: Status {response.status}")
        except Exception as e:
            print(f"Error caching image {url}: {e}")
            return None

    def set_auto_cache(self, enabled):
        """Enable or disable automatic image caching."""
        self.auto_cache_enabled = enabled
        print(f"Auto-caching {'enabled' if enabled else 'disabled'}")
    
    def clear_cache(self):
        """Clear all cached images."""
        try:
            # Create a thread to avoid blocking the UI
            threading.Thread(
                target=self._run_clear_cache,
                daemon=True
            ).start()
        except Exception as e:
            print(f"Error clearing cache: {e}")
    
    def _run_clear_cache(self):
        try:
            # Get list of all files in cache directory
            file_count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.startswith("temp_"):
                    continue  # Skip temporary files
                
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    file_count += 1
            
            print(f"Cleared {file_count} files from cache")
            
            # Reload current images
            GLib.idle_add(self.load_images_from_source, self.current_source)
        except Exception as e:
            print(f"Error in _run_clear_cache: {e}")

class GridItem(GObject.Object):
    """Represents an item in the image grid."""
    
    def __init__(self):
        super().__init__()
        self.data = None       # Original image data
        self.thumbnail = None  # Gdk.Texture
        self.title = ""        # Title/caption