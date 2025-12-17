#!/usr/bin/env python3
"""
Script to render 6 images (like compose/partfield) for a single part,
with 180 frames from 0 to 359 (step 2) for animation.

Renders:
- ours: coarser, default, finer
- partfield: coarser, default, finer
"""

from pathlib import Path
import sys
import argparse
import bpy

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from studio.renderer_context import RenderContext, Material


class AnimatedRenderContext(RenderContext):
    """Custom render context that handles frame-based filenames for animation."""
    
    def render(self, output_dir=None, frame: int = 0, wireframe: bool = False, focal_length=None, part_id: str = None) -> bool:
        """Override render to use frame-based filenames."""
        if output_dir is None:
            output_dir = self.output_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create frame-based filename
        if part_id:
            output_filename = f"{frame:03d}_{part_id}.png"
        else:
            output_filename = f"{frame:03d}_{self.mesh_stem}.png"
        output_path = output_dir / output_filename
        
        # Handle wireframe (from parent class)
        wireframe_obj = None
        if wireframe and self.current_mesh:
            bpy.context.view_layer.objects.active = self.current_mesh
            bpy.ops.object.select_all(action='DESELECT')
            self.current_mesh.select_set(True)
            bpy.ops.object.duplicate()
            wireframe_obj = bpy.context.view_layer.objects.active
            wireframe_obj.name = f"{self.current_mesh.name}_wireframe"
            
            wireframe_modifier = wireframe_obj.modifiers.new(name="Wireframe", type='WIREFRAME')
            wireframe_modifier.thickness = 0.01
            wireframe_modifier.use_even_offset = False
            wireframe_modifier.use_relative_offset = True
            wireframe_modifier.use_replace = True
            
            black_mat = bpy.data.materials.get(Material.BLACK.value)
            if black_mat:
                wireframe_mat = black_mat.copy()
                wireframe_mat.name = "wireframe_black"
            else:
                wireframe_mat = bpy.data.materials.new(name="wireframe_black")
                wireframe_mat.use_nodes = True
                
                nodes = wireframe_mat.node_tree.nodes
                links = wireframe_mat.node_tree.links
                
                for node in nodes:
                    nodes.remove(node)
                
                bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                output = nodes.new(type='ShaderNodeOutputMaterial')
                links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
            
            wireframe_obj.data.materials.clear()
            wireframe_obj.data.materials.append(wireframe_mat)
            
            wireframe_obj.parent = self.current_mesh.parent
            wireframe_obj.parent_type = self.current_mesh.parent_type
            wireframe_obj.location = (0, 0, 0)
            wireframe_obj.rotation_euler = (0, 0, 0)
            wireframe_obj.scale = (1, 1, 1)
        
        if focal_length is not None:
            self.set_focal_length(focal_length)
        
        self.scene.camera = self.camera
        self.scene.render.filepath = str(output_path)
        self.scene.render.image_settings.file_format = 'PNG'
        self.scene.render.film_transparent = True
        self.scene.frame_set(frame)
        
        bpy.ops.render.render(write_still=True)
        
        if wireframe_obj:
            wireframe_mat = wireframe_obj.data.materials[0] if wireframe_obj.data.materials else None
            bpy.data.objects.remove(wireframe_obj, do_unlink=True)
            if wireframe_mat and wireframe_mat.name == "wireframe_black":
                bpy.data.materials.remove(wireframe_mat)
        
        return True


def find_mesh_for_part(part_id: str, processed_dir: Path, variant_name: str, folder_name: str) -> Path | None:
    """Find mesh file for a given part ID, variant, and folder."""
    variant_dir = processed_dir / variant_name / folder_name
    if not variant_dir.exists():
        return None
    
    mesh_extensions = {'.ply', '.obj'}
    for ext in mesh_extensions:
        # Try exact match first
        mesh_path = variant_dir / f"{part_id}{ext}"
        if mesh_path.exists():
            return mesh_path
        
        # Try files starting with part_id
        for mesh_file in variant_dir.glob(f"{part_id}*{ext}"):
            return mesh_file
    
    return None


def render_animated_part(part_id: str, processed_dir: Path, output_base_dir: Path, blend_file: Path):
    """
    Render 6 images for a single part across 180 frames (0-359, step 2).
    
    Args:
        part_id: The part ID to render (e.g., "00006682")
        processed_dir: Directory containing processed mesh files
        output_base_dir: Base output directory (will create animated subfolder)
        blend_file: Path to the Blender blend file
    """
    if not blend_file.exists():
        print(f"Error: Blend file not found at {blend_file}")
        return False
    
    if not processed_dir.exists():
        print(f"Error: Processed directory not found at {processed_dir}")
        return False
    
    # Define the 6 render configurations
    render_configs = [
        ("ours", "coarser_meshes240", "ours_coarser"),
        ("ours", "default_meshes240", "ours_default"),
        ("ours", "finer_meshes240", "ours_finer"),
        ("partfield", "coarser_partfield240", "partfield_coarser"),
        ("partfield", "default_partfield240", "partfield_default"),
        ("partfield", "finer_partfield240", "partfield_finer"),
    ]
    
    # Create output directory structure
    animated_dir = output_base_dir / "animated" / part_id
    animated_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize render context
    context = AnimatedRenderContext(blend_file, animated_dir)
    context.set_focal_length(90.0)
    
    # Frames: 0, 2, 4, ..., 358 (180 frames total)
    frames = list(range(0, 360, 2))
    
    print(f"\nRendering part {part_id} with {len(frames)} frames per variant...")
    
    # Render each of the 6 variants
    for variant_name, folder_name, output_name in render_configs:
        mesh_path = find_mesh_for_part(part_id, processed_dir, variant_name, folder_name)
        
        if mesh_path is None:
            print(f"  Warning: Mesh not found for {variant_name}/{folder_name}")
            continue
        
        print(f"  Rendering {output_name}...")
        
        # Import mesh
        if not context.import_mesh(mesh_path, Material.SEMANTIC):
            print(f"    Warning: Failed to import {mesh_path}")
            continue
        
        # Render all frames for this variant
        variant_output_dir = animated_dir / output_name
        variant_output_dir.mkdir(parents=True, exist_ok=True)
        
        for frame_idx, frame in enumerate(frames, 1):
            # Check if already rendered
            output_filename = f"{frame:03d}_{part_id}.png"
            output_path = variant_output_dir / output_filename
            
            if output_path.exists():
                if frame_idx % 20 == 0:
                    print(f"    Frame {frame_idx}/{len(frames)}: {frame}° (skipped)")
                continue
            
            # Render with wireframe (like partfield_comparison.py)
            context.render(output_dir=variant_output_dir, wireframe=True, frame=frame, part_id=part_id)
            
            if frame_idx % 20 == 0 or frame_idx == len(frames):
                print(f"    Frame {frame_idx}/{len(frames)}: {frame}°")
        
        # Remove mesh before loading next one
        context.remove_current_mesh()
    
    print(f"\nCompleted rendering for part {part_id}!")
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Render 6 images for a single part with 180 animation frames (0-359, step 2)"
    )
    parser.add_argument(
        "part_id",
        type=str,
        help="Part ID to render (e.g., '00006682')"
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default=None,
        help="Directory containing processed mesh files (default: project_root/data/processed)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Base output directory (default: project_root/outputs)"
    )
    parser.add_argument(
        "--blend-file",
        type=str,
        default=None,
        help="Path to Blender blend file (default: project_root/studio/photo_studio.blend)"
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    
    if args.processed_dir:
        processed_dir = Path(args.processed_dir)
    else:
        processed_dir = script_dir / "data" / "processed"
    
    if args.output_dir:
        output_base_dir = Path(args.output_dir)
    else:
        output_base_dir = script_dir / "outputs"
    
    if args.blend_file:
        blend_file = Path(args.blend_file)
    else:
        blend_file = script_dir / "studio" / "photo_studio.blend"
    
    render_animated_part(args.part_id, processed_dir, output_base_dir, blend_file)


if __name__ == "__main__":
    main()

