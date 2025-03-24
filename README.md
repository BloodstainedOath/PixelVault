# PixelVault

A modern, feature-rich GTK4-based image viewer application for Arch Linux. PixelVault integrates with multiple image sources and provides a clean, intuitive interface for browsing and managing images.

## Features

- Multiple image sources: Wallhaven, Waifu.im, Waifu.pics, and Nekos.moe
- Modern grid view with infinite scrolling
- Search and tag-based filtering
- Advanced metadata filtering with search operators
- Favorites and browsing history
- Dark and light mode
- Keyboard shortcuts for power users
- Metadata display
- Drag and drop support

## Requirements

- Python 3.8+
- GTK 4
- libadwaita
- Arch Linux (or other compatible distributions)

## Installation

### Install GTK4 and libadwaita
```bash
sudo pacman -S gtk4 libadwaita
```

### Install Python dependencies
```bash
sudo pacman -S python-gobject python-pillow python-requests python-aiohttp
pip install aiofiles --user
```

### Installation Method 1: Direct Installation
```bash
git clone https://github.com/yourusername/pixelvault.git
cd pixelvault
pip install -e .
pixelvault
```

### Installation Method 2: Run Without Installing
```bash
git clone https://github.com/yourusername/pixelvault.git
cd pixelvault
python src/main.py
```

## Usage

### Keyboard Shortcuts
- `Ctrl+Q` - Quit application
- `Ctrl+F` - Focus search bar
- `Ctrl+R` - Refresh current source
- `Ctrl+D` - Add/remove current image to favorites
- `F11` - Toggle fullscreen
- `Ctrl+,` - Open preferences

### Browsing Images
1. Select an image source from the tabs at the top
2. Browse the grid of images
3. Click on an image to view it in full-screen
4. Use the tag filter to filter images by category
5. Use the search bar to search for specific images

### Managing Favorites
1. Click on an image to view it
2. Click the star icon to add it to favorites
3. Access your favorites from the sidebar

### Advanced Search Filtering
PixelVault supports advanced search with special operators for precise filtering:

- `ratio:16:9` - Filter by aspect ratio (16:9, 4:3, 21:9, 1:1)
- `width:>1920` - Filter by width (supports >, <, =, >=, <= operators)
- `height:>1080` - Filter by height
- `resolution:4k` - Filter by common resolution names (4k, 1080p, 1440p, 720p)
- `color:red` - Filter by dominant color
- `source:wallhaven` - Filter by source
- `category:anime` - Filter by category
- `tag:landscape` - Filter by specific tag

You can combine multiple filters with spaces:
```
width:>1920 height:>1080 tag:nature
```

### Tag Filtering
Each source provides different tags for filtering images:

1. **Wallhaven**:
   - Categories: general, anime, people
   - Content types: landscape, nature, space, city, etc.
   - Colors: red, blue, green, yellow, etc.
   - Purity levels: SFW, sketchy

2. **Waifu.im**:
   - Character tags: waifu, maid, marin-kitagawa, etc.
   - Attribute tags: blonde, glasses, uniform, etc.
   - Emotional tags: happy, sad, angry, cute, etc.

3. **Other Sources**:
   - Each source provides its own set of tags optimized for its content

## API Sources
- Wallhaven: https://wallhaven.cc/help/api
- Waifu.im: https://docs.waifu.im/reference/api-reference
- Waifu.pics: https://waifu.pics/docs
- Nekos.moe: https://docs.nekos.moe/

## License
GPL-3.0 