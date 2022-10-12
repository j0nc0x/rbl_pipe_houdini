#!/usr/bin/env python

"""Run the USD publish."""

import pyblish.api

from rbl_pipe_houdini.shotgun import usdpublishnode


class RunPublish(pyblish.api.InstancePlugin):
    """Pyblish plugin to continue with the USD publish."""

    order = pyblish.api.ExtractorOrder
    label = "USD Publish"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            sg_node = usdpublishnode.get_shotgun_node(node)
            sg_node.usd_publish()
