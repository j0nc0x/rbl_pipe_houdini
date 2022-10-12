#!/usr/bin/env python

"""Handle context in Houdini."""

import logging

import hou

from rbl_pipe_houdini.utils import nodes

from rbl_pipe_sg import load
from rbl_pipe_sg import template

logger = logging.getLogger(__name__)


class HoudiniSGContext(object):
    """Class to handle the Houdini scene context."""

    def __init__(self, sg_node, sg_script, sg_key):
        """Initialise the context.

        Args:
            sg_node(rbl_pipe_houdini.shotgun.node.ShotgunNode): The shotgun node
                instance to initialise the context for.
            sg_script(str): The SG script to use.
            sg_key(str): The SG key to use.
        """
        self.sg_node = sg_node
        self.sg_load = load.ShotgunLoad.get_instance(
            sg_script,
            sg_key,
        )
        self.sg_template = template.SGTemplate(
            sg_script,
            sg_key,
        )
        self.globals_node = self.get_globals_node()

    def get_globals_node(self):
        """Get the globals node from the current scene.

        Returns:
            globals_node(hou.Node): The globals node found in the current scene.
        """
        globals_node = nodes.all_nodes_of_type(
            "global",
            node_filter=hou.nodeTypeFilter.Obj,
        )

        if len(globals_node) == 0:
            logger.info(
                "No global node found in the scene. Falling back to use hip path."
            )
            return None
        elif len(globals_node) > 1:
            logger.warning(
                "Only should be one global node in the scene. Using {path}".format(
                    path=globals_node[0].path(),
                )
            )

        globals_node = globals_node[0]

        return globals_node

    def task_id_from_custom(self):
        """Lookup the task ID from the override on the SG node.

        Returns:
            custom_taskid(int): The custom task ID read from the node.
        """
        try:
            if self.sg_node.current_node.evalParm("override_custom_taskid"):
                return int(self.sg_node.current_node.evalParm("custom_taskid"))
        except hou.OperationFailed:
            logger.debug("Cannot parse custom parm value.")

        return None

    def task_id_from_globals(self):
        """Lookup the task ID from the globals node.

        Returns:
            (int): The task ID as read from the globals node.
        """
        if not self.get_globals_node():
            return None

        context = self.globals_node.evalParm("context")
        task_name = self.globals_node.evalParm("task")
        if context == "asset":
            asset_name = self.globals_node.evalParm("asset")
            asset_id = self.sg_load.asset_id_from_name(asset_name)
        elif context == "shot":
            shot_name = self.globals_node.evalParm("shot")
            shot_id = self.sg_load.shot_id_from_name(shot_name)
        else:
            return None

        return self.sg_load.task_id_from_name(
            task_name,
            asset_id=asset_id,
            shot_id=shot_id,
        )

    def task_id_from_hip(self):
        """Lookup the task ID from the Houdini hip file path.

        Returns:
            (int): The task ID as read from the hip path.
        """
        path = hou.hipFile.path()
        return self.sg_template.task_id_from_path(path)

    def raw_task_id(self):
        """Get the task ID from custom / scene globals / hip file.

        Returns:
            (int): The current context task ID.
        """
        custom_task_id = self.task_id_from_custom()
        if custom_task_id:
            return custom_task_id
        elif self.globals_node:
            return self.task_id_from_globals()
        else:
            return self.task_id_from_hip()

    def is_asset_context(self):
        """Check if the current context is an asset.

        Returns:
            (bool): In asset context.
        """
        task_id = self.raw_task_id()
        return self.sg_load.is_asset_task_id(task_id)

    def is_shot_context(self):
        """Check if the current context is an shot.

        Returns:
            (bool): In shot context.
        """
        task_id = self.raw_task_id()
        return self.sg_load.is_shot_task_id(task_id)

    def template(self):
        """Lookup the template from the context.

        Returns:
            (str): The context template.
        """
        if self.is_asset_context() and self.sg_node.asset_templates:
            return self.sg_node.asset_templates[0]
        elif self.is_shot_context() and self.sg_node.shot_templates:
            return self.sg_node.shot_templates[0]

        logger.warning("Should either be in asset or shot context.")
        return None

    def asset_type(self):
        """Lookup the asset type from the context.

        Returns:
            (str): The context asset type.
        """
        asset_id = self.asset()
        asset = self.sg_load.asset_name_from_id(asset_id)
        return self.sg_load.asset_type_from_name(asset)

    def asset(self):
        """Lookup the asset from the context.

        Returns:
            (int): The context asset.
        """
        task_id = self.task()
        return self.sg_load.asset_id_from_task_id(task_id)

    def step(self):
        """Lookup the step from the context.

        Returns:
            (int): The context step.
        """
        task_id = self.task()
        if not task_id:
            return None

        asset_id = self.asset()
        if not asset_id:
            return None

        step = self.sg_load.step_from_task(task_id)
        if not step:
            return None

        return self.sg_load.step_id_from_name(step, asset_id=asset_id)

    def task(self):
        """Lookup the task from the context.

        Returns:
            (int): The context task.
        """
        if self.is_asset_context():
            return self.raw_task_id()
        return None

    def sequence(self):
        """Lookup the sequence from the context.

        Returns:
            (str): The context sequence.
        """
        shot_id = self.shot()
        return self.sg_load.sequence_name_from_shot_id(shot_id)

    def shot(self):
        """Lookup the shot from the context.

        Returns:
            (int): The context shot.
        """
        task_id = self.shot_task()
        return self.sg_load.shot_id_from_task_id(task_id)

    def shot_step(self):
        """Lookup the shot step from the context.

        Returns:
            (int): The contexct shot step.
        """
        task_id = self.shot_task()
        if not task_id:
            return None

        shot_id = self.shot()
        if not shot_id:
            return None

        step = self.sg_load.step_from_task(task_id)
        if not step:
            return None

        return self.sg_load.step_id_from_name(step, shot_id=shot_id)

    def shot_task(self):
        """Lookup the shot task from the context.

        Returns:
            (int): The context shot task.
        """
        if self.is_shot_context():
            return self.raw_task_id()
        return None

    def parm_value_from_context(self, parm_name):
        """Lookup the value for a parameter from the context.

        Args:
            parm_name(str): The parm name to look up.

        Returns:
            The parameter value.
        """
        method = getattr(self, parm_name, None)
        if not method:
            logger.warning(
                "No context method found for {parm_name}".format(parm_name=parm_name)
            )
            return None

        return method()

    def legacy_auto_mode(self):
        """Check if the node is in auto mode.

        In order to maintain backwards compatibility against older node versions, check
        if the node is in "auto" mode.

        Returns:
            (bool): In legacy auto mode?
        """
        mode_parm = self.sg_node.current_node.parm("mode")
        if mode_parm and mode_parm.evalAsString() == "auto":
            return True

        return False
