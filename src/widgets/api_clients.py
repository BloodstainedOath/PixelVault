import aiohttp
import json
import os
import uuid
from urllib.parse import urlencode, quote_plus
import time
import asyncio

class BaseClient:
    """Base class for all API clients."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "PixelVault/1.0"
        }
    
    async def get_images(self, page=1, query="", tag=""):
        """
        Get images from the source.
        
        Args:
            page: Page number for pagination
            query: Search query
            tag: Tag to filter by
            
        Returns:
            List of image data dictionaries
        """
        raise NotImplementedError("Subclasses must implement get_images")
    
    async def download_image(self, url, save_path):
        """
        Download an image from the given URL and save it to the specified path.
        
        Args:
            url: URL of the image to download
            save_path: Path to save the image to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(save_path, "wb") as f:
                            f.write(await response.read())
                        return True
            return False
        except Exception as e:
            print(f"Error downloading image: {e}")
            return False

class WallhavenClient(BaseClient):
    """Client for Wallhaven API."""
    
    def __init__(self):
        super().__init__()
        self.api_base = "https://wallhaven.cc/api/v1"
        # API key should be set if you have one
        self.api_key = os.environ.get("WALLHAVEN_API_KEY", None)
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
        
        # Tag mappings for better search matching
        self.tag_synonyms = {
            # Category equivalents
            "cartoon": "general",
            "drawing": "general",
            "illustration": "general",
            "manga": "anime",
            "character": "anime",
            "portrait": "people",
            "male": "people",
            "female": "people",
            "person": "people",
            
            # Color variations
            "red": "red",
            "crimson": "red",
            "scarlet": "red",
            "maroon": "red",
            "blue": "blue",
            "azure": "blue",
            "cyan": "blue",
            "teal": "blue",
            "navy": "blue",
            "green": "green",
            "emerald": "green",
            "lime": "green",
            "olive": "green",
            "yellow": "yellow",
            "gold": "yellow",
            "amber": "yellow",
            "orange": "orange",
            "purple": "purple",
            "violet": "purple",
            "magenta": "purple",
            "lavender": "purple",
            "pink": "pink",
            "rose": "pink",
            "brown": "brown",
            "tan": "brown",
            "beige": "brown",
            "black": "black",
            "gray": "black",
            "grey": "black",
            "white": "white",
            "cream": "white",
        }
        
        # Common search categories 
        self.content_categories = [
            "landscape", "nature", "sky", "mountain", "gaming", 
            "car", "space", "city", "abstract", "fantasy", 
            "dark", "sci-fi", "cyberpunk", "minimal", "technology",
            "portrait", "sunset", "beach", "night", "water", 
            "forest", "winter", "summer", "flowers", "architecture",
            "food", "music", "animal", "sport"
        ]
    
    async def get_images(self, page=1, query="", tag=""):
        params = {
            "page": page,
            "sorting": "random"
        }
        
        print(f"WallhavenClient.get_images called with tag: '{tag}', query: '{query}'")
        
        # Add search query if provided
        if query:
            params["q"] = query
        
        # Handle tags according to API documentation
        if tag:
            tag_lower = tag.lower()
            
            # Try to map tag to a known synonym if needed
            if tag_lower in self.tag_synonyms:
                mapped_tag = self.tag_synonyms[tag_lower]
                print(f"Mapped tag '{tag_lower}' to '{mapped_tag}'")
                tag_lower = mapped_tag
            
            # Handle category tags - must be set as 1/0 in a 3-digit format (general/anime/people)
            if tag_lower == "general":
                params["categories"] = "100"  # Only general enabled
                print(f"Setting category filter to general only")
            elif tag_lower == "anime":
                params["categories"] = "010"  # Only anime enabled
                print(f"Setting category filter to anime only")
            elif tag_lower == "people":
                params["categories"] = "001"  # Only people enabled
                print(f"Setting category filter to people only")
                
            # Handle purity tags - must be set as 1/0 in a 3-digit format (sfw/sketchy/nsfw)
            elif tag_lower == "sfw":
                params["purity"] = "100"  # Only SFW enabled
                print(f"Setting purity filter to SFW only")
            elif tag_lower == "sketchy":
                params["purity"] = "110"  # SFW and sketchy enabled
                print(f"Setting purity filter to SFW and sketchy")
            elif tag_lower == "nsfw":
                # NSFW requires API key
                if self.api_key:
                    params["purity"] = "111"  # All purities enabled
                    print(f"Setting purity filter to include NSFW (API key provided)")
                else:
                    params["purity"] = "110"  # SFW and sketchy only (no API key)
                    print(f"Setting purity filter to SFW and sketchy (no API key for NSFW)")
                
            # Handle specific colors
            elif tag_lower in ["red", "blue", "green", "yellow", "purple", "pink", "orange", "brown", "black", "white"]:
                # Map color names to hex codes according to API
                color_map = {
                    "red": "cc0000",
                    "blue": "0066cc",
                    "green": "669900",
                    "yellow": "ffff00",
                    "orange": "ff9900",
                    "purple": "663399",
                    "pink": "ea4c88",
                    "brown": "996633",
                    "black": "000000",
                    "white": "ffffff"
                }
                if tag_lower in color_map:
                    params["colors"] = color_map[tag_lower]
                    print(f"Filtering by color: {tag_lower} ({color_map[tag_lower]})")
                
            # Handle content themes as search terms with + prefix (ensures inclusion)
            else:
                if tag_lower in self.content_categories:
                    # Format search query according to API docs
                    tag_search = "+" + tag_lower  # '+' prefix ensures inclusion
                    if query:
                        params["q"] = query + " " + tag_search
                    else:
                        params["q"] = tag_search
                    print(f"Using tag '{tag}' as specific search term: {params['q']}")
                else:
                    # For any other tag, use it as a general search term
                    tag_search = "+" + tag_lower
                    if query:
                        params["q"] = query + " " + tag_search
                    else:
                        params["q"] = tag_search
                    print(f"Using tag '{tag}' as general search term: {params['q']}")
        
        # Build URL
        url = f"{self.api_base}/search"
        if params:
            url += f"?{urlencode(params)}"
            
        print(f"Request URL: {url}")
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    else:
                        error_text = await response.text()
                        print(f"Error fetching images from Wallhaven: {response.status}, {error_text}")
            return []
        except Exception as e:
            print(f"Error fetching images from Wallhaven: {e}")
            return []
    
    def _parse_response(self, data):
        """Parse Wallhaven API response into a standard format."""
        images = []
        
        for item in data.get("data", []):
            # Extract a better title from the data
            title = item.get("id", "Wallhaven Image")
            
            # Extract all tags (pre-process for better grouping)
            raw_tags = [tag["name"] for tag in item.get("tags", [])]
            tags = self._process_tags(raw_tags)
            
            # Generate a descriptive title based on tags
            if tags:
                # Look for specific categories first
                important_categories = ["anime", "game", "movie", "tv series", "cartoon", "person", "animal", "landscape", "city", "nature", "space"]
                category_tags = []
                
                for category in important_categories:
                    matching_tags = [tag for tag in tags if category in tag.lower()]
                    category_tags.extend(matching_tags)
                
                # Use descriptive title if we found category tags
                if category_tags:
                    # Sort by length to get the most specific tag first
                    category_tags.sort(key=len)
                    primary_tag = category_tags[-1]  # Use the longest, most specific tag
                    
                    # Extract resolution for more detail
                    res_string = ""
                    if item.get("dimension_x") and item.get("dimension_y"):
                        res_string = f" [{item.get('dimension_x')}×{item.get('dimension_y')}]"
                    
                    title = f"{primary_tag.title()}{res_string}"
                else:
                    # If no specific category was found, use the first tag
                    title = tags[0].title()
            
            # Create standardized image data
            image = {
                "id": item.get("id", str(uuid.uuid4())),
                "title": title,
                "url": item.get("path"),
                "thumbnail": item.get("thumbs", {}).get("large"),
                "width": item.get("dimension_x"),
                "height": item.get("dimension_y"),
                "source": "wallhaven",
                "tags": tags,
                "purity": item.get("purity", "sfw"),
                "category": item.get("category"),
                "colors": item.get("colors", []),  # Add color data
                "date_added": item.get("created_at"),  # Add date information
                "ratio": self._calculate_ratio(item.get("dimension_x"), item.get("dimension_y")),
                "views": item.get("views"),
                "favorites": item.get("favorites")
            }
            images.append(image)
        
        return images
        
    def _process_tags(self, raw_tags):
        """Process raw tags into more useful categories"""
        processed_tags = []
        
        # Map of tag categories for grouping
        category_prefixes = {
            "anime:": "Anime",
            "game:": "Game",
            "movie:": "Movie",
            "tv series:": "TV",
        }
        
        # Exclude very generic tags that don't add value
        exclude_tags = {"wallpaper", "wallpapers", "digital art", "artwork", "drawing", "render"}
        
        for tag in raw_tags:
            # Skip excluded tags
            if tag.lower() in exclude_tags:
                continue
                
            # Handle category prefixes
            for prefix, category in category_prefixes.items():
                if tag.lower().startswith(prefix):
                    # Extract the specific item name and add it with category
                    item_name = tag[len(prefix):].strip()
                    if item_name:
                        processed_tags.append(f"{category}: {item_name}")
                    break
            else:
                # No prefix match, add the tag as-is
                processed_tags.append(tag)
                
        return processed_tags
        
    def _calculate_ratio(self, width, height):
        """Calculate aspect ratio as a string like 16:9"""
        if not width or not height:
            return None
            
        # Convert to integers if they're strings
        try:
            w, h = int(width), int(height)
        except (TypeError, ValueError):
            return None
            
        # Find greatest common divisor
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a
            
        divisor = gcd(w, h)
        if divisor > 0:
            ratio_w = w // divisor
            ratio_h = h // divisor
            
            # Handle common ratios
            if (ratio_w, ratio_h) == (16, 9):
                return "16:9"
            elif (ratio_w, ratio_h) == (4, 3):
                return "4:3"
            elif (ratio_w, ratio_h) == (21, 9):
                return "21:9"
            elif (ratio_w, ratio_h) == (1, 1):
                return "1:1"
            else:
                return f"{ratio_w}:{ratio_h}"
        return None

class WaifuImClient(BaseClient):
    """Client for Waifu.im API."""
    
    def __init__(self):
        super().__init__()
        self.api_base = "https://api.waifu.im"
        # Update headers per API docs
        self.headers = {
            "User-Agent": "PixelVault/1.0",
            "Accept": "application/json"
        }
    
    async def get_images(self, page=1, query="", tag=""):
        """
        Get images from Waifu.im API.
        Since the API sometimes returns only one image even with many=true,
        we make multiple requests to build a collection.
        """
        all_images = []
        max_attempts = 12  # Try up to 12 times to get enough images
        target_count = 24  # Increase target count to get more variety
        
        # Valid tags for this API - match the exact format from the API docs
        valid_tags = ["maid", "waifu", "marin-kitagawa", "mori-calliope", "raiden-shogun", 
                      "oppai", "selfies", "uniform", "school", "kemonomimi", "fox-girl",
                      "glasses", "student", "blonde", "elf"]
        
        print(f"WaifuImClient.get_images called with tag: '{tag}', query: '{query}'")
        
        for attempt in range(max_attempts):
            if len(all_images) >= target_count:
                break
                
            # Basic params - each request will be slightly different
            params = {
                "many": "true",     # Try to get multiple images
                "gif": "false",     # Exclude GIFs to keep things fast
                "_": str(int(time.time()) + attempt)  # Cache-busting
            }
            
            # Handle tags according to documentation
            if tag:
                tag_lower = tag.lower()
                # For NSFW content
                if tag_lower == "nsfw":
                    params["is_nsfw"] = "true"
                # For specific tags
                elif tag_lower in valid_tags:
                    # API expects selected_tags as a single tag
                    params["selected_tags"] = tag_lower
                    params["is_nsfw"] = "false"
                    print(f"Using tag '{tag_lower}' as selected_tags parameter")
                # For other tags, try as included_tags
                else:
                    # Try to match partial tag
                    matched_tag = next((valid for valid in valid_tags if tag_lower in valid), None)
                    if matched_tag:
                        params["selected_tags"] = matched_tag
                        print(f"Matched partial tag '{tag_lower}' to '{matched_tag}' as selected_tags")
                    else:
                        # If no match, use as general included tag
                        params["included_tags"] = tag_lower
                        print(f"Using tag '{tag_lower}' as included_tags parameter")
            
            # Build URL
            url = f"{self.api_base}/search"
            if params:
                url += f"?{urlencode(params)}"
            
            print(f"Request URL: {url}")
            
            try:
                async with aiohttp.ClientSession(headers=self.headers) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            new_images = self._parse_response(data)
                            
                            # Only add non-duplicate images
                            for img in new_images:
                                if not any(existing["id"] == img["id"] for existing in all_images):
                                    all_images.append(img)
                        else:
                            error_text = await response.text()
                            print(f"Error from Waifu.im on attempt {attempt+1}: {response.status}, {error_text}")
            except Exception as e:
                print(f"Request error on attempt {attempt+1}: {e}")
            
            # Small delay between requests to avoid rate limiting
            await asyncio.sleep(0.2)
        
        print(f"Waifu.im returned {len(all_images)} total images")
        return all_images
    
    def _parse_response(self, data):
        """Parse Waifu.im API response into a standard format."""
        images = []
        
        # Handle both single image response and 'images' array
        image_list = data.get("images", [])
        
        # If no images array but we have a URL, it's a single image response
        if not image_list and data.get("url"):
            image_list = [data]
        
        for item in image_list:
            # Skip if no URL
            if not item.get("url"):
                continue
                
            # Always use the direct CDN URL for waifu.im images
            image_url = item.get("url")
            
            # Extract more detailed metadata
            # Get a meaningful title - first use dominant_color as it's unique
            title = "waifu"
            
            # Extract all tags for better metadata
            tags = []
            if item.get("tags") and len(item.get("tags")) > 0:
                tags = [tag.get("name", "") for tag in item.get("tags", [])]
                if tags and len(tags) > 0:
                    # Use first tag as title if available
                    title = tags[0]
            
            # If image has a specific character, use that as title
            character_tags = ["marin-kitagawa", "mori-calliope", "raiden-shogun"]
            for char_tag in character_tags:
                if char_tag in tags:
                    title = char_tag.replace("-", " ").title()
                    break
            
            # Create standardized image data
            image = {
                "id": item.get("image_id", str(uuid.uuid4())),
                "title": title,
                "url": image_url,  # Use direct CDN URL for full-size image
                "thumbnail": item.get("url"),  # Use the same URL for thumbnail
                "width": item.get("width"),
                "height": item.get("height"),
                "source": "waifu_im",  # Exact match with source_id
                "tags": tags,
                "nsfw": item.get("is_nsfw", False)
            }
            images.append(image)
        
        return images

class WaifuPicsClient(BaseClient):
    """Client for Waifu.pics API."""
    
    def __init__(self):
        super().__init__()
        self.api_base = "https://api.waifu.pics"
        # Valid categories per API docs
        self.sfw_types = ["waifu", "neko", "shinobu", "megumin", "bully", "cuddle", "cry", "hug", "awoo", "kiss", "lick", "pat", "smug", "bonk", "yeet", "blush", "smile", "wave", "highfive", "handhold", "nom", "bite", "glomp", "slap", "kill", "kick", "happy", "wink", "poke", "dance", "cringe"]
        self.nsfw_types = ["waifu", "neko", "trap", "blowjob"]
    
    async def get_images(self, page=1, query="", tag=""):
        # Default to SFW if no tag specified
        endpoint = "sfw"
        
        # Default category
        category = "waifu"
        
        # Handle tag/category
        if tag:
            if tag.lower() == "nsfw":
                endpoint = "nsfw"
            elif tag.lower() in self.sfw_types:
                category = tag.lower()
            elif tag.lower() in self.nsfw_types:
                endpoint = "nsfw"
                category = tag.lower()
        
        print(f"Waifu.pics using endpoint: {endpoint}/{category}")
        
        # Since there's no pagination in waifu.pics API, we will ignore page parameter
        # and just return 20 images for any request
        try:
            images = []
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # First, try to get a batch using the /many endpoint
                many_url = f"{self.api_base}/many/{endpoint}/{category}"
                
                print(f"Trying Waifu.pics many endpoint: {many_url}")
                
                try:
                    # The /many endpoint expects an empty JSON object as the body
                    async with session.post(many_url, json={}) as response:
                        if response.status == 200:
                            data = await response.json()
                            file_urls = data.get("files", [])
                            
                            # If we got images from many endpoint, use them
                            if file_urls:
                                print(f"Waifu.pics /many returned {len(file_urls)} images")
                                for i, url in enumerate(file_urls):
                                    if url and i < 20:  # Limit to 20 images
                                        image_id = str(uuid.uuid4())
                                        image = {
                                            "id": image_id,
                                            "title": f"{category.capitalize()}",
                                            "url": url,
                                            "thumbnail": url,  # Waifu.pics doesn't provide thumbnails
                                            "width": 0,  # Not provided by the API
                                            "height": 0,  # Not provided by the API
                                            "source": "waifu_pics",  # Exact match with source_id
                                            "tags": [category],
                                            "nsfw": endpoint == "nsfw"
                                        }
                                        images.append(image)
                                return images
                            else:
                                print("Waifu.pics /many returned no images in 'files' array")
                        else:
                            error_text = await response.text()
                            print(f"Error from Waifu.pics /many: {response.status}, {error_text}")
                except Exception as e:
                    print(f"Error with /many endpoint: {e}, falling back to single image endpoint")
                
                # If /many endpoint failed or returned no images, fall back to single image endpoint
                # This is less efficient but more reliable
                print(f"Falling back to single endpoint for Waifu.pics")
                
                single_url = f"{self.api_base}/{endpoint}/{category}"
                for i in range(10):  # Try to get 10 images to keep it reasonable
                    try:
                        async with session.get(single_url) as response:
                            if response.status == 200:
                                data = await response.json()
                                image_url = data.get("url")
                                if image_url:
                                    image_id = str(uuid.uuid4())
                                    image = {
                                        "id": image_id,
                                        "title": f"{category.capitalize()} {i+1}",
                                        "url": image_url,
                                        "thumbnail": image_url,  # Waifu.pics doesn't provide thumbnails
                                        "width": 0,  # Not provided by the API
                                        "height": 0,  # Not provided by the API
                                        "source": "waifu_pics",  # Exact match with source_id
                                        "tags": [category],
                                        "nsfw": endpoint == "nsfw"
                                    }
                                    images.append(image)
                                else:
                                    print(f"Waifu.pics single endpoint returned no URL")
                            else:
                                error_text = await response.text()
                                print(f"Error fetching from Waifu.pics single: {response.status}, {error_text}")
                                break
                    except Exception as e:
                        print(f"Error in Waifu.pics single request: {e}")
                        break
            
            print(f"Waifu.pics returning {len(images)} total images")
            return images
        except Exception as e:
            print(f"Error fetching images from Waifu.pics: {e}")
            return []

class NekosMoeClient(BaseClient):
    """Client for Nekos.moe API."""
    
    def __init__(self):
        super().__init__()
        self.api_base = "https://nekos.moe/api/v1"
        # Set a proper user agent per documentation
        self.headers = {
            "User-Agent": "PixelVault/1.0 (github.com/pixelvault)"
        }
    
    async def get_images(self, page=1, query="", tag=""):
        # Build query parameters
        params = {
            "limit": 20,
            "skip": (page - 1) * 20
        }
        
        # Add search parameters
        search_params = {}
        
        if query:
            search_params["artist"] = query
        
        if tag:
            if tag.lower() == "nsfw":
                search_params["nsfw"] = True
            elif tag.lower() == "gif" or tag.lower() == "animated":
                search_params["animated"] = True
            else:
                search_params["tags"] = [tag.lower()]
        
        # Build URL
        url = f"{self.api_base}/images/search"
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # POST with search parameters
                async with session.post(url, json=search_params, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    else:
                        print(f"Error fetching from Nekos.moe: {response.status}, {await response.text()}")
            return []
        except Exception as e:
            print(f"Error fetching images from Nekos.moe: {e}")
            return []
    
    def _parse_response(self, data):
        """Parse Nekos.moe API response into a standard format."""
        images = []
        
        for item in data.get("images", []):
            image_id = item.get("id")
            
            # Skip if no image ID
            if not image_id:
                continue
                
            # Nekos.moe images need an extension (jpg) for direct viewing
            image_url = f"https://nekos.moe/image/{image_id}.jpg"
            thumbnail_url = f"https://nekos.moe/thumbnail/{image_id}.jpg"
                
            image = {
                "id": image_id,
                "title": item.get("artist", "Unknown Artist"),
                "url": image_url,
                "thumbnail": thumbnail_url,
                "width": 0,  # Not provided in search results
                "height": 0,  # Not provided in search results
                "source": "nekos_moe",  # Exact match with source_id
                "tags": item.get("tags", []),
                "nsfw": item.get("nsfw", False)
            }
            images.append(image)
        
        return images 