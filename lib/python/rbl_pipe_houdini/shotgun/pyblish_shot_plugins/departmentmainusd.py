#!/usr/bin/env python

"""Department Main USD Pyblish Plugin."""

import pyblish.api

from rbl_pipe_houdini.shotgun import usdpublishnode


class DepartmentMainUSD(pyblish.api.InstancePlugin):
    """Pyblish plugin to handle the department main USD publish."""

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Department Main USD"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            sg_node = usdpublishnode.get_shotgun_node(node)
            sg_node.department_main_usd()
