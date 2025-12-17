#!/usr/bin/env python3
"""
Script to compose 6 images into a 2x3 grid comparison for all parts.

Layout:
        T0      T1      T2
partfield [img] [img] [img]
ours      [img] [img] [img]

T0 = default
T1 = finer
T2 = coarser
"""

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def find_image_for_part(part_id: str, directory: Path) -> Path | None:
    """Find the first image file in directory that starts with part_id."""
    if not directory.exists():
        return None
    
    for file in directory.iterdir():
        if file.is_file() and file.name.startswith(part_id):
            return file
    
    return None


def get_all_part_ids(base_dir: Path) -> set[str]:
    """Extract all unique part IDs from the rendered images."""
    part_ids = set()
    
    # Check all directories to get comprehensive list of part IDs
    for method_dir in ["ours", "partfield"]:
        method_path = base_dir / method_dir
        if not method_path.exists():
            continue
        
        for tesselation_dir in method_path.iterdir():
            if not tesselation_dir.is_dir():
                continue
            
            for img_file in tesselation_dir.iterdir():
                if img_file.is_file() and img_file.suffix == ".png":
                    # Extract part ID (first part before underscore)
                    part_id = img_file.name.split("_")[0]
                    part_ids.add(part_id)
    
    return part_ids


def add_soft_shadow(img: Image.Image, shadow_size: int = 15, shadow_opacity: int = 20) -> Image.Image:
    """Add a soft shadow around the image to create smooth blending."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    # Create a larger canvas with padding for shadow
    shadow_padding = shadow_size
    new_width = img.width + shadow_padding * 2
    new_height = img.height + shadow_padding * 2
    
    # Create shadow with smooth gradient
    shadow = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    
    # Create a smooth gradient shadow by drawing multiple overlapping shapes
    # Use a more gradual falloff for smoother appearance
    steps = shadow_size * 2
    for i in range(steps):
        progress = i / steps
        # Use a smoother curve (ease-out)
        alpha = int(shadow_opacity * (1 - progress) ** 2)
        if alpha > 0:
            offset = int(shadow_size * progress)
            bbox = [
                shadow_padding - shadow_size + offset,
                shadow_padding - shadow_size + offset,
                new_width - shadow_padding + shadow_size - offset,
                new_height - shadow_padding + shadow_size - offset,
            ]
            # Use rounded rectangle for smoother corners
            draw.rounded_rectangle(bbox, radius=5, fill=(0, 0, 0, alpha))
    
    # Paste original image on top of shadow
    shadow.paste(img, (shadow_padding, shadow_padding), img)
    return shadow


def compose_comparison(part_id: str, base_dir: Path, output_base_dir: Path) -> bool:
    """
    Compose 6 images for a given part into a 2x3 grid with smooth blending and labels.
    
    Args:
        part_id: The part ID to find images for (e.g., "00006682")
        base_dir: Base directory for input images
        output_base_dir: Base directory for output images
    
    Returns:
        True if successful, False if any images are missing
    """
    # Define the 6 image paths
    image_paths = {
        "partfield_T0": base_dir / "partfield" / "default_partfield240",
        "partfield_T1": base_dir / "partfield" / "finer_partfield240",
        "partfield_T2": base_dir / "partfield" / "coarser_partfield240",
        "ours_T0": base_dir / "ours" / "default_meshes240",
        "ours_T1": base_dir / "ours" / "finer_meshes240",
        "ours_T2": base_dir / "ours" / "coarser_meshes240",
    }
    
    # Find all images and convert to RGBA to preserve alpha channel
    images = {}
    for key, directory in image_paths.items():
        img_path = find_image_for_part(part_id, directory)
        if img_path is None:
            return False
        img = Image.open(img_path)
        # Convert to RGBA to preserve alpha channel
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        images[key] = img
    
    # Get dimensions (assume all images have the same size)
    img_width, img_height = images["partfield_T0"].size
    
    # Add soft shadows to images for smooth blending
    shadow_size = 15
    shadow_padding = shadow_size
    images_with_shadow = {}
    for key, img in images.items():
        images_with_shadow[key] = add_soft_shadow(img, shadow_size=shadow_size, shadow_opacity=25)
    
    # Calculate spacing and dimensions
    cell_padding = 30  # Padding between cells
    label_height = 60  # Height for row labels
    label_width = 120  # Width for column labels
    
    # Calculate composite dimensions
    cell_width = img_width + shadow_padding * 2
    cell_height = img_height + shadow_padding * 2
    composite_width = label_width + cell_width * 3 + cell_padding * 2
    composite_height = label_height + cell_height * 2 + cell_padding * 1
    
    # Create the composite image with white background
    composite = Image.new("RGBA", (composite_width, composite_height), color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(composite)
    
    # Try to load a nice font, fallback to default if not available
    try:
        # Try to use a system font
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
            font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        except:
            # Fallback to default font
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # Column labels (T0, T1, T2 with descriptions)
    column_labels = [
        ("T0", "default"),
        ("T1", "finer"),
        ("T2", "coarser"),
    ]
    
    base_x = label_width
    base_y = 0
    
    for col_idx, (label, desc) in enumerate(column_labels):
        x = base_x + col_idx * (cell_width + cell_padding) + cell_width // 2
        y = label_height // 2
        
        # Draw main label (T0, T1, T2)
        bbox = draw.textbbox((0, 0), label, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            (x - text_width // 2, y - text_height - 5),
            label,
            fill=(0, 0, 0, 255),
            font=font_large,
        )
        
        # Draw description
        bbox = draw.textbbox((0, 0), desc, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (x - text_width // 2, y + 5),
            desc,
            fill=(100, 100, 100, 255),
            font=font_small,
        )
    
    # Row labels and arrange images in grid
    row_labels = ["partfield", "ours"]
    layout = [
        ["partfield_T0", "partfield_T1", "partfield_T2"],  # Top row
        ["ours_T0", "ours_T1", "ours_T2"],                  # Bottom row
    ]
    
    for row_idx, (row_label, row_keys) in enumerate(zip(row_labels, layout)):
        # Draw row label
        y = label_height + row_idx * (cell_height + cell_padding) + cell_height // 2
        bbox = draw.textbbox((0, 0), row_label, font=font_medium)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            (label_width // 2 - text_width // 2, y - text_height // 2),
            row_label,
            fill=(0, 0, 0, 255),
            font=font_medium,
        )
        
        # Paste images with shadows
        for col_idx, key in enumerate(row_keys):
            x = base_x + col_idx * (cell_width + cell_padding)
            y = label_height + row_idx * (cell_height + cell_padding)
            # Paste with alpha channel preserved for smooth blending
            composite.paste(images_with_shadow[key], (x, y), images_with_shadow[key])
    
    # Convert back to RGB for saving (alpha will be composited onto white)
    composite = composite.convert("RGB")
    
    # Save the composite in the comparisons directory
    output_path = output_base_dir / "comparisons" / f"{part_id}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    composite.save(output_path)
    
    return True


def main():
    """Main function to process all parts."""
    parser = argparse.ArgumentParser(
        description="Compose 6 images into a 2x3 grid comparison for all parts"
    )
    parser.add_argument(
        "--part-id",
        type=str,
        default=None,
        help="Optional: Process only a specific part ID (e.g., '00006682')"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="/home/kidziak/Documents/github/blender_studio/data/rendered",
        help="Input directory containing rendered images"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/home/kidziak/Documents/github/blender_studio/outputs/tesselation",
        help="Output directory for composite images"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.input_dir)
    output_base_dir = Path(args.output_dir)
    
    if args.part_id:
        # Process single part
        part_ids = [args.part_id]
    else:
        # Get all part IDs
        print("Collecting all part IDs...")
        part_ids = sorted(get_all_part_ids(base_dir))
        print(f"Found {len(part_ids)} unique part IDs")
    
    # Process each part
    successful = 0
    failed = 0
    
    for i, part_id in enumerate(part_ids, 1):
        if compose_comparison(part_id, base_dir, output_base_dir):
            successful += 1
            if i % 10 == 0 or i == len(part_ids):
                print(f"Processed {i}/{len(part_ids)}: {part_id} ✓")
        else:
            failed += 1
            print(f"Processed {i}/{len(part_ids)}: {part_id} ✗ (missing images)")
    
    print(f"\nCompleted: {successful} successful, {failed} failed")


if __name__ == "__main__":
    main()
