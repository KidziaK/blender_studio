from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from studio.renderer_context import RenderContext, Material

def main():
    processed_dir = project_root / "data" / "processed"
    rendered_dir = project_root / "data" / "rendered"
    blend_file = project_root / "studio" / "photo_studio.blend"
    
    if not blend_file.exists():
        print(f"Error: Blend file not found at {blend_file}")
        sys.exit(1)
    
    if not processed_dir.exists():
        print(f"Error: Processed directory not found at {processed_dir}")
        sys.exit(1)
    
    context = RenderContext(blend_file, rendered_dir)
    context.set_focal_length(90.0)
    
    mesh_extensions = {'.ply', '.obj'}
    mesh_files = []
    
    for ext in mesh_extensions:
        mesh_files.extend(processed_dir.rglob(f"*{ext}"))
    
    if not mesh_files:
        print(f"No mesh files found in {processed_dir}")
        sys.exit(1)
    
    mesh_groups = {}
    for mesh_path in mesh_files:
        filename = mesh_path.stem
        if filename not in mesh_groups:
            mesh_groups[filename] = []
        mesh_groups[filename].append(mesh_path)
    
    render_order = [
        ("ours", "coarser_meshes240"),
        ("ours", "default_meshes240"),
        ("ours", "finer_meshes240"),
        ("partfield", "coarser_partfield240"),
        ("partfield", "default_partfield240"),
        ("partfield", "finer_partfield240"),
    ]
    
    total_parts = len(mesh_groups)
    part_num = 0
    
    for filename, paths in sorted(mesh_groups.items()):
        part_num += 1
        print(f"\n[Part {part_num}/{total_parts}] Processing {filename}")
        
        for variant_name, folder_name in render_order:
            matching_paths = [p for p in paths if variant_name in str(p) and folder_name in str(p)]
            
            for mesh_path in matching_paths:
                relative_path = mesh_path.relative_to(processed_dir)
                output_dir = rendered_dir / relative_path.parent
                output_file = output_dir / f"{mesh_path.stem}.png"
                
                if output_file.exists():
                    print(f"  Skipping {relative_path} (output already exists)")
                    continue
                
                print(f"  Rendering {relative_path}")
                
                if not context.import_mesh(mesh_path, Material.SEMANTIC):
                    print(f"    Warning: Failed to import {mesh_path}")
                    continue
                
                context.render(output_dir=output_dir, wireframe=True, frame=45)
                context.remove_current_mesh()
    
    print("\nRendering complete!")

if __name__ == "__main__":
    main()

