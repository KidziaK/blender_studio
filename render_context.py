import bpy

from pathlib import Path
from typing import Optional, Tuple
from enum import Enum

import open3d as o3d


Object = bpy.types.Object
Scene = bpy.types.Scene
BlendMaterial = bpy.types.Material
NodeTree = bpy.types.NodeTree
Node = bpy.types.Node
NodeLink = bpy.types.NodeLink
NodeSocket = bpy.types.NodeSocket


class Material(Enum):
    PEARL_RED = "pearl-red"
    PEARL_GREY = "pearl-grey"
    CURVATURE = "curvature"


class RenderContext:
    def __init__(self, blend_path_str: Path, output_dir_str: Path):
        self.current_mesh: Optional[Object] = None
        self.scene: Optional[Scene] = None
        self.target_empty: Optional[Object] = None
        self.camera: Optional[Object] = None
        self.mesh_stem: Optional[str] = None
        self.current_material: Optional[Material] = None
        self.mesh_path: Optional[Path] = None

        self.blend_file_path: Path = Path(blend_path_str)
        self.output_dir: Path = Path(output_dir_str)

        bpy.ops.wm.open_mainfile(filepath=str(self.blend_file_path))

        self.scene = bpy.context.scene
        self.scene.use_nodes = True

        self.target_empty = bpy.data.objects.get("light_target")
        self.camera = bpy.data.objects.get("main-camera")

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def import_mesh(self, mesh_path_str: Path, material: Material) -> bool:
        self.mesh_path = Path(mesh_path_str)
        self.mesh_stem = self.mesh_path.stem

        bpy.ops.object.select_all(action='DESELECT')

        extension = self.mesh_path.suffix.lower()

        match extension:
            case '.ply': bpy.ops.wm.ply_import(filepath=str(self.mesh_path))
            case '.obj': bpy.ops.wm.obj_import(filepath=str(self.mesh_path), forward_axis='-Z', up_axis='Y')
            case _: return False

        self.current_mesh = bpy.context.view_layer.objects.active

        self.current_mesh.parent = self.target_empty
        self.current_mesh.location = (0, 0, 0)
        self.current_mesh.rotation_euler = (0, 0, 0)
        self.current_mesh.scale = (1, 1, 1)

        return self.change_material(material)

    def change_material(self, material: Material) -> bool:
        mat: Optional[BlendMaterial] = bpy.data.materials.get(material.value)

        self.current_mesh.data.materials.clear()
        self.current_mesh.data.materials.append(mat)
        self.current_material = material

        return True

    def remove_current_mesh(self) -> None:
        bpy.data.objects.remove(self.current_mesh, do_unlink=True)
        self.current_mesh = None

    def render(self, frame: int = 0) -> bool:
        output_filename = f"{frame:03d}_{self.mesh_stem}_{self.current_material.value}.png"
        output_path = self.output_dir / output_filename

        self.scene.camera = self.camera
        self.scene.render.filepath = str(output_path)
        self.scene.render.image_settings.file_format = 'PNG'
        self.scene.render.film_transparent = True
        self.scene.frame_set(frame)

        bpy.ops.render.render(write_still=True)

        return True

    def render_point_cloud(self, frame: int = 0) -> bool:
        mesh = o3d.io.read_triangle_mesh(str(self.mesh_path))
        pcd = mesh.sample_points_poisson_disk(number_of_points=10000)

        temp_dir = self.output_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        pc_path = temp_dir / f"{self.mesh_stem}_temp_pc.ply"

        o3d.io.write_point_cloud(str(pc_path), pcd)

        bpy.ops.wm.ply_import(filepath=str(pc_path))
        point_cloud_obj = bpy.context.view_layer.objects.active
        point_cloud_obj.parent = self.target_empty
        point_cloud_obj.location = (0, 0, 0)

        node_group_name = "point-cloud-generate"
        node_group = bpy.data.node_groups.get(node_group_name)

        modifier = point_cloud_obj.modifiers.new(name="GenPoints", type='NODES')
        modifier.node_group = node_group

        original_link = self._setup_glare_compositor()
        try:
            self.current_mesh.hide_render = True
            output_filename = f"{frame:03d}_{self.mesh_stem}_pointcloud.png"
            output_path = self.output_dir / output_filename
            self.scene.render.filepath = str(output_path)

            bpy.ops.render.render(write_still=True)
        finally:
            self.current_mesh.hide_render = False
            if original_link:
                self._restore_compositor(original_link)

            bpy.data.objects.remove(point_cloud_obj, do_unlink=True)
            try:
                pc_path.unlink()
                temp_dir.rmdir()
            except OSError as e:
                print(f"Error during file cleanup: {e}")

        return True

    def _setup_glare_compositor(self) -> Optional[Tuple[NodeSocket, NodeSocket]]:
        tree: NodeTree = self.scene.node_tree
        links: list[NodeLink] = tree.links

        composite = next((n for n in tree.nodes if n.type == 'COMPOSITE'), None)
        glare = next((n for n in tree.nodes if n.type == 'GLARE'), None)

        original_link = next((link for link in links if link.to_node == composite), None)

        link_data = (original_link.from_socket, original_link.to_socket)

        links.remove(original_link)

        links.new(glare.outputs['Image'], composite.inputs['Image'])

        return link_data

    def _restore_compositor(self, link_data: Tuple[NodeSocket, NodeSocket]) -> None:
        tree: NodeTree = self.scene.node_tree
        links: list[NodeLink] = tree.links
        from_socket, to_socket = link_data
        links.new(from_socket, to_socket)


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    mock_mesh_path = script_dir / "examples/gt_rescaled.ply"
    blend_file = script_dir / "photo_studio.blend"
    output_dir = script_dir / "outputs"

    context = RenderContext(blend_file, output_dir)
    context.import_mesh(mock_mesh_path, Material.PEARL_RED)

    context.render(frame=0)

    context.render_point_cloud(frame=1)

    context.change_material(Material.PEARL_GREY)
    context.render(frame=90)

    context.remove_current_mesh()
