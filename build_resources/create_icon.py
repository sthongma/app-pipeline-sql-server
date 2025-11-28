#!/usr/bin/env python3
"""
Script to convert PNG icon to ICO format for Windows executable.
Creates a multi-resolution .ico file from an existing PNG icon.
"""

from PIL import Image
import os
import sys

def create_icon():
    """Convert PNG icon to ICO format with multiple resolutions."""
    # Paths
    png_path = "ui/icons/upload_24px.png"
    ico_path = "build_resources/app_icon.ico"

    # Check if PNG exists
    if not os.path.exists(png_path):
        print(f"[ERROR] PNG file not found at {png_path}")
        print("Available icons:")
        if os.path.exists("ui/icons"):
            for icon in os.listdir("ui/icons"):
                if icon.endswith(".png"):
                    print(f"  - ui/icons/{icon}")
        sys.exit(1)

    try:
        # Open PNG image
        print(f"[INFO] Reading icon from: {png_path}")
        img = Image.open(png_path)

        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Create multiple sizes for ICO
        sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]

        print(f"[INFO] Converting to ICO with sizes: {sizes}")

        # Save as ICO
        img.save(ico_path, format='ICO', sizes=sizes)

        print(f"[SUCCESS] Icon created successfully: {ico_path}")
        print(f"[INFO] File size: {os.path.getsize(ico_path) / 1024:.2f} KB")

    except Exception as e:
        print(f"[ERROR] Error creating icon: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 50)
    print("Creating Application Icon")
    print("=" * 50)
    create_icon()
    print("=" * 50)
