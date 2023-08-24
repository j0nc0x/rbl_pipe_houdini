#!/usr/bin/env python

"""Asset USD Pyblish Plugin."""

import pyblish.api

from rbl_pipe_houdini.shotgun import usdpublishnode


class RunPublishAssetUSD(pyblish.api.InstancePlugin):
    """Pyblish plugin to handle the Asset USD publish."""

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Asset USD Publish"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            sg_node = usdpublishnode.get_shotgun_node(node)
            sg_node.auto_generate_asset_usd()
