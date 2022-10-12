#!/usr/bin/env python

"""Class that handles supporting SG menus on Houdini HDAs."""

import logging

import hou

from rbl_pipe_core.util import farm

from rbl_pipe_houdini.shotgun import context
from rbl_pipe_houdini.shotgun import sgmenu
from rbl_pipe_houdini.utils import get_config

from rbl_pipe_sg import load
from rbl_pipe_sg import template


logger = logging.getLogger(__name__)


class ShotgunNode(object):
    """Shotgun Node for houdini HDAs to add support for SG menus."""

    __config = get_config()
    sg_script = __config.get("sg_script")
    sg_key = __config.get("sg_key")

    def __init__(self, current_node, publish=False):
        """Initialise the class based on the given node.

        Args:
            current_node(hou.Node): The Houdini node to initialise the class with.
            publish(bool): Is the node a publish node.
        """
        self.current_node = current_node
        self.sg_load = load.ShotgunLoad.get_instance(
            self.sg_script,
            self.sg_key,
        )
        self.published_file_type_code = self.__load_published_file_type_code()
        self.published_file_type = self.sg_load.get_published_file_type(
            self.published_file_type_code,
        )

        self.output_version = None
        self.output_root = None
        self.output_path = None
        self.missing_template = False
        self.asset_templates = list()
        self.shot_templates = list()
        self.all_asset_templates = list()
        self.all_shot_templates = list()
        self.hip_templates = [
            "houdini_asset_work",
            "houdini_asset_publish",
            "houdini_shot_work",
            "houdini_shot_publish",
        ]
        self.sg_template = template.SGTemplate(
            self.sg_script,
            self.sg_key,
        )
        self.sg_context = context.HoudiniSGContext(
            self,
            self.sg_script,
            self.sg_key,
        )

        self.sg_asset_menus = {}
        self.sg_shot_menus = {}

        self.template_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("template")
        )
        self.sg_asset_menus["template"] = self.template_menu
        self.sg_shot_menus["template"] = self.template_menu

        self.asset_type_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("asset_type")
        )
        self.sg_asset_menus["asset_type"] = self.asset_type_menu

        self.asset_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("asset")
        )
        self.sg_asset_menus["asset"] = self.asset_menu

        self.asset_step_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("step")
        )
        self.sg_asset_menus["step"] = self.asset_step_menu

        self.asset_task_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("task")
        )
        self.sg_asset_menus["task"] = self.asset_task_menu

        self.sequence_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("sequence")
        )
        self.sg_shot_menus["sequence"] = self.sequence_menu

        self.shot_menu = sgmenu.SGMenu(self.sg_context, self.current_node.parm("shot"))
        self.sg_shot_menus["shot"] = self.shot_menu

        self.shot_step_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("shot_step")
        )
        self.sg_shot_menus["shot_step"] = self.shot_step_menu

        self.shot_task_menu = sgmenu.SGMenu(
            self.sg_context, self.current_node.parm("shot_task")
        )
        self.sg_shot_menus["shot_task"] = self.shot_task_menu

        version = self.current_node.parm("version")
        if version:
            self.sg_version_menu = sgmenu.SGMenu(self.sg_context, version)
            self.sg_asset_menus["version"] = self.sg_version_menu
            self.sg_shot_menus["version"] = self.sg_version_menu

        # Refresh the menus
        self.update_all_menus()

        logger.info(
            "ShotgunNode intitalised for {node}".format(
                node=self.current_node,
            )
        )

    @classmethod
    def get_shotgun_node(cls, current_node):
        """Load the current instance of the SG Node.

        This is looked up from the cachedUserData for the node it's being requested
        from.

        Args:
            current_node(hou.Node): The node to get the SG class instance for.

        Returns:
            The SG Node class instance for the given node.
        """
        if not current_node.cachedUserData("sg_init"):
            # Make sure we only initialise once
            current_node.setCachedUserData("sg_init", True)
            sg_node = cls(current_node)
            current_node.setCachedUserData("sg_node", sg_node)
        else:
            sg_node = current_node.cachedUserData("sg_node")

        return sg_node

    @classmethod
    def initialise(cls, current_node):
        """Create a new instance of RebellionFileCacheNode.

        This instance is then stored on the cachedUserData for the node it's being
        requested from.

        Args:
            current_node(hou.Node): The node to initialise the SG class for.
        """
        logger.warning(
            "This method of initialising is deprecated. `get_shotgun_node` should be "
            "used instead."
        )
        current_node.setCachedUserData(
            "sg_init",
            True,
        )
        current_node.setCachedUserData(
            "sg_node",
            cls(current_node),
        )

    def load_from_scene(self, force, node_parm):
        """Load the node parm value from the scene context.

        This can be implemented from inherited classes to read the context from the
        scene.

        Args:
            force(bool): Should we force the context to be loaded fromt the scene.
            node_parm(str): The name of the node parm to load.

        Returns:
            (None): We don't load from scene by default.
        """
        return None

    def __has_asset_menus(self):
        """Check if the current node includes the asset menus.

        Returns:
            bool: Does the current node have SG asset menus.
        """
        if (
            self.current_node.parm("asset_type")
            and self.current_node.parm("asset")
            and self.current_node.parm("step")
            and self.current_node.parm("task")
        ):
            return True

        return False

    def __has_shot_menus(self):
        """Check if the current node includes the shot menus.

        Returns:
            bool: Does the current node have SG shot menus.
        """
        if (
            self.current_node.parm("shot")
            and self.current_node.parm("shot_step")
            and self.current_node.parm("shot_task")
        ):
            return True

        return False

    def in_asset_mode(self):
        """Check if the current node is in asset mode.

        Returns:
            bool: Is the current node in asset mode.
        """
        selected_template = self.get_parm_menu_value("template")
        if selected_template in self.asset_templates:
            return True

        return False

    def in_shot_mode(self):
        """Check if the current node is in shot mode.

        Returns:
            bool: Is the current node in shot mode.
        """
        selected_template = self.get_parm_menu_value("template")
        if selected_template in self.shot_templates:
            return True

        return False

    def get_version(self):
        """Get the version from the current node.

        Check if the latest flag is set, if it is return latest, otherwise return the
        specified version. If latest is not set, and no version is specified, default
        to latest.

        Returns:
            str: The version number for the file being loaded.
        """
        # If "latest" and "version" parameters exist report the version
        if self.current_node.parm("latest") and self.current_node.parm("version"):
            if not self.current_node.evalParm("latest"):
                version = self.current_node.evalParm("version")
                if version:
                    return str(version)
                else:
                    return ""

        # In all other cases always return "latest"
        return "latest"

    def selected_task(self):
        """Get the currently selected task from either the asset task or shot task menu.

        Returns:
            str: The currently selected task ID from the menu.

        Raises:
            RuntimeError: Node must be either in asset mode or shot mode.
        """
        if self.in_asset_mode():
            return self.get_menu("task").get_selection()
        elif self.in_shot_mode():
            return self.get_menu("shot_task").get_selection()
        else:
            raise RuntimeError("Invalid mode. Must be either asset or shot.")

    # --------------------------- Utility methods -----------------------------

    def get_project_name(self):
        """Return the project name as a string if it is available.

        Returns:
            (str): The project name.
        """
        if "name" in self.sg_load.project:
            return self.sg_load.project.get("name")

        return None

    # --------------------------- Get menu selections ---------------------------------

    def selected_template(self):
        """Return the currently selected template.

        Returns:
            (str): The selected template name for the current node.
        """
        template = self.current_node.evalParm("template")
        if not template:
            parm = self.current_node.parm("template")
            menu_items = parm.menuItems()
            if menu_items:
                template = menu_items[0]
            else:
                template = None
        return template

    # ------------------------- Load data from the node -------------------------------

    def __load_published_file_type_code(self):
        """Retrieve the published_file_type_code from the current node.

        Returns:
            (str): The name of the current nodes published file type.

        Raises:
            NodeError: Template missing from current nodes houdini module.
        """
        if hasattr(self.current_node.hm(), "published_file_type_code"):
            return self.current_node.hm().published_file_type_code
        else:
            raise hou.NodeError(
                "No published file type specified on Houdini node."
                " hm().published_file_type_code should be created."
            )

    def __load_templates(self):
        """Load the templates for the Node.

        Returns:
            list: A list of template details used for the template menu on the
                node.

        Raises:
            NodeError: Template missing from current nodes houdini module.
        """
        templates = []

        if (
            hasattr(self.current_node.hm(), "asset_template")
            and self.current_node.hm().asset_template
        ):
            # Read SG template from node
            if isinstance(self.current_node.hm().asset_template, list) and all(
                isinstance(n, dict) for n in self.current_node.hm().asset_template
            ):
                self.asset_templates = [
                    template.get("usd")
                    for template in self.current_node.hm().asset_template
                ]
                self.all_asset_templates = self.current_node.hm().asset_template
            elif isinstance(self.current_node.hm().asset_template, list):
                self.asset_templates = self.current_node.hm().asset_template
            else:
                self.asset_templates = [self.current_node.hm().asset_template]
            for template_item in self.asset_templates:
                label = "Asset ({template})".format(template=template_item)
                templates.append(
                    {
                        "label": label,
                        "template": template_item,
                    }
                )

        if (
            hasattr(self.current_node.hm(), "shot_template")
            and self.current_node.hm().shot_template
        ):
            # Read SG template from node
            if isinstance(self.current_node.hm().shot_template, list) and all(
                isinstance(n, dict) for n in self.current_node.hm().shot_template
            ):
                self.shot_templates = [
                    template.get("usd")
                    for template in self.current_node.hm().shot_template
                ]
                self.all_shot_templates = self.current_node.hm().shot_template
            elif isinstance(self.current_node.hm().shot_template, list):
                self.shot_templates = self.current_node.hm().shot_template
            else:
                self.shot_templates = [self.current_node.hm().shot_template]
            for template_item in self.shot_templates:
                label = "Shot ({template})".format(template=template_item)
                templates.append(
                    {
                        "label": label,
                        "template": template_item,
                    }
                )

        if not self.asset_templates and not self.shot_templates:
            raise hou.NodeError(
                "No template specified on Houdini node. hm().asset_template "
                "and/or hm().asset_template should be created."
            )

        return templates

    # --------------------------- Update the menus ------------------------------------

    def update_all_menus(self, force=False):
        """Update all the menus on the node.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        self.update_templates_menu(force=force)
        if self.__has_asset_menus():
            self.update_asset_types_menu(force=force)
        if self.__has_shot_menus():
            self.update_sequence_menu(force=force)

    def update_templates_menu(self, force=False):
        """Update the template menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # First refresh the cache
        self.templates = self.__load_templates()

        # Update the menu list
        self.get_menu("template").generate_menu(
            self.templates, "template", "label", force=force
        )

    def update_asset_types_menu(self, force=False):
        """Update the asset type menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # Update the menu list
        asset_types = self.sg_load.get_asset_types()
        self.get_menu("asset_type").generate_menu(
            asset_types, "name", "name", force=force
        )

        # Cascade the update to the next menu
        self.update_asset_menu(force=force)

    def update_asset_menu(self, force=False):
        """Update the asset menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        asset_type = self.get_parm_menu_value("asset_type")

        # First refresh the cache
        if asset_type:
            assets = self.sg_load.get_assets(asset_type=asset_type)
        else:
            logger.warning("No asset_type found, skipping loading assets.")
            assets = []

        # Update the menu
        self.get_menu("asset").generate_menu(assets, "id", "code", force=force)

        # Cascade the update to the next menu
        self.update_step_menu(force=force)

    def update_step_menu(self, force=False):
        """Update the step menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # Keep track of currently selected step
        selected_asset = self.get_parm_menu_value("asset")
        if selected_asset:
            selected_asset = int(selected_asset)

        # First refresh the cache
        if selected_asset:
            steps = self.sg_load.get_asset_steps(asset=selected_asset)
        else:
            logger.warning("No asset found, skipping loading steps.")
            steps = []

        # Update the menu
        self.get_menu("step").generate_menu(
            steps, "step.Step.id", "step.Step.code", force=force
        )

        # Cascade the update to the next menu
        self.update_task_menu(force=force)

    def update_task_menu(self, force=False):
        """Update the task menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # Keep track of currently selected asset_type
        selected_asset = self.get_parm_menu_value("asset")
        if selected_asset:
            selected_asset = int(selected_asset)
        selected_step = self.get_parm_menu_value("step")
        if selected_step:
            selected_step = int(selected_step)

        # First refresh the cache
        if selected_asset and selected_step:
            tasks = self.sg_load.get_asset_tasks(
                asset=selected_asset,
                step=selected_step,
            )
        else:
            logger.warning("No asset/step found, skipping loading tasks.")
            tasks = []

        # Update the menu
        self.get_menu("task").generate_menu(tasks, "id", "content", force=force)

        self.update_version_menu()

    def update_sequence_menu(self, force=False):
        """Update the sequence menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # First refresh the cache
        sequences = self.sg_load.get_sequences()

        # Update the menu list
        self.get_menu("sequence").generate_menu(sequences, "name", "name", force=force)

        # Cascade the update to the next menu
        self.update_shot_menu(force=force)

    def update_shot_menu(self, force=False):
        """Update the shot menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # Keep track of currently selected shot
        selected_sequence = self.get_menu("sequence").get_selection()

        # First refresh the cache
        if selected_sequence:
            shots = self.sg_load.get_shots(sequence=selected_sequence)
        else:
            logger.warning("No sequence found, skipping loading shots.")
            shots = []

        # Update the menu list
        self.get_menu("shot").generate_menu(shots, "id", "code", force=force)

        # Cascade the update to the next menu
        self.update_shot_step_menu(force=force)

    def update_shot_step_menu(self, force=False):
        """Update the shot step menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # First refresh the cache
        selected_shot = self.get_menu("shot").get_selection()

        if selected_shot:
            shot_steps = self.sg_load.get_shot_steps(shot=int(selected_shot))
        else:
            logger.warning("No shot found, skipping loading steps.")
            shot_steps = []

        # Update the menu
        self.get_menu("shot_step").generate_menu(
            shot_steps, "step.Step.id", "step.Step.code", force=force
        )

        # Cascade the update to the next menu
        self.update_shot_task_menu(force=force)

    def update_shot_task_menu(self, force=False):
        """Update the shot task menu.

        Args:
            force(bool): Force data to be re-loaded from SG.
        """
        # First refresh the cache
        selected_shot = self.get_menu("shot").get_selection()
        selected_step = self.get_menu("shot_step").get_selection()

        if selected_shot and selected_step:
            shot_tasks = self.sg_load.get_shot_tasks(
                shot=int(selected_shot),
                step=int(selected_step),
            )
        else:
            logger.warning("No shot/step found, skipping loading tasks.")
            shot_tasks = []

        # Update the menu
        self.get_menu("shot_task").generate_menu(
            shot_tasks, "id", "content", force=force
        )

        self.update_version_menu()

    def update_version_menu(self, force=False):
        """Update the version menu.

        Args:
            force(bool): Force data to be re-loaded from SG.

        Raises:
            RuntimeError: Node must be in either asset mode or shot mode.
        """
        if self.current_node.parm("latest") and (
            force or not self.current_node.evalParm("latest")
        ):
            logger.info("Updating version menu.")
            if self.in_asset_mode():
                task = self.get_menu("task").get_selection()
            elif self.in_shot_mode():
                task = self.get_menu("shot_task").get_selection()
            else:
                raise RuntimeError("Invalid mode. Must be either asset or shot.")

            versions = self.sg_load.get_versions(
                int(task),
                published_file_type=self.published_file_type_code,
            )

            self.sg_version_menu.generate_menu(
                versions,
                "version_number",
                "version_number",
                reverse=True,
                force=force,
            )

        self.menus_updated()

    def menus_updated(self):
        """Menus updated callback.

        This method is exectuted after all the menus have been updated. Can be
        implemented to run a post update step.
        """
        pass

    def update_mode(self):
        """Handle the case of the mode menu changing."""
        mode = self.current_node.parm("mode")
        if mode and mode.evalAsString() == "auto":
            self.update_all_menus(force=True)

    def fix_sequence_menu(self):
        """Fix the value set to the sequence menu.

        When the nodetype is updated from a version missing a sequence menu the
        sequence and shot can get out of sync. This method is run from the
        syncnodeversion node callback to manually set the sequence to the correct value
        in there cases.
        """
        selected_shot = self.get_menu("shot").get_selection()
        if selected_shot:
            sequence = self.sg_load.sequence_name_from_shot_id(int(selected_shot))
            self.current_node.parm("sequence").set(sequence)
            self.update_all_menus()

    def get_template_menu(self):
        """Get the value from the template menu.

        Method kept for backwards compatibility with older Node versions.

        Returns:
            menu(:obj: list of `str`): The list of menu entries required for the menu.
        """
        menu = self.template_menu.get_menu()
        return menu

    def __raw_version(self):
        """Read the current version from SG for the selected task_id.

        Returns:
            dict: The SG version dictionary based on the current selections.

        Raises:
            RuntimeError: Node must be in either asset or shot mode.
        """
        if self.in_asset_mode():
            task = self.get_menu("task").get_selection()
        elif self.in_shot_mode():
            task = self.get_menu("shot_task").get_selection()
        else:
            raise RuntimeError("Invalid mode. Must be either asset or shot.")

        return self.sg_load.current_version(
            int(task),
            published_file_type=self.published_file_type_code,
        )

    def current_version(self):
        """Get the current version as a string.

        Returns:
            str: The current version number.
        """
        version = self.__raw_version()

        if version:
            return str(version.get("version_number"))

        return ""

    def set_current_version(self):
        """Get the current version and set it to the node.

        If there is no version clear the parameter.
        """
        self.update_version_menu(force=True)

    def get_menu(self, parm_name):
        """Get the SG menu for the given parm name.

        Args:
            parm_name(str): The parm name to get the SG menu for.

        Returns:
            (rbl_pipe_houdini.shotgun.sgmenu.SGMenu): The SG menu instance for the
                given parm name.
        """
        if parm_name in self.sg_asset_menus:
            return self.sg_asset_menus.get(parm_name)
        elif parm_name in self.sg_shot_menus:
            return self.sg_shot_menus.get(parm_name)

        return None

    def parm_overriden(self, parm_name):
        """Check if the given parm name is overriden.

        Args:
            parm_name(str): The parm name to check the override status for.

        Returns:
            (bool): Is the given parm overriden.
        """
        override_parm_name = "override_{parm}".format(parm=parm_name)
        override_parm = self.current_node.parm(override_parm_name)
        return override_parm and override_parm.eval()

    def get_menu_list(self, parm_name):
        """
        Get the menu list for the given parm name.

        Args:
            parm_name(str): The parm name to lookup the current menu list for.

        Returns:
            menu(list): The menu list for the given parm.
        """
        menu = []
        node_menu = self.get_menu(parm_name)
        if node_menu:
            menu = node_menu.get_menu()
        return menu

    def get_parm_menu_value(self, parm_name):
        """Get the value of the given SG menu parm.

        Args:
            parm_name(str): The parm name to lookup the current value for.

        Returns:
            The value of the given SG menu parm.
        """
        return self.get_menu(parm_name).get_selection()

    def context_overriden(self):
        """
        Determine if the context has been overriden.

        Returns:
            (bool): Is the context overriden using the SG menus.
        """
        for parm_name in self.sg_asset_menus.keys():
            if self.parm_overriden(parm_name):
                return True
        for parm_name in self.sg_shot_menus.keys():
            if self.parm_overriden(parm_name):
                return True

        return False

    def update_menu_overrides(self, parm_name, overriden):
        """Update the menu override parms.

        Args:
            parm_name(str): The name of the parm to update the override for.
            overriden(bool): Should the parm be overriden.
        """
        override_parm = self.current_node.parm("override_{parm}".format(parm=parm_name))
        if not override_parm:
            logger.warning("Cannot configure parm {parm}".format(parm=parm_name))
            return

        if overriden is None:
            overriden = self.parm_overriden(parm_name)

        if overriden:
            override_parm.set(1)
        else:
            override_parm.set(0)

    def configure_menus(self, parm_name=None):
        """Configure the menus on the node based on their overide parms.

        These changes are cascaded across all the menus.

        Args:
            parm_name(str): The name of the parm to cascade the changed from.
        """
        editable = self.current_node.isEditableInsideLockedHDA()
        if not editable:
            return

        if parm_name:
            parms = []
            if parm_name in self.sg_asset_menus.keys():
                parms += list(self.sg_asset_menus.keys())
            if parm_name in self.sg_shot_menus.keys():
                parms += list(self.sg_shot_menus.keys())

            if not parms:
                logger.warning(
                    "Parm couldn't be found: {parm_name}".format(
                        parm_name=parm_name,
                    )
                )
                return
            index = parms.index(parm_name)
            parms = parms[index:]
        else:
            parms = list(self.sg_asset_menus.keys()) + list(self.sg_shot_menus.keys())

        if parms:
            overriden = self.parm_overriden(parms[0])
        else:
            overriden = False

        for parm_name in parms[1:]:
            self.update_menu_overrides(parm_name, overriden)

    def context_message(self):
        """Generate the context message to be displayed on the node.

        Returns:
            (str): Context details string.
        """
        custom_task_id = self.sg_context.task_id_from_custom()
        globals_task_id = self.sg_context.task_id_from_globals()
        hip_task_id = self.sg_context.task_id_from_hip()
        if custom_task_id is not None:
            if self.sg_load.valid_task_id(custom_task_id):
                return "Context from custom task ID: {task_id}".format(
                    task_id=custom_task_id,
                )
        elif globals_task_id is not None:
            if self.sg_load.valid_task_id(globals_task_id):
                return "Context from scene globals at: {path}".format(
                    path=self.sg_context.get_globals_node(),
                )
        elif hip_task_id is not None:
            if self.sg_load.valid_task_id(hip_task_id):
                return "Context from scene path: {path}".format(
                    path=hou.hipFile.path(),
                )

        return "No context could be loaded."

    def invalid_context(self):
        """Check if the current context is invalid.

        This is used to make sure the USD scene graph isn't modified when a valid
        context isn't set using the switch LOP within the SG node.

        Returns:
            (bool): Is the context invalid?
        """
        # If we are on the farm, we use the cached paths returned from the context
        # instead of the context itself. So in that case there is no need to validate
        # the context here.
        if farm.running_on_farm():
            return False

        task_id = self.sg_context.raw_task_id()
        if not self.sg_load.valid_task_id(task_id) and not self.context_overriden():
            return True
        return False

    def template_context(self):
        """Get the current template for the "template_context" parm on the node.

        This parm is referenced in the "Hide When" field for the SG menus. Due to this
        it has a requirement to always return a default.

        Returns:
            (str): The current template.
        """
        template_overriden = self.parm_overriden("template")
        current_template = self.sg_context.template()

        if template_overriden:
            return self.get_parm_menu_value("template")
        elif current_template:
            return current_template
        else:
            if self.asset_templates:
                return self.asset_templates[0]
            elif self.shot_templates:
                return self.shot_templates[0]

        return ""
