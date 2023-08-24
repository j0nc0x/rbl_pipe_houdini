#!/usr/bin/env python

"""Collect the USD publish nodes."""

import pyblish.api

from rbl_pipe_houdini.shotgun import usdpublishnode


class CollectPublishNode(pyblish.api.ContextPlugin):
    """Pyblish plugin to collect the USD Publish node."""

    order = pyblish.api.CollectorOrder
    label = "Collect"

    def process(self, context):
        """Pyblish process method.

        Args:
            context(pyblish.Context): The Houdini node instances we are validating.
        """
        publish_node = usdpublishnode.ShotgunUSDPublishNode.publish_node
        name = publish_node.type().name()
        instance = context.create_instance(name)
        instance[:] = [usdpublishnode.ShotgunUSDPublishNode.publish_node]
