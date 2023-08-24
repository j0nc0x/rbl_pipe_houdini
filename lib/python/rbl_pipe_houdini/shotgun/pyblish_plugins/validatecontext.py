#!/usr/bin/env python

"""Validate USD context."""

import pyblish.api

from rbl_pipe_houdini.shotgun import usdpublishnode


class ValidateContext(pyblish.api.InstancePlugin):
    """Pyblish plugin to validate if the publish context matches the scene context."""

    order = pyblish.api.ValidatorOrder
    label = "Validate Context"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            sg_node = usdpublishnode.get_shotgun_node(node)
            self.matches_scene_context(sg_node)

    def matches_scene_context(self, sg_node):
        """Validate if the USD node context matches the scene context.

        Args:
            sg_node(ShotgunNode): The SG node instance we are validating.

        Raises:
            RuntimeError: Custom task selected on node.
        """
        if sg_node.sg_context.task_id_from_custom() or sg_node.context_overriden():
            raise RuntimeError("Custom task selected on node.")
