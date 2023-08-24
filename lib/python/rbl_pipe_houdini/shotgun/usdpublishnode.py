#!/usr/bin/env python

"""USD Publish Module."""

import logging
import os

import hou

import pyblish.api

from rbl_pipe_houdini.pyblish import houdinipyblishui
from rbl_pipe_houdini.shotgun import usdnode
from rbl_pipe_houdini.utils import dialog
from rbl_pipe_houdini.utils import solaris

from rbl_pipe_sg import publish
from rbl_pipe_sg.template import SgtkTemplateNotFoundException

from rbl_pipe_shotbuild_core.models import DataStore
from rbl_pipe_shotbuild_core.utils import import_shot_data_from_usd

from rbl_pipe_usd.build import assetusd
from rbl_pipe_usd.build import shotusd


logger = logging.getLogger(__name__)


class ShotgunUSDPublishNode(usdnode.ShotgunUSDNode):
    """Publish USD to Shotgun."""

    publish_node = None
    validator_ui = None

    def __init__(self, current_node):
        """Initialise the class based on the given node.

        Args:
            current_node(hou.Node): The Houdini node to initialise the class with.
        """
        self.scene_template = None
        self.scene_asset = None
        self.scene_task = None
        self.scene_step = None
        self.scene_shot = None
        self.scene_shot_step = None
        self.scene_shot_task = None
        self.context = None
        self.hip_asset_templates = [
            "houdini_asset_work",
            "houdini_asset_publish",
        ]
        self.hip_shot_templates = [
            "houdini_shot_work",
            "houdini_shot_publish",
        ]

        super(ShotgunUSDPublishNode, self).__init__(current_node)

        logger.info(
            "ShotgunUSDPublishNode intitalised for {node}".format(
                node=self.current_node,
            )
        )

    def menus_updated(self):
        """Menus updated callback."""
        self.update_output_path()

    def update_save_default(self):
        """Update the save default for the current node.

        We cant set a single default for the USD save style, as this is dependent on
        whether we are in an Asset or Shot context. Check which one and update the
        savestyle parm whenever the template changes.

        Raises:
            RuntimeError: Node must be in either asset mode or shot mode.
        """
        selected_template = self.selected_template()
        # If the template has changed, update the save style
        if selected_template != self.context:
            if self.in_asset_mode():
                self.current_node.parm("savestyle").set("flattenalllayers")
            elif self.in_shot_mode():
                self.current_node.parm("savestyle").set("flattenimplicitlayers")
            else:
                raise RuntimeError("Must be in either asset or shot mode.")
            self.context = selected_template

    def hip_asset_mode(self):
        """Check if we are in asset mode.

        Returns:
            (bool): Is the scene file an asset scene.
        """
        sg_template = self.sg_template.template_from_path(
            hou.hipFile.path(),
            templates=self.hip_templates,
        )
        if sg_template and sg_template.name in self.hip_asset_templates:
            return True

        return False

    def hip_shot_mode(self):
        """Check if we are in shot mode.

        Returns:
            (bool): Is the scene file a shot scene.
        """
        sg_template = self.sg_template.template_from_path(
            hou.hipFile.path(),
            templates=self.hip_templates,
        )
        if sg_template and sg_template.name in self.hip_shot_templates:
            return True

        return False

    def get_output_version(self):
        """Return the output root directory.

        Returns:
            self.output_version(str): The output version for the current node.
        """
        return self.output_version

    def get_output_root(self):
        """Return the output root directory.

        Returns:
            self.output_root(str): The output root for the current node.
        """
        return self.output_root

    def get_output_path(self):
        """Return the output file path.

        Returns:
            self.output_path(str): The output path for the current node.
        """
        return self.output_path

    def update_output_path(self):
        """Update the output file path based on the selected task."""
        if self.missing_template:
            logger.debug("Skipping evaluation for missing template.")
            return

        # Validate the template
        template_name = self.selected_template()
        try:
            self.sg_template.validate_template_list([template_name])
        except SgtkTemplateNotFoundException as e:
            logger.error(e)
            self.missing_template = True
            return

        # Set the context
        task_id = self.selected_task()

        if not task_id:
            logger.warning("No task selected.")
            return

        self.output_version = self.sg_template.next_version_from_template_list(
            [template_name],
            int(task_id),
        )

        self.output_path = self.sg_template.output_path_from_template(
            template_name,
            int(task_id),
            self.output_version,
        )
        self.output_root = os.path.dirname(self.output_path)

        self.current_node.parm("output_version").pressButton()
        self.current_node.parm("output_root").pressButton()
        self.current_node.parm("lopoutput").pressButton()

    def auto_generate_asset_usd(self):
        """Automatically generate and publish the asset USD if it doesn't already exist.

        Raises:
            RuntimeError: Cannot run when not in asset mode.
        """
        task_id = int(self.selected_task())

        if not self.in_asset_mode():
            raise RuntimeError("Can only be run when operating in asset mode.")

        variant_name = self.sg_load.variant_name_from_task(task_id)
        asset_id = self.sg_load.asset_id_from_task_id(task_id)
        assetusd.publish_asset_usd(
            asset_id,
            variant_name,
            self.sg_script,
            self.sg_key,
        )

    def auto_generate_shot_usd(self):
        """Automatically generate and publish the shot USD if it doesn't already exist.

        Raises:
            RuntimeError: Cannot run when not in shot mode.
        """
        task_id = int(self.selected_task())

        if not self.in_shot_mode():
            raise RuntimeError("Can only be run when operating in shot mode.")
            shot_id = self.sg_load.shot_id_from_task_id(task_id)
            shotusd.publish_shot_usd(
                shot_id,
                self.sg_script,
                self.sg_key,
            )

    def department_main_usd(self):
        """Check if the department main USD has been published.

        Raises:
            RuntimeError: The department main USD couldn't be found.
        """
        # Get the context.
        task_id = int(self.selected_task())

        shot_id = self.sg_load.shot_id_from_task_id(task_id)
        shotusd.publish_shot_usd(
            shot_id,
            self.sg_script,
            self.sg_key,
        )

        step = self.sg_load.step_from_task(task_id, short=False)

        ds = DataStore()
        shot = ds.entities["by_id"].get(shot_id)

        # import the task dependency data along the way
        usd_file_path, data_created = import_shot_data_from_usd(shot)

        step_tasks = [
            dep.depends_to for dep in shot.dependencies if dep.depends_to.name == step
        ]

        step_task = None
        main_task = None

        if len(step_tasks) > 1:
            raise RuntimeError(
                "Multiple steps found with the name '{step}'".format(step=step)
            )
        if step_tasks:
            step_task = step_tasks[0]

        if step_task:
            main_tasks = [step_dep.depends_to for step_dep in step_task.dependencies]
            if len(main_tasks) > 1:
                raise RuntimeError(
                    "Multiple main tasks found for step: '{step}'".format(step=step)
                )
            if main_tasks:
                main_task = main_tasks[0]
        else:
            raise RuntimeError(
                "{step} not currently part of Blueprint. This needs updating in "
                "Blueprint before publishes to this task will be included in the "
                "shot.".format(
                    step=step,
                )
            )

        if main_task:
            leaf_tasks = [
                main_task_dep.depends_to for main_task_dep in main_task.dependencies
            ]
            if task_id not in [task.id for task in leaf_tasks]:
                raise RuntimeError(
                    "Publishes to this task will not be included in {step}_main, "
                    "unless Blueprint is updated.".format(
                        step=self.sg_load.step_from_task(task_id),
                    )
                )
        else:
            raise RuntimeError(
                "{step}_main/{current_task} not (yet) part of Blueprint. Publishes to "
                "this task will not be included in {step}_main, unless Blueprint is "
                "updated.".format(
                    step=self.sg_load.step_from_task(task_id),
                    current_task=self.sg_load.task_name_from_id(task_id),
                )
            )

    def run_publish(self):
        """Handle any referenced files whilst running the publish.

        Raises:
            RuntimeError: Invalid mode found on the node.
        """
        # Make sure we don't already have plugins loaded from elsewhere
        pyblish.api.deregister_all_paths()
        pyblish.api.deregister_all_plugins()

        # Make the node to be published available for collection
        ShotgunUSDPublishNode.publish_node = self.current_node

        # Register the application host
        pyblish.api.register_host("houdini")

        # Register the plugins
        python_root = os.path.abspath(__file__).rsplit("/lib/python", 1)[0]
        plugins_root = os.path.join(
            python_root,
            "lib/python/rbl_pipe_houdini/shotgun",
        )
        plugins = os.path.join(plugins_root, "pyblish_plugins")
        pyblish.api.register_plugin_path(plugins)
        if self.in_asset_mode():
            # Asset specific plugins
            pyblish.api.register_plugin_path(
                os.path.join(plugins_root, "pyblish_asset_plugins")
            )
        elif self.in_shot_mode():
            # Shot specific plugins
            pyblish.api.register_plugin_path(
                os.path.join(plugins_root, "pyblish_shot_plugins")
            )
        else:
            raise RuntimeError("Should be either in asset or shot mode.")

        # Launch the UI
        validator = houdinipyblishui.HoudiniPyblishUI(
            title="USD Publish Validation",
            size=(800, 500),
        )
        ShotgunUSDPublishNode.validator_ui = validator.launch_ui()

    def usd_publish(self):
        """Write the usd file and publish it to shotgun."""
        # Make sure output paths are up to date.
        self.update_output_path()

        # Get the context.
        task_id = self.selected_task()

        # Get the publish comment
        comment = None
        comment_parm = self.current_node.parm("comment")
        if comment_parm:
            comment = comment_parm.evalAsString()
        if not comment:
            comment = "{name} version {version}.".format(
                name=os.path.basename(self.current_node.evalParm("lopoutput")),
                version=self.output_version,
            )

        # Create the publish object.
        sg_publish = publish.SGPublish(
            self.sg_script,
            self.sg_key,
            task_id=int(task_id),
            version=self.output_version,
            description=comment,
        )

        # First create any directories required with the correct permissions
        publish_path = self.current_node.evalParm("lopoutput")
        lop_node = self.current_node.node("IN")
        solaris.create_usd_directories(lop_node.path(), publish_path)

        # Write the USD file(s)
        usd_rop = self.current_node.node("usd_rop1")
        usd_rop.parm("execute").pressButton()
        logger.info("USD file written to {path}".format(path=publish_path))

        sg_publish.add_main_publish_item(
            self.current_node.evalParm("lopoutput"),
            "USD Scene",
        )

        # Run the publish.
        result = sg_publish.run_publish()
        logger.info("Publish Complete. ID: {version}.".format(version=result))
        self.update_output_path()

    def run_validate(self):
        """Run the validation on the USD stage."""
        in_node = self.current_node.node("IN")
        references = solaris.get_references(in_node.path())

        severity = hou.severityType.Message
        buttons = ("OK",)

        if len(references) == 0:
            message = "USD file to be created will contain no external file references."
        else:
            message = "USD file to be created will contain external file references."

        # Process Houdini OP implicit refs
        op_refs = solaris.implicit_references(
            in_node.path(),
            external_references=references,
        )
        if len(op_refs) > 0:
            message += (
                "\n\nWarning - Houdini Implicit References (Should be published):"
            )
            severity = hou.severityType.Warning

        for i in op_refs:
            message += "\n{ref}".format(ref=i)

        # Process other file refs
        other_refs = solaris.file_references(
            in_node.path(),
            external_references=references,
        )
        if len(other_refs) > 0:
            message += "\n\nWarning - File References (Should be published):"
            severity = hou.severityType.Warning

        for i in other_refs:
            message += "\n{ref}".format(ref=i)

        # Process turret refs
        turret_refs = solaris.turret_references(
            in_node.path(),
            external_references=references,
        )
        if len(turret_refs) > 0:
            message += "\n\nTurret References:"
        for i in turret_refs:
            message += "\n{ref}".format(ref=i)

        dialog.display_message(
            message,
            buttons=buttons,
            severity=severity,
            title="USD Publish Validation",
        )

    def update_mode(self):
        """Handle the case of the mode menu changing."""
        mode = self.current_node.parm("mode")
        if mode and mode.evalAsString() == "auto":
            self.update_all_menus(force=True)

    def update_templates_menu(self, force=False):
        """Check whether the template menu was updated.

        Only update the save style if it has.

        Args:
            force(bool): Should the update be forced.
        """
        before = self.current_node.parm("template").eval()
        super(ShotgunUSDPublishNode, self).update_templates_menu(force)
        if self.current_node.parm("template").eval() != before:
            self.update_save_default()


def get_shotgun_node(current_node):
    """Load the current instance of ShotgunUSDPublishNode.

    This is looked up from the cachedUserData for the node it's being requested from.

    Args:
        current_node(hou.Node): The node to get the SG class instance for.

    Returns:
        (rbl_pipe_houdini.shotgun.usdpublishnode.ShotgunUSDPublishNode): The SG class
            instance for the given node.
    """
    return ShotgunUSDPublishNode.get_shotgun_node(current_node)


def initialise(current_node, publish=False):
    """Create a new instance of ShotgunUSDPublishNode.

    This instance is stored in the cachedUserData for the node it's being requested
    from.

    Args:
        current_node(hou.Node): The node to initialise the SG class for.
        publish(bool): Are we initialising a node that is responsible for publishing.
    """
    ShotgunUSDPublishNode.initialise(current_node)
