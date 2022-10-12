#!/usr/bin/env python

"""Asset USD Pyblish Plugin."""

import pyblish.api

from rbl_pipe_houdini.shotgun import usdpublishnode


class RunPublishShotUSD(pyblish.api.InstancePlugin):
    """Pyblish plugin to handle the Shot USD publish."""

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Shot USD Publish"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            sg_node = usdpublishnode.get_shotgun_node(node)
            sg_node.auto_generate_shot_usd()
