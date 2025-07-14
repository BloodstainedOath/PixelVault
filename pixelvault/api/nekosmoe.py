import requests
from typing import Dict, List, Optional, Any, Union
import random


class NekosMoeAPI:
    """Client for the nekos.moe API."""
    
    BASE_URL = "https://nekos.moe/api/v1"
    
    def __init__(self, token: Optional[str] = None):
        """Initialize the nekos.moe API client.
        
        Args:
            token: Optional token for authenticated requests
        """
        self.token = token
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "PixelVault/1.0"
        })
        
        if token:
            self.session.headers.update({"Authorization": token})
    
    def get_image(self, image_id: str) -> Dict[str, Any]:
        """Get a specific image by ID.
        
        Args:
            image_id: The ID of the image to retrieve
            
        Returns:
            JSON response containing the image data
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/images/{image_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image from nekos.moe: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return {"image": None}
    
    def get_random_images(self, nsfw: bool = False, count: int = 20) -> Dict[str, Any]:
        """Get random images.
        
        Args:
            nsfw: Whether to include NSFW content
            count: Number of images to return (1-100)
            
        Returns:
            JSON response containing random images
        """
        # Ensure count is within API limits
        count = min(max(count, 1), 100)
        
        params = {
            "count": count
        }
        
        if nsfw:
            params["nsfw"] = "true"
        
        try:
            response = self.session.get(f"{self.BASE_URL}/random/image", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching random images from nekos.moe: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return {"images": []}
    
    def search_images(self, 
                     query: Optional[str] = None,
                     nsfw: bool = False,
                     tags: Optional[List[str]] = None,
                     sort: str = "newest",
                     skip: int = 0,
                     limit: int = 20) -> Dict[str, Any]:
        """Search for images.
        
        Args:
            query: Search query
            nsfw: Whether to include NSFW content
            tags: List of tags to filter by
            sort: Sort method (newest, likes, oldest, relevance)
            skip: Number of images to skip
            limit: Maximum number of images to return (1-50)
            
        Returns:
            JSON response containing search results
        """
        # Ensure limit is within API limits
        limit = min(max(limit, 1), 50)
        
        # Build request body
        body = {
            "nsfw": nsfw,
            "sort": sort,
            "skip": skip,
            "limit": limit
        }
        
        if query:
            body["query"] = query
            
        if tags and len(tags) > 0:
            body["tags"] = tags
        
        try:
            response = self.session.post(f"{self.BASE_URL}/images/search", json=body)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching images from nekos.moe: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return {"images": []}
    
    def get_popular_tags(self, limit: int = 20) -> List[str]:
        """Get a list of popular tags (simulated since API doesn't provide this).
        
        Args:
            limit: Number of tags to return
            
        Returns:
            List of popular tags
        """
        # Since nekos.moe doesn't have a dedicated endpoint for popular tags,
        # we'll return a static list of common anime-related tags
        common_tags = [
            "neko", "cat_ears", "cat_girl", "kemonomimi", 
            "animal_ears", "tail", "fox_girl", "kitsune",
            "maid", "waifu", "anime_girl", "cute", 
            "kawaii", "anime", "catgirl", "nekomimi",
            "blush", "smile", "long_hair", "short_hair",
            "twintails", "ponytail", "blonde", "brown_hair",
            "black_hair", "blue_hair", "pink_hair", "purple_hair",
            "red_hair", "white_hair", "green_hair", "multicolored_hair",
            "blue_eyes", "red_eyes", "green_eyes", "brown_eyes",
            "purple_eyes", "yellow_eyes", "pink_eyes", "heterochromia",
            "school_uniform", "serafuku", "dress", "skirt",
            "thighhighs", "pantyhose", "stockings", "socks",
            "headband", "ribbon", "bow", "hairclip",
            "glasses", "megane", "fang", "fangs"
        ]
        
        # Return a random selection of tags up to the limit
        if limit >= len(common_tags):
            return common_tags
        else:
            return random.sample(common_tags, limit) 