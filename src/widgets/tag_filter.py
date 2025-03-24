import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GObject, Gdk

class TagFilter(Gtk.Box):
    __gsignals__ = {
        'tag-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.add_css_class("tag-filter")
        self.set_hexpand(True)
        
        # Create a flowbox to contain the tags
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(20)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(False)
        self.flowbox.set_activate_on_single_click(True)
        self.flowbox.connect("child-activated", self.on_tag_activated)
        
        # Create a scrolled window for the flowbox
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_hexpand(True)
        self.scrolled.set_max_content_height(60)
        self.scrolled.set_min_content_height(60)
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.scrolled.set_child(self.flowbox)
        
        # Add the scrolled window to this box
        self.append(self.scrolled)
        
        # Dictionary of tags for each source - expand to include more meaningful tags
        self.source_tags = {
            # Wallhaven categories, purity filters, and specific content tags
            "wallhaven": [
                # Categories
                "general", "anime", "people", 
                # Content types
                "landscape", "nature", "space", "city", 
                "abstract", "dark", "sci-fi", "cyberpunk", 
                "fantasy", "gaming", "car", "animal",
                # Purity
                "SFW", "sketchy",
                # Colors
                "red", "blue", "green", "yellow", "purple", 
                "pink", "orange", "brown", "black", "white",
                # Specific themes
                "portrait", "sunset", "beach", "night", 
                "water", "forest", "winter", "summer", 
                "flowers", "architecture", "minimal", 
                "technology", "food", "music"
            ],
            
            # Waifu.im categories - include all valid tags from API
            "waifu_im": [
                "waifu", "maid", "marin-kitagawa", 
                "mori-calliope", "raiden-shogun", 
                "oppai", "selfies", "uniform", "school", 
                "glasses", "elf", "kemonomimi", "fox-girl", 
                "blonde", "student", "dress", "swimsuit",
                "happy", "sad", "angry", "cute", "warm", "cool",
                "casual", "formal", "outdoor", "indoor",
                "sports", "reading", "gaming"
            ],
            
            # Waifu.pics categories - most common tags
            "waifu_pics": [
                "waifu", "neko", "shinobu", "megumin", 
                "cuddle", "hug", "kiss", "smile", "blush", 
                "happy", "cry", "dance", "pout", "highfive", 
                "bite", "slap", "kick", "handhold", "wink", 
                "bully", "pat", "kill", "yeet", "bonk"
            ],
            
            # Nekos.moe categories
            "nekos_moe": [
                "neko", "cat", "catgirl", "ears", "tail", 
                "kemonomimi", "cute", "moe", "animated", "lewd",
                "green_eyes", "blue_eyes", "red_eyes", "blonde",
                "brown_hair", "black_hair", "white_hair", "pink_hair",
                "smile", "school_uniform", "dress", "headband",
                "indoor", "outdoor", "happy", "sad"
            ]
        }
        
        # Keep track of current source and selected tag
        self.current_source = None
        self.current_tag = None
        self.active_button = None
        
        # Set up initial tags for default source
        self.update_tags_for_source("wallhaven")
    
    def update_tags_for_source(self, source_id):
        # Save current source
        self.current_source = source_id
        self.current_tag = ""
        
        # Clear existing tags
        self.clear_tags()
        
        # Add "All" tag first
        self.add_tag("All")
        
        # Add tags for the selected source
        if source_id in self.source_tags:
            for tag in self.source_tags[source_id]:
                self.add_tag(tag)
        
        # Reset the selection to "All" (no filter)
        self.reset_selection()
        
        # Emit a clear filter signal
        self.emit("tag-selected", "")
    
    def clear_tags(self):
        while True:
            child = self.flowbox.get_first_child()
            if child:
                self.flowbox.remove(child)
            else:
                break
    
    def add_tag(self, tag_name):
        # Create a toggle button for the tag
        button = Gtk.ToggleButton(label=tag_name)
        button.add_css_class("tag-button")
        
        # If this is the "All" tag, set it as active initially
        if tag_name == "All":
            button.set_active(True)
            
        # Add tooltip to describe what the tag does
        tooltip = self._get_tag_tooltip(tag_name)
        if tooltip:
            button.set_tooltip_text(tooltip)
            
        # Connect to the toggled signal
        button.connect("toggled", self._on_tag_button_toggled)
        
        # Add the button to the flowbox
        self.flowbox.append(button)
    
    def _get_tag_tooltip(self, tag_name):
        """Provide helpful tooltips for tags to improve usability"""
        if tag_name == "All":
            return "Show all images without filtering"
            
        tag_lower = tag_name.lower()
        
        # Category tooltips
        if tag_lower in ["general", "anime", "people"]:
            return f"Show only {tag_lower} images"
            
        # Purity tooltips
        if tag_lower == "sfw":
            return "Show only safe-for-work images"
        elif tag_lower == "sketchy":
            return "Show images that may contain suggestive content"
            
        # Color tooltips
        if tag_lower in ["red", "blue", "green", "yellow", "purple", "pink", "orange", "brown", "black", "white"]:
            return f"Show images where {tag_lower} is a dominant color"
            
        # Default tooltip
        return f"Filter images by '{tag_name}' tag"
    
    def _on_tag_button_toggled(self, button):
        # Only process if the button is being activated
        if button.get_active():
            tag = button.get_label()
            print(f"Tag button '{tag}' activated")
            
            # Store this as the active button
            self.active_button = button
            
            # Deactivate all other buttons
            child = self.flowbox.get_first_child()
            while child:
                child_button = child.get_child()
                if child_button != button:
                    # Set active to false while blocking signals to avoid recursion
                    with child_button.freeze_notify():
                        child_button.set_active(False)
                child = child.get_next_sibling()
            
            # Apply CSS class to highlight this button
            button.add_css_class("tag-button-active")
            
            # Handle "All" tag differently
            if tag == "All":
                tag = ""
                
            # Update current tag and emit signal
            if tag != self.current_tag:
                self.current_tag = tag
                print(f"Emitting tag-selected signal with tag: '{tag}'")
                self.emit("tag-selected", tag)
        elif button.get_label() == "All":
            # Don't allow deactivating the "All" button without another being active
            print("Preventing 'All' tag deactivation")
            button.set_active(True)
        else:
            # For non-All buttons that are deactivated, go back to "All"
            print(f"Tag button '{button.get_label()}' deactivated, switching to 'All'")
            button.remove_css_class("tag-button-active")
            self.reset_selection()
    
    def on_tag_activated(self, flowbox, child):
        # Get the selected tag's button
        button = child.get_child()
        button_label = button.get_label()
        
        print(f"Tag '{button_label}' activated via flowbox")
        
        # Don't do anything if the button is already active
        if button.get_active():
            print(f"Tag '{button_label}' already active, ignoring")
            return
            
        # Set it as active (which will trigger the toggled signal)
        button.set_active(True)
    
    def reset_selection(self):
        # Find the "All" button and set it as active
        child = self.flowbox.get_first_child()
        while child:
            button = child.get_child()
            if button.get_label() == "All":
                # Store as active button
                self.active_button = button
                button.set_active(True)
                button.add_css_class("tag-button-active")
                break
            elif self.active_button and button == self.active_button:
                button.remove_css_class("tag-button-active")
            child = child.get_next_sibling()
            
        # Reset current tag
        self.current_tag = ""
    
    def select_tag(self, tag_name):
        """Programmatically select a tag by name"""
        print(f"Attempting to select tag: '{tag_name}'")
        
        # Clear the active button's styling if exists
        if self.active_button:
            self.active_button.remove_css_class("tag-button-active")
            
        # If tag is empty, select the "All" tag
        if not tag_name:
            self.reset_selection()
            return True
            
        # First look for the exact tag name
        child = self.flowbox.get_first_child()
        while child:
            button = child.get_child()
            if button.get_label() == tag_name:
                self.active_button = button
                button.set_active(True)
                button.add_css_class("tag-button-active")
                return True
            child = child.get_next_sibling()
            
        # If tag not found exactly, try case-insensitive match
        child = self.flowbox.get_first_child()
        while child:
            button = child.get_child()
            if button.get_label().lower() == tag_name.lower():
                self.active_button = button
                button.set_active(True)
                button.add_css_class("tag-button-active")
                return True
            child = child.get_next_sibling()
            
        # Try partial matching for more flexibility
        child = self.flowbox.get_first_child()
        best_match = None
        best_similarity = 0
        
        while child:
            button = child.get_child()
            label = button.get_label().lower()
            tag_lower = tag_name.lower()
            
            if label != "all":
                # Simple similarity score (can be improved with Levenshtein distance)
                similarity = 0
                if tag_lower in label or label in tag_lower:
                    # Length of common substring
                    similarity = len(set(tag_lower) & set(label)) / max(len(tag_lower), len(label))
                    
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = button
                    
            child = child.get_next_sibling()
            
        # If we found a decent match, use it
        if best_match and best_similarity > 0.5:
            self.active_button = best_match
            best_match.set_active(True)
            best_match.add_css_class("tag-button-active")
            print(f"Found fuzzy match: '{best_match.get_label()}' for '{tag_name}' (similarity: {best_similarity:.2f})")
            return True
                
        # If still not found, default to All
        print(f"Tag '{tag_name}' not found in current source")
        self.reset_selection()
        return False 