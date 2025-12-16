# Blender Studio

Utility tools for rendering single objects in a photo studio like environment.

## Installation

Install the package:

```bash
uv pip install -e .
```

## Usage

Create script in `/run` that use `RenderContext` from `studio.renderer_context`:

```python
from studio.renderer_context import RenderContext, Material

context = RenderContext(blend_file, output_dir)
context.import_mesh(mesh_path, Material.SEMANTIC)
context.render(frame=0)
```
