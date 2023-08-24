#!/usr/bin/env python

"""Validate if a Houdini node is published."""

import pyblish.api

from rbl_pipe_core.util import filesystem

from rbl_pipe_houdini.utils import nodes


class IsPublished(pyblish.api.InstancePlugin):
    """Pyblish plugin to check if the current node is published.

    This is only applicable if the node is a HDA. Non-HDAs are skipped.
    """

    families = ["generic"]
    order = pyblish.api.ValidatorOrder
    label = "Houdini Node - Published"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            if not nodes.is_digital_asset(node.path()):
                self.log.info("Skipping {node} - not a HDA.".format(node=node.name()))
                continue

            path = node.type().definition().libraryFilePath()
            if not filesystem.is_released(path):
                self.log.warning(
                    "Using HDA definition from non-standard \
                location: {path}".format(
                        path=path
                    )
                )
