import requests
from typing import Dict, List, Optional, Any, Union
from enum import Enum

class Purity(Enum):
    """Purity levels for Wallhaven API."""
    SFW = "100"              # Only SFW
    SKETCHY = "010"          # Only Sketchy
    NSFW = "001"             # Only NSFW
    SFW_SKETCHY = "110"      # SFW + Sketchy
    SFW_NSFW = "101"         # SFW + NSFW
    SKETCHY_NSFW = "011"     # Sketchy + NSFW
    ALL = "111"              # SFW + Sketchy + NSFW

class Category(Enum):
    """Categories for Wallhaven API."""
    GENERAL = "100"
    ANIME = "010"
    PEOPLE = "001"
    GENERAL_ANIME = "110"
    GENERAL_PEOPLE = "101"
    ANIME_PEOPLE = "011"
    ALL = "111"

class Sorting(Enum):
    """Sorting options for Wallhaven API."""
    DATE_ADDED = "date_added"
    RELEVANCE = "relevance"
    RANDOM = "random"
    VIEWS = "views"
    FAVORITES = "favorites"
    TOPLIST = "toplist"

class Order(Enum):
    """Order options for Wallhaven API."""
    DESC = "desc"
    ASC = "asc"

class TopRange(Enum):
    """Time range options for toplist."""
    ONE_DAY = "1d"
    THREE_DAYS = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    SIX_MONTHS = "6M"
    ONE_YEAR = "1y"

class WallhavenAPI:
    """Client for the Wallhaven API.
    
    This client implements the Wallhaven API v1, supporting all major endpoints:
    - Search for wallpapers with filtering options
    - Get details of specific wallpapers
    - Browse user collections
    - Access user settings
    
    Authentication can be provided using an API key, which is added as both:
    - An X-API-Key header (recommended method per API docs)
    - A URL parameter "apikey" (fallback for specific endpoints)
    
    The API key can be obtained from the user's account settings page on Wallhaven.
    Without an API key, access is limited to SFW content only.
    """
    
    BASE_URL = "https://wallhaven.cc/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Wallhaven API client.
        
        Args:
            api_key: Optional API key for authenticated requests
        """
        self.api_key = api_key
        self.session = requests.Session()
        # Set user agent to avoid 403 errors
        self.session.headers.update({
            "User-Agent": "PixelVault/1.0 (https://github.com/pixelvault)"
        })
        
        if api_key:
            print(f"Initializing Wallhaven API with API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
            # Set the API key as a header for all requests
            self.session.headers.update({"X-API-Key": api_key})
            # Also keep the URL param method as fallback for specific endpoints
            self.session.params = {"apikey": api_key}
        else:
            print("Initializing Wallhaven API without an API key (NSFW content will be limited)")
            self.session.params = {}
    
    def search(self, 
               query: str = "", 
               categories: Union[str, Category] = Category.ALL, 
               purity: Union[str, Purity] = Purity.SFW, 
               sorting: Union[str, Sorting] = Sorting.DATE_ADDED, 
               order: Union[str, Order] = Order.DESC, 
               top_range: Union[str, TopRange] = TopRange.ONE_MONTH,
               atleast: Optional[str] = None,
               resolutions: Optional[List[str]] = None,
               ratios: Optional[List[str]] = None,
               colors: Optional[str] = None,
               tags: Optional[List[str]] = None,
               page: int = 1,
               seed: Optional[str] = None) -> Dict[str, Any]:
        """Search for wallpapers.
        
        Args:
            query: Search query
            categories: Category filter (general,anime,people) as 3-digit binary, e.g., "111"
            purity: Content filter (sfw,sketchy,nsfw) as 3-digit binary, e.g., "100"
            sorting: Sort results by (date_added, relevance, random, views, favorites, toplist)
            order: Order results (desc, asc)
            top_range: Time range for toplist sorting (1d, 3d, 1w, 1M, 3M, 6M, 1y)
            atleast: Minimum resolution (e.g. "1920x1080")
            resolutions: List of exact resolutions (e.g. ["1920x1080", "2560x1440"])
            ratios: List of aspect ratios (e.g. ["16x9", "21x9"])
            colors: Color to search for (hex color without the #)
            tags: List of tags to search for
            page: Page number
            seed: Seed for random sorting (to maintain consistency between pages)
            
        Returns:
            JSON response containing search results and pagination information
        """
        # Process categories
        if isinstance(categories, Category):
            categories = categories.value
            
        # Process purity
        if isinstance(purity, Purity):
            purity = purity.value
            
        # Check if NSFW content is requested without an API key
        if purity in ("110", "111") and not self.api_key:
            print("Warning: NSFW or Sketchy content requested but no API key provided.")
            print(f"Please set a valid Wallhaven API key in settings to access NSFW content.")
            # We'll continue with the request, but it will likely return only SFW content
            
        # Process sorting
        if isinstance(sorting, Sorting):
            sorting = sorting.value
            
        # Process order
        if isinstance(order, Order):
            order = order.value
            
        # Process top_range
        if isinstance(top_range, TopRange):
            top_range = top_range.value
        
        # Create query from tags if provided
        if tags and not query:
            query = " ".join([f"+{tag}" for tag in tags])
        
        params = {
            "q": query,
            "categories": categories,
            "purity": purity,
            "sorting": sorting,
            "order": order,
            "page": page
        }
        
        # Add topRange parameter only when sorting by toplist
        if sorting == Sorting.TOPLIST.value or sorting == "toplist":
            params["topRange"] = top_range
            
        # Add seed parameter for random sorting if provided
        if (sorting == Sorting.RANDOM.value or sorting == "random") and seed:
            params["seed"] = seed
            
        # Add optional parameters if provided
        if atleast:
            params["atleast"] = atleast
            
        if resolutions:
            params["resolutions"] = ",".join(resolutions)
            
        if ratios:
            params["ratios"] = ",".join(ratios)
            
        if colors:
            params["colors"] = colors
        
        try:
            response = self.session.get(f"{self.BASE_URL}/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check if we got any results
            if "data" in data and len(data["data"]) == 0 and purity in ("110", "111"):
                print(f"No results found. If you're looking for NSFW content, verify your Wallhaven API key is valid.")
                print(f"API returned meta: {data.get('meta', {})}")
            
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Authentication error: Invalid API key")
                # Return empty result set
                return {"data": [], "meta": {"current_page": page, "last_page": page}, "error": "Invalid API key"}
            elif e.response.status_code == 429:
                print("Rate limit exceeded. Please try again later.")
                # Return empty result set
                return {"data": [], "meta": {"current_page": page, "last_page": page}, "error": "Rate limit exceeded"}
            elif e.response.status_code == 400:
                print(f"Bad request: Invalid parameters - {e}")
                return {"data": [], "meta": {"current_page": page, "last_page": page}, "error": "Invalid parameters"}
            else:
                print(f"HTTP error {e.response.status_code}: {e}")
                return {"data": [], "meta": {"current_page": page, "last_page": page}, "error": f"HTTP error {e.response.status_code}"}
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return {"data": [], "meta": {"current_page": page, "last_page": page}, "error": str(e)}
    
    def get_wallpaper(self, wallpaper_id: str) -> Dict[str, Any]:
        """Get details for a specific wallpaper.
        
        Args:
            wallpaper_id: The ID of the wallpaper
            
        Returns:
            JSON response containing wallpaper details
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/w/{wallpaper_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                if not self.api_key:
                    print("Authentication error: API key required for this wallpaper (likely NSFW content)")
                    return {"data": None, "error": "API key required for NSFW content"}
                else:
                    print("Authentication error: Invalid API key or insufficient permissions")
                    return {"data": None, "error": "Invalid API key or insufficient permissions"}
            else:
                raise
    
    def get_tag(self, tag_id: int) -> Dict[str, Any]:
        """Get information about a specific tag.
        
        Args:
            tag_id: The ID of the tag
            
        Returns:
            JSON response containing tag information
        """
        response = self.session.get(f"{self.BASE_URL}/tag/{tag_id}")
        response.raise_for_status()
        return response.json()
    
    def get_user_settings(self) -> Dict[str, Any]:
        """Get authenticated user settings.
        
        Requires a valid API key.
        
        Returns:
            JSON response containing user settings
        """
        if not self.api_key:
            raise ValueError("API key is required for this operation")
            
        try:
            response = self.session.get(f"{self.BASE_URL}/settings")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Authentication error: Invalid API key")
                return {"data": None, "error": "Invalid API key"}
            else:
                raise
    
    def get_collections(self, username: Optional[str] = None) -> Dict[str, Any]:
        """Get collections for a user.
        
        If username is provided, returns public collections for that user.
        If username is not provided, returns collections for the authenticated user (requires API key).
        
        Args:
            username: Username to get collections for
            
        Returns:
            JSON response containing collections
        """
        if username:
            url = f"{self.BASE_URL}/collections/{username}"
        else:
            if not self.api_key:
                raise ValueError("API key is required when username is not provided")
            url = f"{self.BASE_URL}/collections"
        
        try:    
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Authentication error: Invalid API key")
                return {"data": [], "error": "Invalid API key"}
            elif e.response.status_code == 404:
                print(f"User not found: {username}")
                return {"data": [], "error": f"User not found: {username}"}
            else:
                raise
    
    def get_collection_wallpapers(self, username: str, collection_id: int, page: int = 1) -> Dict[str, Any]:
        """Get wallpapers from a specific collection.
        
        Args:
            username: Username of the collection owner
            collection_id: ID of the collection
            page: Page number
            
        Returns:
            JSON response containing wallpapers in the collection
        """
        params = {"page": page}
        try:
            response = self.session.get(f"{self.BASE_URL}/collections/{username}/{collection_id}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Authentication error: This collection may be private and requires a valid API key")
                return {"data": [], "meta": {"current_page": page, "last_page": page}, "error": "Authentication required"}
            elif e.response.status_code == 404:
                print(f"Collection not found: User={username}, Collection ID={collection_id}")
                return {"data": [], "meta": {"current_page": page, "last_page": page}, "error": "Collection not found"}
            else:
                raise
    
    def get_latest(self, page: int = 1, **kwargs) -> Dict[str, Any]:
        """Get latest wallpapers.
        
        Args:
            page: Page number
            **kwargs: Additional search parameters
            
        Returns:
            JSON response containing latest wallpapers
        """
        return self.search(sorting=Sorting.DATE_ADDED, page=page, **kwargs)
    
    def get_top(self, page: int = 1, top_range: Union[str, TopRange] = TopRange.ONE_MONTH, **kwargs) -> Dict[str, Any]:
        """Get top wallpapers.
        
        Args:
            page: Page number
            top_range: Time range for toplist
            **kwargs: Additional search parameters
            
        Returns:
            JSON response containing top wallpapers
        """
        return self.search(sorting=Sorting.TOPLIST, top_range=top_range, page=page, **kwargs)
    
    def get_random(self, page: int = 1, seed: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Get random wallpapers.
        
        Args:
            page: Page number
            seed: Seed for random results (to maintain consistency between pages)
            **kwargs: Additional search parameters
            
        Returns:
            JSON response containing random wallpapers
        """
        return self.search(sorting=Sorting.RANDOM, page=page, seed=seed, **kwargs)
        
    def verify_api_key(self) -> bool:
        """Verify that the current API key is valid.
        
        Returns:
            True if API key is valid, False otherwise
        """
        if not self.api_key:
            print("No API key provided to verify")
            return False
            
        try:
            # Try to get user settings which requires authentication
            response = self.session.get(f"{self.BASE_URL}/settings")
            response.raise_for_status()
            print("API key verification successful")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("API key verification failed: Invalid API key")
                return False
            else:
                print(f"API key verification failed: HTTP error {e.response.status_code}")
                return False
        except Exception as e:
            print(f"API key verification failed: {str(e)}")
            return False
            
    def debug_request(self, url: str, params: Dict[str, Any] = None) -> None:
        """Debug an API request by showing request and response details."""
        print(f"\nDEBUG REQUEST: {url}")
        print(f"Headers: {self.session.headers}")
        print(f"Params: {params if params else self.session.params}")
        
        try:
            response = self.session.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"Response Body: {response.text[:500]}...")  # Show first 500 chars
        except Exception as e:
            print(f"Error during debug request: {e}")
