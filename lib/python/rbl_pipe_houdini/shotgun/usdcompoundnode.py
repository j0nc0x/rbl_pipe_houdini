#!/usr/bin/env python

"""Compound Publish Module."""

import logging
import os

import hou

from rbl_pipe_core.util import filesystem

from rbl_pipe_houdini.shotgun import usdpublishnode
from rbl_pipe_houdini.utils import nodes
from rbl_pipe_houdini.utils import solaris

from rbl_pipe_sg import publish
from rbl_pipe_sg.template import SgtkTemplateNotFoundException


logger = logging.getLogger(__name__)


class USDCompoundPublish(usdpublishnode.ShotgunUSDPublishNode):
    """Publish USD and Compound files to SG."""

    validator_ui = None

    def __init__(self, current_node):
        """
        Initialise the class for the given node.

        Args:
            current_node(hou.Node): The houdini node to initialise the class with.
        """
        self.output_hip_path = None
        self.output_alembic_path = None

        super(USDCompoundPublish, self).__init__(current_node)

        logger.info(
            "{node_class} intitalised for {node}".format(
                node_class=type(self).__name__,
                node=self.current_node,
            )
        )

    def get_all_templates(self, base_template):
        """
        Get a list of all the templates based on the selected base template.

        Args:
            base_template(str): The base (usd) template to lookup against.

        Returns:
            (dict): A dictionary containing all of the templates relating to the given
                base_template.
        """
        all_templates = []

        if self.in_asset_mode():
            all_templates = self.all_asset_templates
        elif self.in_shot_mode():
            all_templates = self.all_shot_templates
        else:
            logger.warning("Should be in either asset or shot mode.")

        selected_templates = [
            templates
            for templates in all_templates
            if templates.get("usd") == base_template
        ]

        if selected_templates:
            return selected_templates[0]
        else:
            return {}

    def get_output_hip_path(self):
        """
        Return the output hip path.

        Returns:
            self.output_hip_path(str): The path to save the published Hip file to.
        """
        return self.output_hip_path

    def get_output_alembic_path(self):
        """
        Return the output alembic path.

        Returns:
            self.output_alembic_path(str): The path to save Alembic file to.
        """
        return self.output_alembic_path

    def get_output_usd_compound_path(self, compound):
        """
        Look-up the correct compound path for the given compound file.

        Args:
            compound(str): The name of the compound file.

        Returns:
            (str): The full path to where the given compound shoud be written.
        """
        path = self.get_output_root()
        return os.path.join(path, "compound", compound)

    def update_output_path(self):
        """Update the output file paths based on the selected task."""
        if self.missing_template:
            logger.debug("Skipping evaluation for missing template.")
            return

        # Grab the template.
        template_name = self.selected_template()
        all_templates = self.get_all_templates(template_name)
        if not all_templates:
            logger.warning("No templates found.")
            return

        try:
            self.sg_template.validate_template_list(all_templates.values())
        except SgtkTemplateNotFoundException as e:
            logger.error(e)
            self.missing_template = True
            return

        # Set the context.
        task_id = self.selected_task()
        if not task_id:
            logger.warning("No task selected.")
            return

        # Set the output version.
        self.output_version = self.sg_template.next_version_from_template_list(
            all_templates.values(),
            int(task_id),
        )

        # Set the output USD path.
        self.output_path = self.sg_template.output_path_from_template(
            template_name,
            int(task_id),
            self.output_version,
        )

        # Set the output root path.
        self.output_root = os.path.dirname(self.output_path)

        # Set the output Hip path.
        self.output_hip_path = self.sg_template.output_path_from_template(
            all_templates.get("publish_scene"),
            int(task_id),
            self.output_version,
        )

        # Set the output alembic path.
        self.output_alembic_path = self.sg_template.output_path_from_template(
            all_templates.get("alembic"),
            int(task_id),
            self.output_version,
        )

        # Clean-up the UI.
        refresh_list = []
        refresh_list.append(self.current_node.parm("output_version").path())
        refresh_list.append(self.current_node.parm("output_root").path())
        refresh_list.append(self.current_node.parm("lopoutput").path())
        nodes.force_ui_update(refresh_list)

    def __write_publish_scene(self):
        """Write the publish scene file to disk."""
        current_hip_path = hou.hipFile.path()
        filesystem.create_directory(os.path.dirname(self.output_hip_path))
        hou.hipFile.save(file_name=self.output_hip_path, save_to_recent_files=False)
        logger.info(
            "Publish scene file written to {path}".format(
                path=self.output_hip_path,
            )
        )
        hou.hipFile.setName(current_hip_path)

    def __write_alembic(self):
        """Write the publish alembic to disk."""
        abc_rop_node = self.current_node.node("ALEMBIC_OUT/sopnet1/EDIT/ABC_OUT")
        abc_rop_node.parm("execute").pressButton()
        logger.info(
            "Alembic file written to {path}".format(path=self.output_alembic_path)
        )

    def __write_usd(self):
        """Write the publish USD (and compounds) to disk."""
        lop_node = self.current_node.node("IN")
        solaris.create_usd_directories(lop_node.path(), self.output_path)

        # Write the USD file(s).
        usd_rop = self.current_node.node("USD_OUT")
        usd_rop.parm("execute").pressButton()
        logger.info("USD file written to {path}".format(path=self.output_path))

    def __get_compound_path(self, parm_name):
        """
        Get the compound path for the given parm.

        Args:
            parm_name(str): The compound parm to look-up.

        Returns:
            compound_path(str): The path for the given compound.
        """
        compound_path = self.current_node.evalParm(parm_name)
        try:
            is_file = os.path.isfile(compound_path)
        except Exception as e:
            logger.error("Failed to os.path.isfile('{}'): {}".format(compound_path, e))
        else:
            if not is_file:
                logger.warning(
                    "Compound USD not found: {path}".format(
                        path=compound_path,
                    )
                )

        return compound_path

    def usd_publish(self):
        """Write the USD and associated files and publish it to shotgun."""
        # Make sure output paths are up to date.
        self.update_output_path()

        # Grab the templates.
        template_name = self.selected_template()
        all_templates = self.get_all_templates(template_name)

        task_id = self.selected_task()

        # Get the publish comment.
        comment = self.current_node.evalParm("comment")
        if not comment:
            comment = "Compound publish for {name} version {version}.".format(
                name=os.path.basename(self.current_node.evalParm("lopoutput")),
                version=self.output_version,
            )

        # Get the context.
        task_id = self.selected_task()

        # Create the publish object.
        sg_publish = publish.SGPublish(
            self.sg_script,
            self.sg_key,
            task_id=int(task_id),
            version=self.output_version,
            description=comment,
        )

        # Save a new work file version.
        work_path = self.sg_template.output_path_from_template(
            all_templates.get("work_scene"),
            int(task_id),
            self.output_version,
        )
        filesystem.create_directory(os.path.dirname(work_path))
        hou.hipFile.save(file_name=work_path)
        logger.info("Work scene file written to {path}".format(path=work_path))

        # Save a publish file version.
        if self.current_node.evalParm("include_hip"):
            self.__write_publish_scene()
            sg_publish.add_child_publish_item(
                self.output_hip_path,
                "Houdini Scene",
            )

        # Write Alembic file.
        if self.current_node.evalParm("include_alembic"):
            self.__write_alembic()
            sg_publish.add_child_publish_item(
                self.output_alembic_path,
                "Alembic Cache",
            )

        # Write USD file.
        self.__write_usd()

        # Publish USD compound files.
        if self.current_node.evalParm("include_compound_usd"):
            compound_parms = [
                "output_compound_group",
                "output_compound_render",
                "output_compound_proxy",
                "output_compound_guide",
            ]
            for compound in compound_parms:
                input_group_usd = self.__get_compound_path(compound)
                sg_publish.add_child_publish_item(
                    input_group_usd,
                    "USD Compound",
                )

        sg_publish.add_main_publish_item(
            self.current_node.evalParm("lopoutput"),
            "USD Scene",
        )

        # Run the publish.
        result = sg_publish.run_publish()
        logger.info("Publish Complete. ID: {version}.".format(version=result))
        self.update_output_path()


def get_shotgun_node(current_node):
    """Load the current instance of the SG node.

    This is looked up from the cachedUserData for the node it's being requested from.

    Args:
        current_node(hou.Node): The node to get the SG class instance for.

    Returns:
        sg_node(rbl_pipe_houdini.shotgun.usdcompoundnode.USDCompoundPublish): The SG
            class instance for the given node.
    """
    return USDCompoundPublish.get_shotgun_node(current_node)
