"""
Icon Manager - Loads Material Icons from local PNG files for UI
Icons are pre-downloaded using download_icons_simple.py
"""
import os
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps
from pathlib import Path
from typing import Optional


class IconManager:
    """Manages Material Icons - loads from local PNG files"""

    # Icon mapping: friendly name -> Material Symbol file name
    ICON_MAP = {
        'search': 'search',
        'upload': 'upload',
        'folder': 'folder_open',
        'folder_input': 'folder',
        'settings': 'settings',
        'add': 'add',
        'remove': 'remove',
        'save': 'check_circle',
        'edit': 'edit',
        'time': 'schedule',
        'refresh': 'refresh',
        'key': 'vpn_key',
    }

    def __init__(self, icon_dir: str = "ui/icons", icon_size: int = 20):
        """
        Initialize IconManager

        Args:
            icon_dir: Directory containing icon PNG files
            icon_size: Size of icons in pixels (default 20)
        """
        self.icon_dir = Path(icon_dir)
        self.icon_size = icon_size

        # Cache for loaded CTkImages
        self._loaded_icons = {}

    def get_icon(self, icon_name: str, size: Optional[int] = None) -> Optional[ctk.CTkImage]:
        """
        Get icon as CTkImage from local PNG files

        Args:
            icon_name: Name of icon (e.g., 'search', 'upload')
            size: Size override (default uses self.icon_size)

        Returns:
            CTkImage or None if failed
        """
        size = size or self.icon_size
        cache_key = f"{icon_name}_{size}"

        # Return from cache if available
        if cache_key in self._loaded_icons:
            return self._loaded_icons[cache_key]

        # Get Material Symbol file name
        symbol_name = self.ICON_MAP.get(icon_name, icon_name)

        # Try to load from local PNG file
        # Try exact size first, then fallback to nearby sizes
        possible_sizes = [size, 20, 24, 40, 48]
        icon_path = None

        for try_size in possible_sizes:
            try_path = self.icon_dir / f"{symbol_name}_{try_size}px.png"
            if try_path.exists():
                icon_path = try_path
                break

        if icon_path and icon_path.exists():
            try:
                img_light = Image.open(icon_path)
                # Resize if needed
                if img_light.size[0] != size:
                    img_light = img_light.resize((size, size), Image.LANCZOS)

                # Create white version for dark theme while preserving transparency
                img_dark = img_light.convert('RGBA')
                # Extract alpha channel
                r, g, b, a = img_dark.split()
                # Invert only RGB channels (not alpha)
                rgb = Image.merge('RGB', (r, g, b))
                rgb_inverted = ImageOps.invert(rgb)
                r2, g2, b2 = rgb_inverted.split()
                # Merge back with original alpha
                img_dark = Image.merge('RGBA', (r2, g2, b2, a))

                ctk_image = ctk.CTkImage(light_image=img_light, dark_image=img_dark, size=(size, size))
                self._loaded_icons[cache_key] = ctk_image
                return ctk_image
            except Exception as e:
                print(f"Error loading icon {icon_name}: {e}")
                pass

        # Fallback: create a simple placeholder
        return self._create_placeholder(size)

    def _create_placeholder(self, size: int) -> ctk.CTkImage:
        """
        Create a simple placeholder icon

        Args:
            size: Icon size

        Returns:
            CTkImage with simple placeholder
        """
        # Create dark placeholder for light theme
        img_light = Image.new('RGBA', (size, size), (128, 128, 128, 0))
        draw_light = ImageDraw.Draw(img_light)
        margin = size // 4
        draw_light.ellipse([margin, margin, size - margin, size - margin], fill=(128, 128, 128, 180))

        # Create light placeholder for dark theme
        img_dark = Image.new('RGBA', (size, size), (200, 200, 200, 0))
        draw_dark = ImageDraw.Draw(img_dark)
        draw_dark.ellipse([margin, margin, size - margin, size - margin], fill=(200, 200, 200, 180))

        return ctk.CTkImage(light_image=img_light, dark_image=img_dark, size=(size, size))

    def preload_icons(self, icon_names: list):
        """
        Preload a list of icons

        Args:
            icon_names: List of icon names to preload
        """
        for icon_name in icon_names:
            self.get_icon(icon_name)


# Global icon manager instance
_icon_manager = None

def get_icon_manager(icon_size: int = 20) -> IconManager:
    """Get global IconManager instance"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager(icon_size=icon_size)
    return _icon_manager

def get_icon(icon_name: str, size: Optional[int] = None) -> Optional[ctk.CTkImage]:
    """
    Convenience function to get icon

    Args:
        icon_name: Name of icon
        size: Optional size override

    Returns:
        CTkImage or None
    """
    manager = get_icon_manager()
    return manager.get_icon(icon_name, size)
