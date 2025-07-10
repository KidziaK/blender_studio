# Blender Studio

Utility tools for rendering single objects in a photo studio like environment.
---

## Installation

```bash
pip install open3d
pip install bpy
```

---

## Usage

1.  **Initialization**:
    -   Create an instance of `RenderContext` by providing paths to your `.blend` file and the desired output directory.

    ```python
    from pathlib import Path
    from your_script_name import RenderContext, Material

    script_dir = Path(__file__).parent
    blend_file = script_dir / "photo_studio.blend"
    output_dir = script_dir / "outputs"

    context = RenderContext(blend_file, output_dir)
    ```

2.  **Import a Mesh**:
    -   Use the `import_mesh` method to load a mesh and apply an initial material.

    ```python
    mock_mesh_path = script_dir / "examples/gt_rescaled.ply"
    context.import_mesh(mock_mesh_path, Material.PEARL_RED)
    ```

3.  **Render the Mesh**:
    -   Call the `render` method. You can optionally specify a frame number, which will be part of the output filename.

    ```python
    context.render(frame=0)
    # Output: outputs/000_gt_rescaled_pearl-red.png
    ```

4.  **Render a Point Cloud**:
    -   Use the `render_point_cloud` method to generate and render a point cloud from the currently loaded mesh.

    ```python
    context.render_point_cloud(frame=1)
    # Output: outputs/001_gt_rescaled_pointcloud.png
    ```

5.  **Change Material and Re-render**:
    -   You can easily switch materials and render again.

    ```python
    context.change_material(Material.PEARL_GREY)
    context.render(frame=90)
    # Output: outputs/090_gt_rescaled_pearl-grey.png
    ```

6.  **Cleanup**:
    -   When you're finished with a mesh, you can remove it from the scene.

    ```python
    context.remove_current_mesh()
    ```

---

## Customization

-   **Adding Materials**: To add new materials, first create them in your `.blend` file. Then, add a corresponding entry to the `Material` enum in the script.
-   **Point Cloud Density**: You can change the number of points in the generated point cloud by modifying the `number_of_points` parameter in the `render_point_cloud` method.

