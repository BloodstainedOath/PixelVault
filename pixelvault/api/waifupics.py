import requests
from typing import Dict, List, Optional, Any

class WaifuPicsAPI:
    """Client for the Waifu.pics API."""
    
    BASE_URL = "https://api.waifu.pics"
    
    # Valid categories for each endpoint
    SFW_CATEGORIES = [
        "waifu", "neko", "shinobu", "megumin", "bully", "cuddle", "cry", "hug", "awoo", 
        "kiss", "lick", "pat", "smug", "bonk", "yeet", "blush", "smile", "wave", "highfive", 
        "handhold", "nom", "bite", "glomp", "slap", "kill", "kick", "happy", "wink", "poke", 
        "dance", "cringe"
    ]
    
    NSFW_CATEGORIES = [
        "waifu", "neko", "trap", "blowjob"
    ]
    
    def __init__(self):
        """Initialize the API client."""
        self.session = requests.Session()
    
    def get_random(self, category: str, is_nsfw: bool = False) -> Dict[str, Any]:
        """Get a random image from a specific category.
        
        Args:
            category: Image category (e.g., 'waifu', 'neko', etc.)
            is_nsfw: Whether to use NSFW endpoint
            
        Returns:
            JSON response containing image URL
        """
        # Determine the type (sfw/nsfw)
        type_path = "nsfw" if is_nsfw else "sfw"
        
        # Validate category exists for the selected endpoint
        valid_categories = self.NSFW_CATEGORIES if is_nsfw else self.SFW_CATEGORIES
        if category not in valid_categories:
            print(f"Warning: Category '{category}' is not valid for the {type_path} endpoint.")
            # Fall back to 'waifu' if category doesn't exist
            category = "waifu"
        
        try:
            response = self.session.get(f"{self.BASE_URL}/{type_path}/{category}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image from Waifu.pics: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return {}
    
    def get_many(self, category: str, is_nsfw: bool = False, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get multiple images from a specific category.
        
        Args:
            category: Image category (e.g., 'waifu', 'neko', etc.)
            is_nsfw: Whether to use NSFW endpoint
            exclude: List of URLs to exclude from results
            
        Returns:
            JSON response containing list of image URLs
        """
        # Determine the type (sfw/nsfw)
        type_path = "nsfw" if is_nsfw else "sfw"
        
        # Validate category exists for the selected endpoint
        valid_categories = self.NSFW_CATEGORIES if is_nsfw else self.SFW_CATEGORIES
        if category not in valid_categories:
            print(f"Warning: Category '{category}' is not valid for the {type_path} endpoint.")
            # Fall back to 'waifu' if category doesn't exist
            category = "waifu"
        
        # Prepare request data
        data = {"exclude": exclude} if exclude else {}
        
        try:
            response = self.session.post(f"{self.BASE_URL}/many/{type_path}/{category}", json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching images from Waifu.pics: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return {"files": []} 