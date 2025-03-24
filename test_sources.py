#!/usr/bin/env python3
import asyncio
import sys

from src.widgets.api_clients import (
    WallhavenClient,
    WaifuImClient,
    WaifuPicsClient,
    NekosMoeClient
)

async def test_client(name, client):
    print(f"\nTesting {name}...")
    try:
        images = await client.get_images()
        print(f"  Got {len(images)} images")
        if images:
            print(f"  First image: {images[0].get('title')} - {images[0].get('url')}")
            return len(images) > 0
        else:
            print("  No images returned!")
            return False
    except Exception as e:
        print(f"  Error testing {name}: {e}")
        return False

async def main():
    clients = {
        "Wallhaven": WallhavenClient(),
        "Waifu.im": WaifuImClient(),
        "Waifu.pics": WaifuPicsClient(),
        "Nekos.moe": NekosMoeClient()
    }
    
    results = {}
    
    for name, client in clients.items():
        results[name] = await test_client(name, client)
    
    print("\nSummary:")
    success = True
    for name, result in results.items():
        status = "✅ Working" if result else "❌ Not working"
        print(f"{name}: {status}")
        if not result:
            success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 