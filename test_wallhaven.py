#!/usr/bin/env python3
"""Test script for the Wallhaven API client."""

import sys
from pixelvault.api.wallhaven import WallhavenAPI, Category, Purity, Sorting

def main():
    """Test the Wallhaven API client."""
    # Create a new API client
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        print(f"Using provided API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    
    api = WallhavenAPI(api_key=api_key)
    
    # Debug a basic search request
    print("\n=== Testing search API ===")
    api.debug_request(f"{api.BASE_URL}/search")
    
    # Try a search
    print("\n=== Performing wallpaper search ===")
    results = api.search(
        query="nature",
        categories=Category.GENERAL,
        purity=Purity.SFW,
        page=1
    )
    
    # Print search results summary
    if "data" in results:
        wallpapers = results["data"]
        meta = results.get("meta", {})
        print(f"Found {len(wallpapers)} wallpapers (page {meta.get('current_page', 1)} of {meta.get('last_page', 1)})")
        
        if wallpapers:
            # Print basic info about the first wallpaper
            first = wallpapers[0]
            print(f"\nFirst wallpaper: {first.get('id')}")
            print(f"URL: {first.get('url')}")
            print(f"Resolution: {first.get('resolution')}")
            print(f"File type: {first.get('file_type')}")
            print(f"File size: {first.get('file_size', 0) / 1024:.2f} KB")
            print(f"Purity: {first.get('purity')}")
            print(f"Tags count: {len(first.get('tags', []))}")
            
            # Try to get detailed info for this wallpaper
            print(f"\n=== Getting wallpaper details for {first.get('id')} ===")
            try:
                wallpaper = api.get_wallpaper(first.get('id'))
                if "data" in wallpaper:
                    data = wallpaper["data"]
                    print(f"Detailed info: {data.get('id')}")
                    print(f"Tags: {', '.join([tag.get('name') for tag in data.get('tags', [])])}")
                    print(f"Uploader: {data.get('uploader', {}).get('username')}")
                else:
                    print(f"Error fetching wallpaper details: {wallpaper.get('error')}")
            except Exception as e:
                print(f"Error getting wallpaper details: {e}")
    else:
        print(f"Search returned error: {results.get('error', 'Unknown error')}")
    
    # If we have an API key, test authenticated endpoints
    if api_key:
        print("\n=== Testing API key verification ===")
        if api.verify_api_key():
            print("API key is valid!")
            
            # Test getting user settings
            print("\n=== Getting user settings ===")
            try:
                settings = api.get_user_settings()
                if "data" in settings:
                    data = settings["data"]
                    print(f"User settings: {data}")
                else:
                    print(f"Error getting user settings: {settings.get('error')}")
            except Exception as e:
                print(f"Error getting user settings: {e}")
            
            # Test getting collections
            print("\n=== Getting user collections ===")
            try:
                collections = api.get_collections()
                if "data" in collections:
                    data = collections["data"]
                    print(f"Found {len(data)} collections:")
                    for i, collection in enumerate(data[:5]):  # Show up to 5 collections
                        print(f"{i+1}. {collection.get('label')} (ID: {collection.get('id')}) - {collection.get('count')} wallpapers")
                    
                    # If there are collections, try to get wallpapers from one
                    if data:
                        collection = data[0]
                        print(f"\n=== Getting wallpapers from collection: {collection.get('label')} ===")
                        try:
                            collection_wallpapers = api.get_collection_wallpapers(
                                username=collection.get('owner', 'unknown'),
                                collection_id=collection.get('id'),
                                page=1
                            )
                            if "data" in collection_wallpapers:
                                wallpapers = collection_wallpapers["data"]
                                print(f"Found {len(wallpapers)} wallpapers in the collection")
                            else:
                                print(f"Error getting collection wallpapers: {collection_wallpapers.get('error')}")
                        except Exception as e:
                            print(f"Error getting collection wallpapers: {e}")
                else:
                    print(f"Error getting collections: {collections.get('error')}")
            except Exception as e:
                print(f"Error getting collections: {e}")
        else:
            print("API key verification failed!")
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    main() 