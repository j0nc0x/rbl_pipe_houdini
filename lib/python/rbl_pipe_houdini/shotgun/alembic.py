#!/usr/bin/env python

"""Class that handles loading Alembics from SG, used by alembicimport LOP."""

import logging
import os

from rbl_pipe_core.util import farm

from rbl_pipe_houdini.shotgun import node


logger = logging.getLogger(__name__)


class ShotgunAlembicNode(node.ShotgunNode):
    """Load Alembics from Shotgun."""

    def __init__(self, current_node):
        """Initialise the class with the given node.

        Args:
            current_node(hou.Node): The Houdini node to initialise the class with.
        """
        self.node_name = None
        super(ShotgunAlembicNode, self).__init__(current_node)
        logger.info(
            "ShotgunAlembicNode intitalised for {current_node}".format(
                current_node=self.current_node,
            )
        )

    def menus_updated(self):
        """Menus updated callback."""
        self.update_path()

        # If the UI is loaded update the node name if required
        if not farm.running_on_farm():
            self.update_node_name()

    def get_template(self):
        """Get the selected template on the current node.

        Returns:
            tank.template.TemplatePath: The SGTK template path for the current
                node.
        """
        template_name = self.selected_template()
        tk = self.sg_load.get_tk()
        if not tk:
            return None

        template = tk.templates.get(template_name)
        return template

    def get_path(self):
        """Get the alembic file path, updating it if possible.

        Returns:
            str: The Alembic file path for the current node.
        """
        if not farm.running_on_farm():
            self.update_path()

        if self.current_node.userData("file_path"):
            logger.info(
                "Using cached alembic path for {current_node}".format(
                    current_node=self.current_node,
                )
            )
            return self.current_node.userData("file_path")

        return ""

    def update_path(self):
        """Generate an Alembic path based on the current settings.

        Returns:
            (str): The currently selected path.

        Raises:
            RuntimeError: The node must either be in asset mode or shot mode.
        """
        if farm.running_on_farm() and self.current_node.userData("file_path"):
            return self.current_node.userData("file_path")

        if self.in_asset_mode():
            data = self.generate_asset_data()
        elif self.in_shot_mode():
            data = self.generate_shot_data()
        else:
            raise RuntimeError("Invalid mode. Must be either asset or shot.")

        if data:
            template = self.get_template()
            missing_keys = template.missing_keys(data)
            if missing_keys:
                raise RuntimeError(
                    "Error: Missing keys:{}\n for template:{}".format(
                        missing_keys, template.name
                    )
                )

            file_path = template.apply_fields(data)

            if file_path:
                abc_name = os.path.basename(file_path)
                # Set the node name and filepath
                self.node_name = os.path.splitext(abc_name)[0]
                self.current_node.setUserData("file_path", file_path)
                logger.info(
                    "{current_node} path updated to {path}.".format(
                        current_node=self.current_node,
                        path=file_path,
                    )
                )
                return

        # Unset the node name and filepath
        self.current_node.setUserData("file_path", "")
        self.node_name = "alembicimport"
        logger.info(
            "Path reset for {current_node}".format(
                current_node=self.current_node,
            )
        )

    def update_node_name(self):
        """Update the node name for the current node."""
        if (
            self.node_name
            and self.node_name != self.current_node.name()
            and self.current_node.evalParm("mode") == 0
        ):
            self.current_node.setName(self.node_name, unique_name=True)

    def generate_asset_data(self):
        """Generate the asset data dictionary.

        This dictionary of data is needed to evaluate against an asset template.

        Returns:
            dict: Containing the key data needed to lookup against a SG
                template.
        """
        asset_type = self.get_menu("asset_type").get_selection()
        asset_id = self.get_menu("asset").get_selection()
        task_id = self.get_menu("task").get_selection()

        if asset_type and asset_id and task_id and self.sg_load.assets:
            step = self.sg_load.step_from_task(int(task_id))
            asset = self.sg_load.asset_name_from_id(int(asset_id))
            variant_name = self.sg_load.variant_name_from_task(int(task_id))
            version = self.get_version()

            if version == "latest":
                version = self.current_version()

            if asset and step and asset_type and variant_name and version:
                return {
                    "Asset": asset,
                    "Step": step,
                    "sg_asset_type": asset_type,
                    "variant_name": variant_name,
                    "version": int(version),
                }

        return {}

    def generate_shot_data(self):
        """Generate the dictionary of data needed to evaluate against an shot template.

        Returns:
            dict: Containing the key data needed to lookup against a SG
                template.
        """
        shot_id = self.get_menu("shot").get_selection()
        step_id = self.get_menu("shot_step").get_selection()
        task_id = self.get_menu("shot_task").get_selection()

        if shot_id and step_id and task_id and self.sg_load.shots:
            sequence_name = self.sg_load.sequence_name_from_shot_id(int(shot_id))
            shot_name = self.sg_load.shot_name_from_id(int(shot_id))
            step_name = self.sg_load.step_name_from_id(
                int(step_id),
                shot_id=int(shot_id),
            )
            variant_name = self.sg_load.variant_name_from_task(int(task_id))
            version = self.get_version()

            if version == "latest":
                version = self.current_version()

            if sequence_name and shot_name and step_name and variant_name and version:
                return {
                    "Sequence": sequence_name,
                    "Shot": shot_name,
                    "Step": step_name,
                    "variant_name": variant_name,
                    "version": int(version),
                }

        return {}

    def is_camera(self):
        """Determine if the node is being used to load a camera.

        Returns:
            (bool): Is the current selection a camera?

        Raises:
            RuntimeError: Node must either be in asset mode or shot mode.
        """
        if self.in_asset_mode():
            asset_id = self.get_menu("asset").get_selection()
            step_id = self.get_menu("step").get_selection()
            step_name = self.sg_load.step_name_from_id(
                int(step_id),
                asset_id=int(asset_id),
            )
        elif self.in_shot_mode():
            shot_id = self.get_menu("shot").get_selection()
            step_id = self.get_menu("shot_step").get_selection()
            step_name = self.sg_load.step_name_from_id(
                int(step_id),
                shot_id=int(shot_id),
            )
        else:
            raise RuntimeError("Invalid mode. Must be either asset or shot.")

        if step_name == "CAM":
            return True

        return False


def get_shotgun_node(current_node):
    """Load the current instance of ShotgunLoad.

    This is looked up from cachedUserData for the node it's being requested from.

    Args:
        current_node(hou.Node): The node to get the ShotgunAlembicNode
            instance for.

    Returns:
        rbl_pipe_houdini.shotgun.alembic.ShotgunAlembicNode: The instance of
            ShotgunAlembicNode for the given Houdini node.
    """
    return ShotgunAlembicNode.get_shotgun_node(current_node)


def initialise(current_node):
    """Create a new instance of ShotgunLoad.

    This store it on cachedUserData for the node it's being requested from.

    Args:
        current_node(hou.Node): The node we want to initalise
            ShotgunAlembicNode for.
    """
    ShotgunAlembicNode.initialise(current_node)
