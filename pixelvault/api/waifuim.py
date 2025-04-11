import requests
from typing import Dict, List, Optional, Any, Union
import sys
import importlib.util

# Try to import the official waifuim.py library if available
try:
    waifuim_spec = importlib.util.find_spec('waifuim')
    has_waifuim_lib = waifuim_spec is not None
except ImportError:
    has_waifuim_lib = False

if has_waifuim_lib:
    try:
        import waifuim
        import asyncio
        print("Using official waifuim.py library")
    except ImportError:
        has_waifuim_lib = False


class WaifuImAPI:
    """Client for the Waifu.im API."""
    
    BASE_URL = "https://api.waifu.im"
    API_VERSION = "v6"  # Current API version
    
    def __init__(self, token: Optional[str] = None):
        """Initialize the Waifu.im API client.
        
        Args:
            token: Optional token for authenticated requests
        """
        self.token = token
        
        # Use the official library if available
        self.use_official_lib = has_waifuim_lib
        
        if self.use_official_lib:
            # Create the async client
            self.async_client = waifuim.WaifuAioClient(token=token)
            # Create an event loop for async calls
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        else:
            # Fall back to requests-based client
            self.session = requests.Session()
            
            # Set default headers
            self.session.headers.update({
                "Accept-Version": self.API_VERSION,
                "Content-Type": "application/json"
            })
            
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def get_images(self, 
                  included_tags: Optional[List[str]] = None,
                  excluded_tags: Optional[List[str]] = None,
                  is_nsfw: Optional[bool] = False,
                  gif: Optional[bool] = None,
                  orientation: Optional[str] = None,
                  width: Optional[str] = None,
                  height: Optional[str] = None,
                  limit: Optional[int] = 30,
                  many: bool = True) -> Dict[str, Any]:
        """Get images from Waifu.im.
        
        Args:
            included_tags: List of tags to include
            excluded_tags: List of tags to exclude
            is_nsfw: Whether to include NSFW content
            gif: Whether to include GIF images
            orientation: Image orientation (landscape, portrait, square)
            width: Width constraint (e.g., ">=1920")
            height: Height constraint (e.g., ">=1080")
            limit: Maximum number of images to return (1-30)
            many: Whether to return multiple images
            
        Returns:
            JSON response containing images
        """
        if self.use_official_lib:
            try:
                # Use the official library
                async def fetch_images():
                    images = await self.async_client.search(
                        included_tags=included_tags,
                        excluded_tags=excluded_tags,
                        is_nsfw=is_nsfw,
                        gif=gif,
                        orientation=orientation,
                        width=width,
                        height=height,
                        limit=limit,
                        raw=True
                    )
                    return images
                
                # Run the async function and get the result
                result = self.loop.run_until_complete(fetch_images())
                return result
            except Exception as e:
                print(f"Error using official waifuim.py library: {e}")
                # Fall back to requests-based implementation
                return self._get_images_with_requests(
                    included_tags, excluded_tags, is_nsfw, 
                    gif, orientation, width, height, limit, many
                )
        else:
            # Use the requests-based implementation
            return self._get_images_with_requests(
                included_tags, excluded_tags, is_nsfw, 
                gif, orientation, width, height, limit, many
            )
    
    def _get_images_with_requests(self,
                                included_tags: Optional[List[str]] = None,
                                excluded_tags: Optional[List[str]] = None,
                                is_nsfw: Optional[bool] = False,
                                gif: Optional[bool] = None,
                                orientation: Optional[str] = None,
                                width: Optional[str] = None,
                                height: Optional[str] = None,
                                limit: Optional[int] = 30,
                                many: bool = True) -> Dict[str, Any]:
        """Fallback method to get images using the requests library."""
        params = {}
        
        if included_tags:
            params["included_tags"] = included_tags
        if excluded_tags:
            params["excluded_tags"] = excluded_tags
        if is_nsfw is not None:
            params["is_nsfw"] = str(is_nsfw).lower()
        if gif is not None:
            params["gif"] = str(gif).lower()
        if orientation:
            params["orientation"] = orientation
        if width:
            params["width"] = width
        if height:
            params["height"] = height
        if limit:
            params["limit"] = limit
        
        try:
            response = self.session.get(f"{self.BASE_URL}/search", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching images from Waifu.im: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return {"images": []}
    
    def get_random(self, is_nsfw: bool = False, selected_tags: List[str] = None) -> Dict[str, Any]:
        """Get random images.
        
        Args:
            is_nsfw: Whether to include NSFW content
            selected_tags: List of tags to filter by (if None, combines results from various tags)
            
        Returns:
            JSON response containing random images
        """
        # If specific tags are selected, use those directly
        if selected_tags and len(selected_tags) > 0:
            print(f"Fetching Waifu.im images with selected tags: {selected_tags}")
            result = self.get_images(
                included_tags=selected_tags,
                is_nsfw=is_nsfw,
                limit=30
            )
            print(f"Waifu.im API response with tags {selected_tags}: {len(result.get('images', [])) if 'images' in result else 0} images")
            return result
            
        # Otherwise make multiple API calls and combine the results to get more images
        all_images = []
        
        # Try different tag combinations to get more variety
        tag_combinations = [
            ["waifu"],
            ["maid"],
            ["uniform"],
            ["oppai"],
            ["waifu", "maid"],
            ["raiden-shogun"],
            ["marin-kitagawa"],
            [],  # No specific tags
        ]
        
        # Try each combination to get more images
        for tags in tag_combinations:
            try:
                # Get images for this tag combination
                response = self.get_images(
                    included_tags=tags if tags else None,
                    is_nsfw=is_nsfw,
                    limit=10
                )
                
                # Add new images to our collection
                if "images" in response and response["images"]:
                    # Filter out duplicates
                    new_images = []
                    for img in response["images"]:
                        if not any(existing.get("image_id") == img.get("image_id") for existing in all_images):
                            new_images.append(img)
                    
                    all_images.extend(new_images)
                
                # If we have enough images, stop making requests
                if len(all_images) >= 20:
                    break
                    
            except Exception as e:
                print(f"Error fetching images with tags {tags}: {e}")
                continue
        
        # Return the combined results
        result = {"images": all_images}
        print(f"Waifu.im API combined response: {len(all_images)} images")
        return result
    
    def get_favorites(self) -> Dict[str, Any]:
        """Get user's favorite images (requires authentication).
        
        Returns:
            JSON response containing favorite images
        """
        if not self.token:
            raise ValueError("Authentication token required for this endpoint")
        
        if self.use_official_lib:
            try:
                async def fetch_favorites():
                    return await self.async_client.fav(raw=True)
                
                return self.loop.run_until_complete(fetch_favorites())
            except Exception as e:
                print(f"Error using official waifuim.py library for favorites: {e}")
                # Fall back to requests implementation
        
        try:
            response = self.session.get(f"{self.BASE_URL}/fav")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching favorites from Waifu.im: {e}")
            return {"images": []}
    
    def get_tags(self) -> Dict[str, Any]:
        """Get available tags.
        
        Returns:
            JSON response containing available tags
        """
        if self.use_official_lib:
            try:
                async def fetch_tags():
                    return await self.async_client.tags(raw=True)
                
                return self.loop.run_until_complete(fetch_tags())
            except Exception as e:
                print(f"Error using official waifuim.py library for tags: {e}")
                # Fall back to requests implementation
        
        try:
            response = self.session.get(f"{self.BASE_URL}/tags")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching tags from Waifu.im: {e}")
            return {"versatile": [], "nsfw": []}

    def get_all_tags(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available tags from the API.
        
        Returns:
            Dictionary containing versatile and nsfw tags
        """
        tags_data = self.get_tags()
        result = {
            "versatile": [],
            "nsfw": []
        }
        
        # Process tag data from API
        if "versatile" in tags_data:
            result["versatile"] = tags_data["versatile"]
            
        if "nsfw" in tags_data:
            result["nsfw"] = tags_data["nsfw"]
        
        return result
