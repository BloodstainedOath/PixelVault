import requests
from typing import Dict, List, Optional, Any
import json
import os

class WaifuPicsAPI:
    """Client for the Waifu.pics API."""
    
    # Use the official API URL by default, with option to use a local server
    DEFAULT_BASE_URL = "https://api.waifu.pics"
    LOCAL_API_PATH = "/home/cursed-undead/Music/waifu-api"
    
    def __init__(self, use_local: bool = False, local_url: str = "http://localhost:8000"):
        """Initialize the Waifu.pics API client.
        
        Args:
            use_local: Whether to use a local server
            local_url: URL of the local server
        """
        self.session = requests.Session()
        
        # Determine if we should use the local API server
        self.use_local = use_local
        self.local_url = local_url
        self.base_url = self.local_url if use_local else self.DEFAULT_BASE_URL
        
        # Cache the available endpoints
        self._sfw_endpoints = None
        self._nsfw_endpoints = None
        
        # If using local server, try to read the config
        if use_local:
            self._read_local_endpoints()
    
    def _read_local_endpoints(self):
        """Read endpoints from the local API config."""
        try:
            config_path = os.path.join(self.LOCAL_API_PATH, "config", "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'endpoints' in config:
                        self._sfw_endpoints = config['endpoints'].get('sfw', [])
                        self._nsfw_endpoints = config['endpoints'].get('nsfw', [])
        except Exception as e:
            print(f"Error reading local API config: {e}")
    
    def get_image(self, category: str = "sfw", endpoint: str = "waifu") -> Dict[str, Any]:
        """Get a single image.
        
        Args:
            category: Image category (sfw, nsfw)
            endpoint: Image endpoint (waifu, neko, shinobu, etc.)
            
        Returns:
            JSON response containing image URL
        """
        try:
            response = self.session.get(f"{self.base_url}/{category}/{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image from Waifu.pics: {e}")
            # Fall back to the default API if local fails
            if self.use_local:
                print("Falling back to default API...")
                original_base_url = self.base_url
                self.base_url = self.DEFAULT_BASE_URL
                try:
                    result = self.get_image(category, endpoint)
                    return result
                finally:
                    self.base_url = original_base_url
            return {"url": ""}
    
    def get_many(self, category: str = "sfw", endpoint: str = "waifu", exclude: List[str] = None, count: int = 30) -> Dict[str, Any]:
        """Get multiple images.
        
        Args:
            category: Image category (sfw, nsfw)
            endpoint: Image endpoint (waifu, neko, shinobu, etc.)
            exclude: List of image URLs to exclude
            count: Number of images to request (maximum is 30)
            
        Returns:
            JSON response containing image URLs
        """
        if exclude is None:
            exclude = []
        
        # Enforce maximum count
        count = min(count, 30)
        
        data = {"exclude": exclude}
        
        try:
            # Make multiple requests if needed to get the desired count
            # Some endpoints might not have enough images
            all_files = []
            attempt_count = 0
            max_attempts = 5  # Limit to avoid infinite loops
            
            while len(all_files) < count and attempt_count < max_attempts:
                # Update exclude list with files we've already seen
                data["exclude"] = exclude + all_files
                
                response = self.session.post(f"{self.base_url}/many/{category}/{endpoint}", json=data)
                response.raise_for_status()
                result = response.json()
                
                if "files" in result and result["files"]:
                    # Filter out duplicates
                    new_files = [f for f in result["files"] if f not in all_files]
                    all_files.extend(new_files)
                    if not new_files:
                        # If we got no new files, break to avoid infinite loop
                        break
                else:
                    # If no files were returned, break
                    break
                
                attempt_count += 1
            
            return {"files": all_files[:count]}
        except requests.exceptions.RequestException as e:
            print(f"Error fetching multiple images from Waifu.pics: {e}")
            # Fall back to the default API if local fails
            if self.use_local:
                print("Falling back to default API...")
                original_base_url = self.base_url
                self.base_url = self.DEFAULT_BASE_URL
                try:
                    result = self.get_many(category, endpoint, exclude, count)
                    return result
                finally:
                    self.base_url = original_base_url
            return {"files": []}
    
    def get_random_images(self, count: int = 30, is_nsfw: bool = False, selected_endpoints: List[str] = None) -> Dict[str, Any]:
        """Get random images from various endpoints.
        
        Args:
            count: Number of images to request
            is_nsfw: Whether to include NSFW images
            selected_endpoints: Specific endpoints to use (tags), if None, all available endpoints will be used
            
        Returns:
            JSON response containing image URLs
        """
        category = "nsfw" if is_nsfw else "sfw"
        
        # Get a list of available endpoints (tags)
        available_endpoints = self.get_nsfw_endpoints() if is_nsfw else self.get_sfw_endpoints()
        
        # Use selected endpoints if provided and valid
        if selected_endpoints and len(selected_endpoints) > 0:
            # Filter selected endpoints to make sure they're valid
            valid_endpoints = []
            
            # Check if endpoints are valid by comparing lowercased strings
            available_endpoints_lower = [ep.lower() for ep in available_endpoints]
            for ep in selected_endpoints:
                if ep.lower() in available_endpoints_lower:
                    # Find the original endpoint with correct case
                    idx = available_endpoints_lower.index(ep.lower())
                    valid_endpoints.append(available_endpoints[idx])
                else:
                    print(f"Warning: Endpoint '{ep}' is not valid for {category} category.")
            
            if not valid_endpoints:
                print(f"Warning: None of the selected endpoints {selected_endpoints} are valid for {category} category. Using all available endpoints.")
                endpoints = available_endpoints
            else:
                print(f"Using selected endpoints: {valid_endpoints}")
                endpoints = valid_endpoints
        else:
            # Use all available endpoints
            endpoints = available_endpoints
        
        # Shuffle endpoints to increase variety
        import random
        random.shuffle(endpoints)
        
        # Get images from different endpoints
        all_files = []
        images_per_endpoint = max(1, count // len(endpoints))
        
        for endpoint in endpoints:
            if len(all_files) >= count:
                break
                
            try:
                result = self.get_many(category, endpoint, exclude=all_files, count=images_per_endpoint)
                if "files" in result and result["files"]:
                    all_files.extend(result["files"])
            except Exception as e:
                print(f"Error fetching images from endpoint {endpoint}: {e}")
                continue
        
        print(f"Waifu.pics API response: {len(all_files)} images")
        return {"files": all_files[:count]}
    
    def get_sfw_endpoints(self) -> List[str]:
        """Get available SFW endpoints.
        
        Returns:
            List of available SFW endpoints
        """
        # Use cached endpoints from config if available
        if self._sfw_endpoints is not None:
            return self._sfw_endpoints
        
        # Otherwise use the hardcoded list
        return [
            "waifu", "neko", "shinobu", "megumin", "bully", "cuddle", "cry",
            "hug", "awoo", "kiss", "lick", "pat", "smug", "bonk", "yeet",
            "blush", "smile", "wave", "highfive", "handhold", "nom", "bite",
            "glomp", "slap", "kill", "kick", "happy", "wink", "poke", "dance",
            "cringe"
        ]
    
    def get_nsfw_endpoints(self) -> List[str]:
        """Get available NSFW endpoints.
        
        Returns:
            List of available NSFW endpoints
        """
        # Use cached endpoints from config if available
        if self._nsfw_endpoints is not None:
            return self._nsfw_endpoints
            
        # Otherwise use the hardcoded list
        return ["waifu", "neko", "trap", "blowjob"]
    
    def get_all_tags(self) -> Dict[str, List[str]]:
        """Get all available tags (endpoints) from the API.
        
        Returns:
            Dictionary containing SFW and NSFW tags
        """
        return {
            "sfw": self.get_sfw_endpoints(),
            "nsfw": self.get_nsfw_endpoints()
        }
