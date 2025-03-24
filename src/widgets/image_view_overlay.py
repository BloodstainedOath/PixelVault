import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GObject, GLib, Gdk, GdkPixbuf, Gio

import os
import threading
import asyncio
import aiohttp
import aiofiles
from urllib.parse import urlparse
import tempfile

class ImageViewOverlay(Gtk.Overlay):
    def __init__(self, parent_window):
        super().__init__()
        
        self.parent_window = parent_window
        self.current_image_data = None
        
        # Create main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Create black background
        self.background = Gtk.Box()
        self.background.add_css_class("image-overlay-bg")
        
        # Create image view
        self.image_view = Gtk.Picture()
        self.image_view.set_size_request(800, 600)
        self.image_view.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.image_view.set_halign(Gtk.Align.CENTER)
        self.image_view.set_valign(Gtk.Align.CENTER)
        
        # Create close button
        self.close_button = Gtk.Button()
        self.close_button.set_icon_name("window-close-symbolic")
        self.close_button.add_css_class("overlay-close-button")
        self.close_button.connect("clicked", self.on_close_clicked)
        
        # Create toolbar
        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.toolbar.add_css_class("overlay-toolbar")
        
        # Add download button
        self.download_button = Gtk.Button(label="Download")
        self.download_button.set_icon_name("document-save-symbolic")
        self.download_button.connect("clicked", self.on_download_clicked)
        
        # Add favorite button
        self.favorite_button = Gtk.ToggleButton()
        self.favorite_button.set_icon_name("starred-symbolic")
        self.favorite_button.connect("toggled", self.on_favorite_toggled)
        
        # Add buttons to toolbar
        self.toolbar.append(self.download_button)
        self.toolbar.append(self.favorite_button)
        
        # Create metadata box
        self.metadata_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.metadata_box.add_css_class("metadata-box")
        
        self.title_label = Gtk.Label()
        self.title_label.set_halign(Gtk.Align.START)
        self.title_label.add_css_class("overlay-title")
        
        self.source_label = Gtk.Label()
        self.source_label.set_halign(Gtk.Align.START)
        
        self.resolution_label = Gtk.Label()
        self.resolution_label.set_halign(Gtk.Align.START)
        
        self.metadata_box.append(self.title_label)
        self.metadata_box.append(self.source_label)
        self.metadata_box.append(self.resolution_label)
        
        # Set up layout
        self.set_child(self.background)
        
        # Add widgets to the overlay
        self.add_overlay(self.image_view)
        self.add_overlay(self.close_button)
        self.add_overlay(self.toolbar)
        self.add_overlay(self.metadata_box)
        
        # Position widgets
        self.close_button.set_halign(Gtk.Align.END)
        self.close_button.set_valign(Gtk.Align.START)
        self.close_button.set_margin_top(12)
        self.close_button.set_margin_end(12)
        
        self.toolbar.set_halign(Gtk.Align.CENTER)
        self.toolbar.set_valign(Gtk.Align.END)
        self.toolbar.set_margin_bottom(24)
        
        self.metadata_box.set_halign(Gtk.Align.START)
        self.metadata_box.set_valign(Gtk.Align.END)
        self.metadata_box.set_margin_start(24)
        self.metadata_box.set_margin_bottom(24)
        
        # Hide initially
        self.set_visible(False)
        
        # Add keyboard shortcuts for navigation
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)
        
        # Add click event to close
        click_controller = Gtk.GestureClick.new()
        click_controller.connect("pressed", self.on_background_clicked)
        self.background.add_controller(click_controller)
    
    def show_image(self, image_data):
        self.current_image_data = image_data
        
        # Update metadata with better formatting
        # Title
        title = image_data.get("title", "Untitled")
        self.title_label.set_markup(f"<b>{title}</b>")
        
        # Source with better naming
        source_name = self._get_formatted_source_name(image_data.get("source", "unknown"))
        self.source_label.set_text(f"Source: {source_name}")
        
        # Resolution with proper display when unknown
        width = image_data.get("width", 0)
        height = image_data.get("height", 0)
        resolution_text = "Resolution: Unknown"
        if width and height and width > 0 and height > 0:
            resolution_text = f"Resolution: {width} × {height}"
        self.resolution_label.set_text(resolution_text)
        
        # Add tags if available
        tags = image_data.get("tags", [])
        if tags and len(tags) > 0:
            # Create or clear the tag flow box
            if not hasattr(self, 'tags_container'):
                # Create a container for "Tags:" label and the flow box
                self.tags_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                self.tags_label = Gtk.Label(label="Tags:")
                self.tags_label.set_halign(Gtk.Align.START)
                self.tags_container.append(self.tags_label)
                
                # Create a flow box for tags
                self.tags_flow = Gtk.FlowBox()
                self.tags_flow.set_selection_mode(Gtk.SelectionMode.NONE)
                self.tags_flow.set_max_children_per_line(5)
                self.tags_flow.set_homogeneous(False)
                self.tags_flow.set_row_spacing(4)
                self.tags_flow.set_column_spacing(4)
                self.tags_container.append(self.tags_flow)
                
                self.metadata_box.append(self.tags_container)
            else:
                # Clear existing tags
                while self.tags_flow.get_first_child():
                    self.tags_flow.remove(self.tags_flow.get_first_child())
            
            # Add tags to the flow box (limited to first 15)
            displayed_tags = tags[:15]
            for tag in displayed_tags:
                tag_text = tag.strip()
                if tag_text:
                    tag_button = Gtk.Button(label=tag_text)
                    tag_button.set_has_frame(False)
                    tag_button.add_css_class("metadata-tag")
                    tag_button.connect("clicked", self._on_tag_clicked, tag_text)
                    self.tags_flow.append(tag_button)
            
            # Show indicator for more tags if needed
            if len(tags) > 15 and hasattr(self, 'more_tags_label'):
                self.more_tags_label.set_text(f"+{len(tags) - 15} more")
                self.more_tags_label.set_visible(True)
            elif len(tags) > 15:
                self.more_tags_label = Gtk.Label(label=f"+{len(tags) - 15} more")
                self.more_tags_label.add_css_class("metadata-tag")
                self.more_tags_label.set_opacity(0.7)
                self.tags_flow.append(self.more_tags_label)
            elif hasattr(self, 'more_tags_label'):
                self.more_tags_label.set_visible(False)
                
            self.tags_container.set_visible(True)
        elif hasattr(self, 'tags_container'):
            self.tags_container.set_visible(False)
        
        # Check if image is in favorites
        is_favorite = self.parent_window.sidebar.is_in_favorites(image_data)
        self.favorite_button.set_active(is_favorite)
        
        # Load the full image
        self._load_full_image(image_data.get("url"))
        
        # Add to history
        self.parent_window.sidebar.add_to_history(image_data)
        
        # Show the overlay
        self.set_visible(True)
        
        # Make sure it's on top
        self.parent_window.set_content(self)
    
    def hide_image(self):
        self.set_visible(False)
        self.parent_window.set_content(self.parent_window.main_layout)
    
    def is_visible(self):
        return self.get_visible()
    
    def toggle_favorite(self):
        # Toggle the favorite button
        self.favorite_button.set_active(not self.favorite_button.get_active())
    
    def on_close_clicked(self, button):
        self.hide_image()
    
    def on_background_clicked(self, gesture, n_press, x, y):
        self.hide_image()
    
    def on_favorite_toggled(self, button):
        if not self.current_image_data:
            return
            
        if button.get_active():
            self.parent_window.sidebar.add_to_favorites(self.current_image_data)
        else:
            self.parent_window.sidebar.remove_from_favorites(self.current_image_data)
    
    def on_download_clicked(self, button):
        if not self.current_image_data:
            return
            
        source = self.current_image_data.get("source")
        url = self.current_image_data.get("url")
        
        if not url:
            return
            
        # Get the filename from the URL
        filename = os.path.basename(urlparse(url).path)
        
        # For waifu_im, make sure we have a valid image extension
        if source == "waifu_im":
            # Extract extension or use .jpg as fallback
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # Check URL for extension hints
                if 'png' in url.lower():
                    filename = f"{os.path.splitext(filename)[0]}.png"
                else:
                    filename = f"{os.path.splitext(filename)[0]}.jpg"
        
        # Create a file chooser dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Image")
        dialog.set_initial_name(filename)
        
        # Show the dialog
        dialog.save(self.parent_window, None, self._on_save_dialog_response)
    
    def _on_save_dialog_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                # Get save path
                save_path = file.get_path()
                
                # Get URL to download
                source = self.current_image_data.get("source")
                url = self.current_image_data.get("url")
                
                # For waifu_im, use the thumbnail URL which is more reliable
                if source == "waifu_im":
                    thumbnail = self.current_image_data.get("thumbnail")
                    if thumbnail:
                        url = thumbnail
                
                # Start download in a thread
                threading.Thread(
                    target=self._run_download,
                    args=(url, save_path,),
                    daemon=True
                ).start()
        except Exception as e:
            print(f"Error saving file: {e}")
    
    def _run_download(self, url, save_path):
        # Create and run async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._download_image(url, save_path))
        finally:
            loop.close()
    
    async def _download_image(self, url, save_path):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.read()
                        async with aiofiles.open(save_path, "wb") as f:
                            await f.write(data)
        except Exception as e:
            print(f"Error downloading image: {e}")
    
    def on_key_pressed(self, controller, keyval, keycode, state):
        key = Gdk.keyval_name(keyval)
        
        if key == "Escape":
            self.hide_image()
            return True
        
        return False
    
    def _load_full_image(self, url):
        if not url:
            return
            
        # Start loading in a thread
        threading.Thread(
            target=self._run_load_image,
            args=(url,),
            daemon=True
        ).start()
    
    def _run_load_image(self, url):
        # Create and run async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._async_load_image(url))
        finally:
            loop.close()
    
    async def _async_load_image(self, url):
        try:
            # If URL is empty or invalid, skip loading
            if not url:
                return
                
            print(f"Loading full-sized image from: {url}")
            
            async with aiohttp.ClientSession() as session:
                # Add a user agent to avoid being blocked by some servers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        # Create a temporary file
                        with tempfile.NamedTemporaryFile(delete=False) as temp:
                            temp_path = temp.name
                        
                        # Save the image data
                        data = await response.read()
                        async with aiofiles.open(temp_path, "wb") as f:
                            await f.write(data)
                        
                        # Make sure the data is actually an image
                        # This helps detect HTML error pages posing as images
                        if len(data) > 0 and data[0:4] not in [b'\xff\xd8\xff\xe0', b'\x89PNG', b'GIF8', b'RIFF', b'\xff\xd8\xff\xe1']:
                            print(f"Warning: The data from {url} doesn't appear to be a valid image")
                            # For waifu_im, try falling back to the thumbnail which is usually reliable
                            if self.current_image_data and self.current_image_data.get("source") == "waifu_im":
                                thumbnail = self.current_image_data.get("thumbnail")
                                if thumbnail and thumbnail != url:
                                    print(f"Falling back to thumbnail URL: {thumbnail}")
                                    # Start a new thread to load the thumbnail
                                    threading.Thread(
                                        target=self._run_load_image,
                                        args=(thumbnail,),
                                        daemon=True
                                    ).start()
                                    # Clean up this temporary file
                                    os.unlink(temp_path)
                                    return
                        
                        # Load the image on the main thread
                        GLib.idle_add(self._set_image_from_file, temp_path)
                    else:
                        print(f"Error loading image, status code: {response.status}")
                        # For waifu_im, try falling back to the thumbnail which is usually reliable
                        if self.current_image_data and self.current_image_data.get("source") == "waifu_im":
                            thumbnail = self.current_image_data.get("thumbnail")
                            if thumbnail and thumbnail != url:
                                print(f"Falling back to thumbnail URL after error: {thumbnail}")
                                # Start a new thread to load the thumbnail
                                threading.Thread(
                                    target=self._run_load_image,
                                    args=(thumbnail,),
                                    daemon=True
                                ).start()
        except Exception as e:
            print(f"Error loading image: {e}")
    
    def _set_image_from_file(self, file_path):
        try:
            # Load the image
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_path)
            
            # Create texture from pixbuf - this is the critical part that might be failing
            # The direct conversion might fail depending on GTK version
            try:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            except Exception as e:
                print(f"Error creating texture from pixbuf: {e}")
                # Alternative method to create texture from memory
                success, buffer = pixbuf.save_to_bufferv("png", [], [])
                if success:
                    gbytes = GLib.Bytes.new(buffer)
                    stream = Gio.MemoryInputStream.new_from_bytes(gbytes)
                    texture = Gdk.Texture.new_from_stream(stream, None)
                else:
                    raise Exception("Failed to create buffer from pixbuf")
            
            # Set the image
            self.image_view.set_paintable(texture)
            
            # Update resolution metadata with actual image dimensions
            if self.current_image_data:
                width = pixbuf.get_width()
                height = pixbuf.get_height()
                
                # Update the metadata in memory
                self.current_image_data["width"] = width
                self.current_image_data["height"] = height
                
                # Update the display
                self.resolution_label.set_text(f"Resolution: {width} × {height}")
                
                # Also update the title since some images might have better titles
                # after loading the full image (especially for wallhaven)
                if self.current_image_data.get("source") == "wallhaven":
                    title = self.current_image_data.get("title", "Untitled")
                    self.title_label.set_markup(f"<b>{title}</b>")
            
            # Clean up the temporary file
            os.unlink(file_path)
        except Exception as e:
            print(f"Error setting image: {e}")
            
            # Attempt to recover with a fallback for waifu_im images
            if self.current_image_data and self.current_image_data.get("source") == "waifu_im":
                thumbnail = self.current_image_data.get("thumbnail")
                if thumbnail and thumbnail != self.current_image_data.get("url"):
                    print(f"Trying one more fallback to thumbnail after pixbuf error")
                    self._load_full_image(thumbnail)
            
            # Clean up the temporary file even if there was an error
            try:
                os.unlink(file_path)
            except:
                pass
        
        return False
    
    def _get_formatted_source_name(self, source_id):
        """Convert source ID to a friendly display name."""
        source_names = {
            "wallhaven": "Wallhaven",
            "waifu_im": "Waifu.im",
            "waifu_pics": "Waifu.pics",
            "nekos_moe": "Nekos.moe"
        }
        return source_names.get(source_id, source_id.capitalize())
        
    def _format_tags_display(self, tags, total_count):
        """Format tags for better display with styling."""
        formatted_tags = []
        for tag in tags:
            tag_text = tag.strip().replace(" ", "_")
            formatted_tags.append(f"<span class='metadata-tag'>{tag_text}</span>")
            
        result = "<span>Tags:</span> " + " ".join(formatted_tags)
        
        # Add note if there are more tags
        if total_count > len(tags):
            result += f" <i>(+{total_count - len(tags)} more)</i>"
            
        return result
    
    def _on_tag_clicked(self, button, tag):
        """Handle tag button clicks to filter by the clicked tag"""
        # Hide the overlay first
        self.hide_image()
        
        # Get the current source
        current_source = self.parent_window.source_switcher.get_active_source()
        
        # Find the tag in the tag filter and activate it
        self.parent_window.tag_filter.select_tag(tag)
        
        # Filter the images by the tag
        self.parent_window.image_grid.filter_by_tag(tag, current_source) 