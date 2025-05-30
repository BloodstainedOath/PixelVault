# PixelVault

A GTK-based wallpaper app that fetches images from multiple sources:
- Wallhaven
- Waifu.im

## Features
- Switch between different wallpaper sources
- Browse and search for wallpapers
- Set wallpapers directly from the app
- Save favorite wallpapers
- Automatically download images to a specified folder
- Sort images by Latest, Top, or Random (for Wallhaven)
- Support for Wallhaven API key to access NSFW and Sketchy content
- Modern UI with clean grid layout, rounded corners, and smooth transitions

## Installation

### Arch Linux

1. Install system dependencies:
```bash
sudo pacman -S python-gobject gtk3 python-pip python-pillow python-requests
```

2. Set up virtual environment:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the application:
```bash
python -m pixelvault
```

### Alternative Installation

If you prefer to install the Python dependencies directly:

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python -m pixelvault
```

## Requirements
- Python 3.8+
- GTK 3.0+
- PyGObject
- Requests
- Pillow

## API Integration Notes

PixelVault integrates with the following APIs:

### Wallhaven
- Uses the public API at https://wallhaven.cc/api/v1
- Provides high-quality wallpapers from various categories
- API key support for accessing NSFW and Sketchy content
- Configure your API key in the Settings dialog

### Waifu.im
- Uses the API at https://api.waifu.im (version v6)
- Provides anime-style character images with various tags
- See full documentation at https://docs.waifu.im/

## Usage

### Basic Navigation
- Use the Source dropdown to switch between Wallhaven and Waifu.im
- For Wallhaven, use the Sort dropdown to sort by Latest, Top, or Random
- Click on any image to open it in a larger view
- From the image view, you can download the image or set it as wallpaper

### Advanced Options
- Click the "Advanced Options" button to access additional filters:
  - For Wallhaven: Content categories (General, Anime, People) and Content filters (SFW, Sketchy, NSFW)
  - For Waifu.im: Various tags to filter images

### Wallhaven API Key
To access Sketchy and NSFW content from Wallhaven:
1. Create an account on [Wallhaven](https://wallhaven.cc/)
2. Get your API key from your [Wallhaven settings page](https://wallhaven.cc/settings/account)
3. In PixelVault, click the Settings button (gear icon)
4. Go to the Wallhaven tab and enter your API key
5. Click "Test Key" to verify it works
6. Click "Save" to apply the settings

### Auto-Download Feature
PixelVault allows automatic downloading of images:

1. Click the Settings button (gear icon) in the top-right corner
2. Go to the "Auto Download" tab
3. Toggle "Automatically download images" to enable/disable the feature
4. Set your preferred download directory
5. Choose whether to organize by source
6. Select your preferred filename format
7. Click "Save" to apply the settings

With auto-download enabled, any image you click on will be automatically saved to your specified directory while also opening in the preview dialog.

## Recent Improvements
- **Memory Management**: Fixed memory handling to prevent crashes when browsing large image collections
- **UI Modernization**: Improved grid view with better spacing, rounded corners, and hover effects
- **Wallhaven API Key Support**: Added ability to use NSFW and Sketchy content with proper API key
- **Enhanced Download Options**: Added options for organizing by source and customizing filename formats
- **GIF Support**: Added support for animated GIFs with proper frame handling and animation display
