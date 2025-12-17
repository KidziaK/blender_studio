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
            print(f"Warning: Directory {method_path} does not exist")
            continue
        
        for tesselation_dir in method_path.iterdir():
            if not tesselation_dir.is_dir() or tesselation_dir.name.startswith('.'):
                continue
            
            png_count = 0
            for img_file in tesselation_dir.iterdir():
                if img_file.is_file() and img_file.suffix == ".png":
                    png_count += 1
                    # Extract part ID (first part before underscore)
                    part_id = img_file.name.split("_")[0]
                    part_ids.add(part_id)
            
            if png_count == 0:
                print(f"Warning: No PNG files found in {tesselation_dir}")
    
    return part_ids


def blur_edges(img: Image.Image, blur_size: int = 20) -> Image.Image:
    """Blur the edges of an image by applying a gradient alpha mask."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    width, height = img.size
    img_array = img.load()
    
    # Create a new image with the same size
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    result_array = result.load()
    
    for y in range(height):
        for x in range(width):
            # Calculate distance from edges
            dist_left = x
            dist_right = width - 1 - x
            dist_top = y
            dist_bottom = height - 1 - y
            
            # Find minimum distance to any edge
            min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
            
            # Calculate alpha based on distance from edge
            if min_dist < blur_size:
                # Smooth fade-out using a quadratic curve
                alpha_factor = (min_dist / blur_size) ** 2
                r, g, b, a = img_array[x, y]
                new_alpha = int(a * alpha_factor)
                result_array[x, y] = (r, g, b, new_alpha)
            else:
                # Keep original pixel
                result_array[x, y] = img_array[x, y]
    
    return result


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
    
    # Apply edge blurring to images with greater blur
    images_to_use = {}
    for key, img in images.items():
        images_to_use[key] = blur_edges(img, blur_size=150)
    
    # Calculate spacing and dimensions with 15% overlap
    label_width = 100  # Width for row labels on the left (increased for larger fonts)
    label_overlay = 20  # How much labels can overlay image borders
    left_padding = 20  # Extra padding from left edge
    
    # Calculate overlap amounts (15% of image dimensions)
    horizontal_overlap = int(img_width * 0.15)
    vertical_overlap = int(img_height * 0.15)
    
    # Calculate composite dimensions accounting for overlaps
    # For 3 columns: first image full width, next 2 overlap by 15% each
    total_width = img_width + (img_width - horizontal_overlap) * 2
    # For 2 rows: first image full height, second overlaps by 15%
    total_height = img_height + (img_height - vertical_overlap)
    
    composite_width = left_padding + label_width + total_width
    composite_height = total_height
    
    # Create the composite image with white background
    composite = Image.new("RGBA", (composite_width, composite_height), color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(composite)
    
    # Try to load a nice font, fallback to default if not available
    try:
        # Try to use a system font
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 64)
            font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
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
    
    base_x = left_padding + label_width
    
    # Draw column labels directly on top of images (after images are pasted)
    # We'll do this after pasting images
    
    # Row labels and arrange images in grid
    row_labels = ["partfield", "ours"]
    layout = [
        ["partfield_T0", "partfield_T1", "partfield_T2"],  # Top row
        ["ours_T0", "ours_T1", "ours_T2"],                  # Bottom row
    ]
    
    for row_idx, (row_label, row_keys) in enumerate(zip(row_labels, layout)):
        # Paste images with overlaps
        for col_idx, key in enumerate(row_keys):
            # Horizontal positioning: each image overlaps previous by 15%
            if col_idx == 0:
                x = base_x
            else:
                x = base_x + col_idx * (img_width - horizontal_overlap)
            
            # Vertical positioning: second row overlaps first by 15%
            if row_idx == 0:
                y = 0
            else:
                y = img_height - vertical_overlap
            
            # Paste with alpha channel preserved
            composite.paste(images_to_use[key], (x, y), images_to_use[key])
        
        # Draw row label - overlay on left border of images
        if row_idx == 0:
            y = img_height // 2
        else:
            y = img_height - vertical_overlap + (img_height - vertical_overlap) // 2
        
        bbox = draw.textbbox((0, 0), row_label, font=font_medium)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            (left_padding + label_width - label_overlay - text_width // 2, y - text_height // 2),
            row_label,
            fill=(0, 0, 0, 255),
            font=font_medium,
        )
    
    # Draw column labels directly on top of images
    for col_idx, (label, desc) in enumerate(column_labels):
        # Calculate x position accounting for overlaps
        if col_idx == 0:
            x = base_x + img_width // 2
        else:
            x = base_x + col_idx * (img_width - horizontal_overlap) + img_width // 2
        
        y = label_overlay  # Position at top of images with small offset
        
        # Draw main label (T0, T1, T2) - overlay on top of images
        bbox = draw.textbbox((0, 0), label, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            (x - text_width // 2, y),
            label,
            fill=(0, 0, 0, 255),
            font=font_large,
        )
        
        # Draw description - just below main label
        bbox = draw.textbbox((0, 0), desc, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (x - text_width // 2, y + text_height + 5),
            desc,
            fill=(100, 100, 100, 255),
            font=font_small,
        )
    
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
        default=None,
        help="Input directory containing rendered images (default: project_root/data/rendered)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for composite images (default: project_root/outputs/tesselation)"
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    if args.input_dir:
        base_dir = Path(args.input_dir)
    else:
        base_dir = script_dir / "data" / "rendered"
    
    if args.output_dir:
        output_base_dir = Path(args.output_dir)
    else:
        output_base_dir = script_dir / "outputs" / "tesselation"
    
    if not base_dir.exists():
        print(f"Error: Input directory does not exist: {base_dir}")
        return
    
    if args.part_id:
        # Process single part
        part_ids = [args.part_id]
    else:
        # Get all part IDs
        print(f"Collecting all part IDs from {base_dir}...")
        part_ids = sorted(get_all_part_ids(base_dir))
        print(f"Found {len(part_ids)} unique part IDs")
        if len(part_ids) == 0:
            print(f"Warning: No part IDs found. Check that {base_dir} contains 'ours' and 'partfield' subdirectories with images.")
            return
    
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
