"""
Simple script to download Material Icons without dependencies
"""
import os
import requests
from pathlib import Path

# Icon directory
ICON_DIR = Path("ui/icons")
ICON_DIR.mkdir(parents=True, exist_ok=True)

# Material Symbols base URL
MATERIAL_SYMBOLS_BASE = "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined"

# Icons to download: friendly_name -> (material_symbol_name, sizes)
ICONS = {
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

SIZES = [20, 24]  # Download multiple sizes


def download_icon_svg_to_png(symbol_name: str, size: int) -> bool:
    """Download SVG icon and convert to PNG"""
    url = f"{MATERIAL_SYMBOLS_BASE}/{symbol_name}/default/{size}px.svg"
    output_path = ICON_DIR / f"{symbol_name}_{size}px.png"

    if output_path.exists():
        print(f"  ✓ Already cached: {output_path.name}")
        return True

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Try to convert SVG to PNG using cairosvg
            try:
                import cairosvg
                png_bytes = cairosvg.svg2png(
                    bytestring=response.content,
                    output_width=size,
                    output_height=size
                )
                with open(output_path, 'wb') as f:
                    f.write(png_bytes)
                print(f"  ✓ Downloaded: {output_path.name} (via cairosvg)")
                return True
            except ImportError:
                # Save SVG file instead (will need runtime conversion)
                svg_path = ICON_DIR / f"{symbol_name}_{size}px.svg"
                with open(svg_path, 'wb') as f:
                    f.write(response.content)
                print(f"  ✓ Downloaded SVG: {svg_path.name} (cairosvg not available)")
                return True
        else:
            print(f"  ✗ Failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    print("📥 Downloading Material Icons")
    print("=" * 60)

    # Check if cairosvg is available
    try:
        import cairosvg
        print("✓ cairosvg available - will convert SVG to PNG")
    except ImportError:
        print("⚠ cairosvg not available - will download SVG only")
        print("  Install with: pip install cairosvg")

    print("=" * 60)

    total = len(ICONS) * len(SIZES)
    success = 0

    for friendly_name, symbol_name in ICONS.items():
        print(f"\n{friendly_name} ({symbol_name}):")
        for size in SIZES:
            if download_icon_svg_to_png(symbol_name, size):
                success += 1

    print("\n" + "=" * 60)
    print(f"✓ Downloaded: {success}/{total}")
    print(f"📁 Icons saved to: {ICON_DIR.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
