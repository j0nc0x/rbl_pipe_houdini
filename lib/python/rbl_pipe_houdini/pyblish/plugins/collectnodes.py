#!/usr/bin/env python

"""Validate if a Houdini node is published."""

import hou

import pyblish.api

from rbl_pipe_houdini.pyblish import nodevalidator


class CollectNodes(pyblish.api.ContextPlugin):
    """Pyblish plugin to collect Houdini nodes to validate.

    The nodes are included based on a given dictionary of node paths.
    """

    order = pyblish.api.CollectorOrder
    label = "Houdini Node - Collect"

    def process(self, context):
        """Pyblish process method.

        Args:
            context(pyblish.Context): The Houdini node instances we are validating.
        """
        for node_path in nodevalidator.PyblishNodeValidator.all_nodes:
            families = nodevalidator.PyblishNodeValidator.all_nodes.get(node_path)
            node = hou.node(node_path)

            # Note - pyblish is horrible. If you don't set a family here it adds
            # the 'default' family automatically, which will be the first in the
            # list and will be used to seperate the collected instances in the
            # UI (so they will all be grouped together). You cant pass a list in
            # here, so instead pass the first in our list of families, adding
            # the rest two lines below (yes = must be overloaded here, and yes,
            # again pyblish is horrible)
            instance = context.create_instance(node.name(), family=families[0])
            instance[:] = [node]
            instance.data["families"] = families[1:]
