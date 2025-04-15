"""API module for PixelVault."""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum, auto
from .wallhaven import WallhavenAPI, Category as WallhavenCategory, Purity as WallhavenPurity
from .waifuim import WaifuImAPI
from .waifupics import WaifuPicsAPI
from ..settings import settings

class ImageSource(Enum):
    """Enum for different image sources."""
    WALLHAVEN = auto()
    WAIFUIM = auto()
    WAIFUPICS = auto()

class SourceManager:
    """Manager for all image sources."""
    
    def __init__(self):
        """Initialize the source manager with all API clients."""
        # Get API key from settings
        self.wallhaven_api_key = settings.get("wallhaven_api_key", "")
        
        # Initialize APIs
        self.wallhaven = WallhavenAPI(api_key=self.wallhaven_api_key if self.wallhaven_api_key else None)
        self.waifuim = WaifuImAPI()
        self.waifupics = WaifuPicsAPI()
        self.current_source = ImageSource.WALLHAVEN
        
        # Wallhaven random seed for maintaining consistency between pages
        self.wallhaven_random_seed = None
        
        # Cache for common wallhaven tags
        self._wallhaven_tags = [
            {"id": 1, "name": "anime", "category": "anime"},
            {"id": 2, "name": "digital art", "category": "art"},
            {"id": 3, "name": "landscape", "category": "nature"},
            {"id": 4, "name": "nature", "category": "nature"},
            {"id": 5, "name": "city", "category": "urban"},
            {"id": 6, "name": "fantasy", "category": "fiction"},
            {"id": 7, "name": "space", "category": "science"},
            {"id": 8, "name": "animals", "category": "nature"},
            {"id": 9, "name": "technology", "category": "technology"},
            {"id": 10, "name": "minimalism", "category": "design"},
            {"id": 11, "name": "abstract", "category": "art"},
            {"id": 12, "name": "cyberpunk", "category": "fiction"},
            {"id": 13, "name": "car", "category": "vehicles"},
            {"id": 14, "name": "photography", "category": "photography"},
            {"id": 15, "name": "mountain", "category": "nature"},
            {"id": 16, "name": "sea", "category": "nature"},
            {"id": 17, "name": "forest", "category": "nature"},
            {"id": 18, "name": "winter", "category": "seasons"},
            {"id": 19, "name": "summer", "category": "seasons"},
            {"id": 20, "name": "spring", "category": "seasons"},
            {"id": 21, "name": "fall", "category": "seasons"},
            {"id": 22, "name": "sunset", "category": "nature"},
            {"id": 23, "name": "night", "category": "time"},
            {"id": 24, "name": "sky", "category": "nature"}
        ]
        
        # Cache for waifu.pics categories
        self._waifupics_sfw_categories = [
            "waifu", "neko", "shinobu", "megumin", "bully", "cuddle", "cry", "hug", "awoo", "kiss", "lick", "pat",
            "smug", "bonk", "yeet", "blush", "smile", "wave", "highfive", "handhold", "nom", "bite", "glomp", "slap",
            "kill", "kick", "happy", "wink", "poke", "dance", "cringe"
        ]
        self._waifupics_nsfw_categories = [
            "waifu", "neko", "trap", "blowjob"
        ]
        
    def update_wallhaven_api_key(self, api_key: str):
        """Update the Wallhaven API key.
        
        Args:
            api_key: The new API key
        """
        if api_key != self.wallhaven_api_key:
            self.wallhaven_api_key = api_key
            # Recreate the Wallhaven API client with the new key
            self.wallhaven = WallhavenAPI(api_key=api_key if api_key else None)
            # Clear the random seed
            self.wallhaven_random_seed = None
    
    def set_source(self, source: ImageSource):
        """Set the current image source.
        
        Args:
            source: The image source to set
        """
        self.current_source = source
    
    def get_images(self, tags: List[str] = None, page: int = 1, reset_seed: bool = False, **kwargs) -> Dict[str, Any]:
        """Get images from the current source.
        
        Args:
            tags: List of tags to filter by
            page: Page number for pagination
            reset_seed: Whether to reset the random seed (for new searches)
            **kwargs: Additional arguments for the API
            
        Returns:
            Dictionary containing images list and pagination info
        """
        if self.current_source == ImageSource.WALLHAVEN:
            # Set default parameters for Wallhaven
            wallhaven_params = {
                'categories': WallhavenCategory.ALL,
                'purity': WallhavenPurity.SFW,
                'page': page
            }
            
            # Extract Wallhaven-specific parameters
            if 'categories' in kwargs:
                wallhaven_params['categories'] = kwargs['categories']
            
            if 'purity' in kwargs:
                requested_purity = kwargs['purity']
                # Store the originally requested purity
                wallhaven_params['purity'] = requested_purity
                
                # Check if NSFW or Sketchy content is requested and we have an API key
                requested_purity_value = requested_purity.value if hasattr(requested_purity, 'value') else requested_purity
                if (requested_purity_value in ["110", "111"]) and not self.wallhaven_api_key:
                    print(f"Warning: NSFW or Sketchy content requested but no API key provided. Falling back to SFW.")
                    print(f"Original purity request: {requested_purity_value}")
                    print(f"API key present: {bool(self.wallhaven_api_key)}")
                    # Only fall back to SFW if no API key is available
                    wallhaven_params['purity'] = WallhavenPurity.SFW
                
            if 'sorting' in kwargs:
                wallhaven_params['sorting'] = kwargs['sorting']
                
            if 'resolutions' in kwargs:
                wallhaven_params['resolutions'] = kwargs['resolutions']
                
            if 'ratios' in kwargs:
                wallhaven_params['ratios'] = kwargs['ratios']
                
            if 'colors' in kwargs:
                wallhaven_params['colors'] = kwargs['colors']
                
            if 'atleast' in kwargs:
                wallhaven_params['atleast'] = kwargs['atleast']
                
            if 'top_range' in kwargs:
                wallhaven_params['top_range'] = kwargs['top_range']
                
            # Handle tags parameter
            if tags and len(tags) > 0:
                wallhaven_params['tags'] = tags
            
            # Handle search query
            if 'query' in kwargs and kwargs['query']:
                wallhaven_params['query'] = kwargs['query']
            
            # Reset seed if requested (for new searches)
            if reset_seed:
                self.wallhaven_random_seed = None
                
            # Get images based on the selected method
            method = kwargs.get('method', 'latest')
            if method == 'top':
                print(f"Fetching top wallpapers, page {page}")
                response = self.wallhaven.get_top(**wallhaven_params)
            elif method == 'random':
                # For random sorting, include the seed if we have one
                if not reset_seed and self.wallhaven_random_seed:
                    print(f"Using existing seed for random: {self.wallhaven_random_seed}, page {page}")
                    wallhaven_params['seed'] = self.wallhaven_random_seed
                else:
                    print(f"Fetching new random wallpapers without seed, page {page}")
                
                response = self.wallhaven.get_random(**wallhaven_params)
                
                # Store the seed from the response for next page
                if 'meta' in response and 'seed' in response['meta']:
                    self.wallhaven_random_seed = response['meta']['seed']
                    print(f"Received new seed: {self.wallhaven_random_seed}")
            else:  # default to latest
                print(f"Fetching latest wallpapers, page {page}")
                response = self.wallhaven.get_latest(**wallhaven_params)
            
            # Normalize Wallhaven response
            images = []
            pagination = {
                "has_next_page": False,
                "current_page": 1,
                "total_pages": 1
            }
            
            if "data" in response:
                # Check if we received empty results and might need to show a warning
                if len(response["data"]) == 0:
                    purity_value = wallhaven_params['purity'].value if hasattr(wallhaven_params['purity'], 'value') else wallhaven_params['purity']
                    if purity_value in ["110", "111"] and self.wallhaven_api_key:
                        print(f"No results found with purity: {purity_value}")
                        print("If you're looking for NSFW content, verify that:")
                        print("1. Your Wallhaven API key is valid")
                        print("2. Your Wallhaven account has NSFW content enabled")
                        print("3. Your Wallhaven account has the appropriate purity levels enabled")
                
                images = [
                    {
                        "id": item["id"],
                        "url": item["path"],
                        "preview": item["thumbs"]["large"],
                        "source": item.get("source", ""),
                        "width": item["dimension_x"],
                        "height": item["dimension_y"],
                        "provider": "wallhaven",
                        "category": item.get("category", ""),
                        "purity": item.get("purity", ""),
                        "tags": [tag.get("name", "") for tag in item.get("tags", [])]
                    }
                    for item in response["data"]
                ]
                
                # Extract pagination info if available
                if "meta" in response:
                    meta = response["meta"]
                    pagination = {
                        "current_page": meta.get("current_page", 1),
                        "total_pages": meta.get("last_page", 1),
                        "has_next_page": meta.get("current_page", 1) < meta.get("last_page", 1),
                        "seed": meta.get("seed")  # Include the seed in pagination info
                    }
            
            return {
                "images": images,
                "pagination": pagination
            }
            
        elif self.current_source == ImageSource.WAIFUIM:
            response = self.waifuim.get_random(is_nsfw=kwargs.get('is_nsfw', False), selected_tags=tags)
            # Normalize Waifu.im response
            images = []
            pagination = {
                "has_next_page": False,
                "current_page": page,
                "total_pages": page
            }
            
            if "images" in response:
                for item in response["images"]:
                    try:
                        # Use the main URL for preview since preview_url is not a direct image URL
                        image_data = {
                            "id": str(item["image_id"]),
                            "url": item["url"],
                            "preview": item["url"],  # Use the main URL for preview
                            "source": item.get("source", ""),
                            "width": item.get("width", 0),
                            "height": item.get("height", 0),
                            "provider": "waifu.im",
                            "tags": item.get("tags", [])
                        }
                        images.append(image_data)
                    except KeyError as e:
                        print(f"Error normalizing Waifu.im image data: {e}")
                        print(f"Image data: {item}")
                        continue
            
            return {
                "images": images,
                "pagination": pagination
            }
        
        elif self.current_source == ImageSource.WAIFUPICS:
            # Get images from Waifu.pics
            images = []
            pagination = {
                "has_next_page": False,
                "current_page": page,
                "total_pages": page
            }
            
            # Get multiple images
            is_nsfw = kwargs.get('is_nsfw', False)
            
            # Use first tag as category if provided, otherwise use 'waifu'
            category = 'waifu'  # Default category
            if tags and len(tags) > 0:
                category = tags[0]
                print(f"Using category: {category} for waifu.pics (NSFW: {is_nsfw})")
            
            # Get multiple images
            response = self.waifupics.get_many(category=category, is_nsfw=is_nsfw)
            
            if "files" in response and response["files"]:
                for url in response["files"]:
                    image_data = {
                        "id": url.split('/')[-1],  # Use filename as ID
                        "url": url,
                        "preview": url,  # Use same URL for preview
                        "source": "",  # Waifu.pics doesn't provide source
                        "width": 0,  # Width not provided
                        "height": 0,  # Height not provided
                        "provider": "waifu.pics",
                        "tags": [category] if category else []
                    }
                    images.append(image_data)
            else:
                print(f"No images found for category: {category} (NSFW: {is_nsfw})")
            
            return {
                "images": images,
                "pagination": pagination
            }
        
        return {
            "images": [],
            "pagination": {
                "has_next_page": False,
                "current_page": page,
                "total_pages": page
            }
        }
    
    def get_source_name(self) -> str:
        """Get the name of the current source.
        
        Returns:
            Name of the current source
        """
        if self.current_source == ImageSource.WALLHAVEN:
            return "Wallhaven"
        elif self.current_source == ImageSource.WAIFUIM:
            return "Waifu.im"
        elif self.current_source == ImageSource.WAIFUPICS:
            return "Waifu.pics"
        return "Unknown"
    
    def get_available_tags(self) -> List[Dict[str, Any]]:
        """Get available tags for the current source.
        
        Returns:
            List of available tags
        """
        if self.current_source == ImageSource.WALLHAVEN:
            # Return cached common Wallhaven tags
            # Since Wallhaven doesn't have a simple tag list API endpoint
            return self._wallhaven_tags
            
        elif self.current_source == ImageSource.WAIFUIM:
            # Get tags from Waifu.im API
            all_tags = self.waifuim.get_all_tags()
            result = []
            
            # Add versatile tags (SFW)
            for tag in all_tags.get("versatile", []):
                if isinstance(tag, dict):
                    result.append({
                        "name": tag.get("name", ""),
                        "description": tag.get("description", ""),
                        "category": "sfw"
                    })
                elif isinstance(tag, str):
                    result.append({
                        "name": tag,
                        "description": f"SFW {tag} images",
                        "category": "sfw"
                    })
            
            # Add NSFW tags
            for tag in all_tags.get("nsfw", []):
                if isinstance(tag, dict):
                    result.append({
                        "name": tag.get("name", ""),
                        "description": tag.get("description", ""),
                        "category": "nsfw"
                    })
                elif isinstance(tag, str):
                    result.append({
                        "name": tag,
                        "description": f"NSFW {tag} images",
                        "category": "nsfw"
                    })
                
            return result
        
        elif self.current_source == ImageSource.WAIFUPICS:
            # Return waifu.pics categories as tags
            result = []
            
            # Add SFW categories
            for category in self._waifupics_sfw_categories:
                result.append({
                    "name": category,
                    "description": f"SFW {category} images",
                    "category": "sfw"
                })
            
            # Add NSFW categories
            for category in self._waifupics_nsfw_categories:
                result.append({
                    "name": category,
                    "description": f"NSFW {category} images",
                    "category": "nsfw"
                })
            
            return result
        
        return []
    
    def get_source_features(self) -> Dict[str, Any]:
        """Get features available for the current source.
        
        Returns:
            Dictionary of available features
        """
        if self.current_source == ImageSource.WALLHAVEN:
            return {
                "categories": True,
                "purity_levels": True,
                "resolutions": True,
                "aspect_ratios": True,
                "sorting_options": [
                    {"id": "latest", "name": "Latest"},
                    {"id": "toplist", "name": "Top"},
                    {"id": "random", "name": "Random"},
                    {"id": "views", "name": "Views"},
                    {"id": "favorites", "name": "Favorites"}
                ],
                "time_ranges": [
                    {"id": "1d", "name": "1 Day"},
                    {"id": "3d", "name": "3 Days"},
                    {"id": "1w", "name": "1 Week"},
                    {"id": "1M", "name": "1 Month"},
                    {"id": "3M", "name": "3 Months"},
                    {"id": "6M", "name": "6 Months"},
                    {"id": "1y", "name": "1 Year"}
                ],
                "color_filtering": True,
                "tag_filtering": True
            }
        elif self.current_source == ImageSource.WAIFUIM:
            return {
                "categories": False,
                "purity_levels": True,  # SFW/NSFW toggle
                "resolutions": False,
                "aspect_ratios": False,
                "sorting_options": [],
                "time_ranges": [],
                "color_filtering": False,
                "tag_filtering": True
            }
        elif self.current_source == ImageSource.WAIFUPICS:
            return {
                "categories": False,
                "purity_levels": True,  # SFW/NSFW toggle
                "resolutions": False,
                "aspect_ratios": False,
                "sorting_options": [],
                "time_ranges": [],
                "color_filtering": False,
                "tag_filtering": True  # Categories are implemented as tags
            }
        return {}
