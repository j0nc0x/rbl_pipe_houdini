#!/usr/bin/env python

"""Report the node details."""

import pyblish.api


class NodeDetails(pyblish.api.InstancePlugin):
    """Pyblish plugin to make sure the node details are logged.

    This is in order to make it easy to determine which node each instance refers to. It
    is intentionally designed to run before all other validators, to ensure the entries
    are at the top of the list.
    """

    families = ["generic"]
    order = pyblish.api.ValidatorOrder - 0.1
    label = "Houdini Node - Details"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            self.log.info("Node path: {node_path}.".format(node_path=node.path()))
            self.log.info(
                "Node type: {node_type}.".format(node_type=node.type().name())
            )
