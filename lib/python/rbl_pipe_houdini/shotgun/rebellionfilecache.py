#!/usr/bin/env python

"""SG based Houdini File Cache."""

import logging
import os
import re

import hou

from rbl_pipe_core.util import farm

from rbl_pipe_houdini.shotgun import node
from rbl_pipe_houdini.shotgun import sgmenu
from rbl_pipe_houdini.utils import dialog


logger = logging.getLogger(__name__)


class RebellionFileCacheNode(node.ShotgunNode):
    """Cache files to working directories."""

    def __init__(self, current_node):
        """Initialise the File Cache for the given node.

        Args:
            current_node(hou.Node): The node we are initialising the File Cache for.
        """
        self.scene_template = None
        self.scene_asset = None
        self.scene_task = None
        self.scene_step = None
        self.scene_shot = None
        self.scene_shot_step = None
        self.scene_shot_task = None
        self.context = None
        self.file_type = None
        self.fields = None

        super(RebellionFileCacheNode, self).__init__(current_node)

        self.name_menu = sgmenu.SGMenu(self, self.current_node.parm("name"))
        self.file_type_menu = sgmenu.SGMenu(self, self.current_node.parm("file_type"))

        # Force a flush of the nodes
        self.update_all_menus(force=True)

        logger.info(
            "RebellionFileCacheNode intitalised for {node}".format(
                node=self.current_node,
            )
        )

    def menus_updated(self):
        """Menus updated callback."""
        self.update_output_path()

    def refresh_context(self):
        """Refresh the context from the current hipfile."""
        sg_template = self.sg_template.template_from_path(
            hou.hipFile.path(),
            templates=self.hip_templates,
        )

        if sg_template:
            asset_templates = ["houdini_asset_work", "houdini_asset_publish"]
            shot_templates = ["houdini_shot_work", "houdini_shot_publish"]

            hip = hou.hipFile.path()

            fields = sg_template.get_fields(hip)

            if sg_template.name in asset_templates:
                self.scene_template = "file_cache_asset"
                self.scene_asset = fields.get("Asset")
                self.scene_task = "{variant}_{step}".format(
                    variant=fields.get("variant_name"),
                    step=fields.get("Step"),
                )
                self.scene_step = fields.get("Step")
            elif sg_template.name in shot_templates:
                self.scene_template = "file_cache_shot"
                self.scene_shot = fields.get("Shot")
                self.scene_shot_step = fields.get("Step")
                self.scene_shot_task = "{variant}_{step}".format(
                    variant=fields.get("variant_name"),
                    step=fields.get("Step"),
                )
            else:
                logger.warning("No template found for {path}".format(path=hip))

    def get_output_version(self):
        """Get the output version.

        Returns:
            (int): The current output version.
        """
        return self.output_version

    def get_output_root(self):
        """Get the output root directory.

        Returns:
            (str): The output root directory path.
        """
        return self.output_root

    def get_output_path(self, frame=-1):
        """Get the output file path.

        Args:
            frame(:obj:`int`, optional): The frame number to use in the path.

        Returns:
            (str): The output file path.
        """
        name = self.get_parm("name")
        file_type = self.get_parm("file_type")

        root = self.current_node.userData("output_root")

        if self.is_sequence():
            path = "{root}/{name}.{frame:0>4}.{file_type}".format(
                root=root,
                name=name,
                frame=frame,
                file_type=file_type,
            )
        else:
            path = "{root}/{name}.{file_type}".format(
                root=root,
                name=name,
                file_type=file_type,
            )
        return path

    def selected_task(self):
        """Get the selected task.

        Returns:
            (str): The task ID from the node.

        Raises:
            RuntimeError: Invalid mode set on the node.
        """
        if self.in_asset_mode():
            return self.get_menu("task").get_selection()
        elif self.in_shot_mode():
            return self.get_menu("shot_task").get_selection()
        else:
            raise RuntimeError("Invalid mode. Must be either asset or shot.")

    def get_parm(self, parm):
        """Get the value for parm on the current node.

        Args:
            parm(str): The parameter name to get on the current node.

        Returns:
            The value retrieved from the parameter.
        """
        return self.current_node.evalParm(parm)

    def set_parm(self, parm, value):
        """Set the value for a parm on the current node.

        Args:
            parm(str): The parameter name to set on the current node.
            value: The value to set onto the parameter on the node.
        """
        self.current_node.setParms({parm: value})

    def update_name(self):
        """Update the node name."""
        name = self.get_parm("name")

        if not name.isalnum():
            pattern = re.compile(r"[\W_]+")
            self.set_parm("name", pattern.sub("", name))
            dialog.display_message(
                "Please choose a name with only alphanumeric characters, {name} is "
                "not valid".format(name=name)
            )
            self.current_node.parm("name").pressButton()

            # Update path now name is alphanumeric
            self.update_output_path(sg=False)
        else:
            self.update_output_path(sg=False)

    def is_sequence(self):
        """Check if we are dealing with a sequence.

        Returns:
            (bool): If the node has a frame sequence configured.
        """
        if self.current_node.evalParm("trange") == 0:
            return False
        else:
            return True

    def create_file_structure(self, tk, task_id):
        """Check if the work area exists on the file system.

        Args:
            tk(sgtk instance): The sgtk instance for the current session.
            task_id(int): The task ID we want to create the file structure for.
        """
        work_area_template = ""

        if self.in_shot_mode():
            work_area_template = tk.templates["shot_work_area_houdini"]
        elif self.in_asset_mode():
            work_area_template = tk.templates["asset_work_area_houdini"]

        fields = self.get_fields()

        # Get path to work directory
        work_path = work_area_template.apply_fields(fields)

        # Create filesystem structure if it doesn't exist
        if not os.path.exists(work_path):
            # Find context for the task
            context = tk.context_from_entity("Task", int(task_id))
            # Create the filesystem structure
            tk.create_filesystem_structure("Task", context.task["id"])

    def get_latest_version(self):
        """Get the latest version of the current file.

        It's a brute force approach, and just checks to see if the directory exists.
        Good enough for now until we get publishing.

        Returns:
            (int): The latest version.
        """
        root = self.get_output_root()
        parent = os.path.dirname(root)

        version = 0

        if os.path.exists(parent):
            folders = os.listdir(parent)
            if folders:
                name = self.get_parm("name")
                file_folders = sorted([x for x in folders if name + "_" in x])
                if file_folders:
                    folder = file_folders[-1].split("_")
                    version = int(re.sub("[^0-9]", "", folder[-1]))

        return version

    def get_fields(self):
        """Get the fields for the shot.

        Returns:
            (dict): The fields dictionary used by SG.
        """
        fields = {}

        if self.in_asset_mode():
            # Get menu values
            asset_id = self.get_menu("asset").get_selection()
            asset_step = self.get_menu("step").get_selection()
            asset_task_id = self.get_menu("task").get_selection()

            # Set values from menu values
            fields["sg_asset_type"] = self.sg_load.asset_type_from_name(
                self.sg_load.asset_name_from_id(int(asset_id))
            )
            fields["Asset"] = self.sg_load.asset_name_from_id(int(asset_id))
            fields["Step"] = self.sg_load.step_name_from_id(
                int(asset_step), asset_id=int(asset_id)
            )
            fields["variant_name"] = self.sg_load.task_name_from_id(int(asset_task_id))
        elif self.in_shot_mode():
            # Get menu values
            shot_id = self.get_menu("shot").get_selection()
            shot_step_id = self.get_menu("shot_step").get_selection()
            shot_task_id = self.get_menu("shot_task").get_selection()

            # Set values from menu items
            fields["Sequence"] = self.sg_load.sequence_name_from_shot_id(int(shot_id))
            fields["Shot"] = self.sg_load.shot_name_from_id(int(shot_id))
            fields["Step"] = self.sg_load.step_name_from_id(
                int(shot_step_id), shot_id=int(shot_id)
            )
            fields["variant_name"] = self.sg_load.task_name_from_id(int(shot_task_id))

        return fields

    def update_output_path(self, sg=True, frame=-1):
        """Update the output file path.

        This should be based on the selected task with the resulting path cached into
        the node.

        Args:
            sg(:obj:`bool`, optional): Should the path be updated from SG.
            frame(:obj:`int`, optional): The frame number to use in the path.

        Returns:
            (None)
        """
        if farm.running_on_farm() and self.current_node.userData("output_root"):
            return self.current_node.userData("output_root")

        # Only run the update on the sg side if we have to
        if sg:

            # Grab the template
            template_name = self.selected_template()

            # Set as sequence if animated template
            if self.is_sequence():
                template_name = "{name}_sequence".format(name=template_name)

            tk = self.sg_load.get_tk()
            if not tk:
                return
            if template_name not in tk.templates:
                if not self.missing_template:
                    msg = (
                        "{template} missing from project template. It looks like file "
                        "caching is not yet supported on this project."
                    ).format(
                        template=template_name,
                    )
                    dialog.display_message(msg)
                    self.missing_template = True
                # Maybe add a node error here
                return
            template = tk.templates[template_name]

            # Set the context
            task_id = self.selected_task()

            if not task_id:
                # maybe add a warning here
                return

            # Check to see if it exists, and create if not
            self.create_file_structure(tk, task_id)

            fields = self.get_fields()

            self.fields = fields
            self.template = template

        fields = self.fields
        template = self.template

        # Set custom fields
        fields["name"] = self.get_parm("name")
        fields["hcache_extension"] = self.get_parm("file_type")
        fields["version"] = self.get_parm("current_version")

        if self.is_sequence():
            fields["SEQ"] = frame

        # Set the version on the node
        self.output_version = str(fields["version"]).zfill(3)

        # Generate the publish path
        self.output_path = template.apply_fields(fields)
        self.output_root = os.path.dirname(self.output_path)
        self.current_node.setUserData("output_root", self.output_root)

        # Update output file
        self.current_node.parm("file").pressButton()
        self.current_node.parm("latest_version").pressButton()

    def get_file_types_menu(self):
        """Define the asset types we're able to write out.

        Returns:
            (list): A list containing the file type menu entries.
        """
        asset_types = ["bgeo", "vdb", "abc"]

        menu = list()

        for ass in asset_types:
            menu.append(ass)
            menu.append(ass)

        return menu

    def get_version_menu(self):
        """Generate the version menu entries.

        Returns:
            (list): A list containing the version menu entries.
        """
        version = self.get_latest_version()
        return [version, version]

    def load_from_scene(self, force, node_parm):
        """Update the information from the scene.

        Args:
            force(bool): Should the load be forced rather than relying on the mode
                parameter value on the node.
            node_parm(str): The name of the parameter we want to set from the scene
                context.

        Returns:
            (str): The value the paramter should be set to.
        """
        # Make sure we have the up to date context from the scene name
        self.refresh_context()

        # Determine if we should be forcing the context to load from the scene
        mode = None
        mode_parm = self.current_node.parm("mode")
        if mode_parm:
            mode = mode_parm.evalAsString()
        force_load = (
            force or mode == "auto" or not self.current_node.evalParm(node_parm)
        )
        if (
            force_load
            and self.scene_template
            and self.scene_asset
            and self.scene_task
            and self.scene_step
        ):
            if node_parm == "template":
                return self.scene_template
            elif node_parm == "asset_type":
                return self.sg_load.asset_type_from_name(self.scene_asset)
            elif node_parm == "asset":
                return self.sg_load.asset_id_from_name(self.scene_asset)
            elif node_parm == "step":
                asset_id = self.sg_load.asset_id_from_name(self.scene_asset)
                return self.sg_load.step_id_from_name(
                    self.scene_step,
                    asset_id=int(asset_id),
                )
            elif node_parm == "task":
                asset_id = self.sg_load.asset_id_from_name(self.scene_asset)
                return self.sg_load.task_id_from_name(
                    self.scene_task,
                    asset_id=int(asset_id),
                )
        elif (
            force_load
            and self.scene_template
            and self.scene_shot
            and self.scene_shot_step
            and self.scene_shot_task
        ):
            if node_parm == "template":
                return self.scene_template
            elif node_parm == "sequence":
                return self.sg_load.sequence_name_from_shot_name(self.scene_shot)
            elif node_parm == "shot":
                return self.sg_load.shot_id_from_name(self.scene_shot)
            elif node_parm == "shot_step":
                shot_id = self.sg_load.shot_id_from_name(self.scene_shot)
                return self.sg_load.step_id_from_name(
                    self.scene_shot_step,
                    shot_id=int(shot_id),
                )
            elif node_parm == "shot_task":
                shot_id = self.sg_load.shot_id_from_name(self.scene_shot)
                return self.sg_load.task_id_from_name(
                    self.scene_shot_task,
                    shot_id=int(shot_id),
                )


def get_shotgun_node(current_node):
    """
    Load the current instance of RebellionFileCacheNode.

    This is looked up from cachedUserData for the node it's being requested from.

    Args:
        current_node(hou.Node): The node to get the SG class instance for.

    Returns:
        (RebellionFileCacheNode): The class instance for the given node.
    """
    return RebellionFileCacheNode.get_shotgun_node(current_node)


def initialise(current_node):
    """Create a new instance of RebellionFileCacheNode.

    This is created and then stored on the cachedUserData for the node it's being
    requested from.

    Args:
        current_node(hou.Node): The node to initialise the SG class for.
    """
    RebellionFileCacheNode.initialise(current_node)
