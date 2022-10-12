#!/usr/bin/env python

"""Shotgun USD Node."""

import logging
import os
import time

from rbl_pipe_core.util import farm

from rbl_pipe_houdini.shotgun import node

from rbl_pipe_usd.resolve import ar
from rbl_pipe_usd.resolve import uribuilder


logger = logging.getLogger(__name__)


class ShotgunUSDNode(node.ShotgunNode):
    """Shotgun USD Node - USD / Turret support."""

    def __init__(self, current_node):
        """
        Initialise based on the given node.

        Args:
            current_node(hou.Node): The Houdini node to intialise based on.
        """
        super(ShotgunUSDNode, self).__init__(current_node)
        self.uri_builder = uribuilder.UriBuilder(self.sg_script, self.sg_key)

        logger.info(
            "ShotgunUSDNode intitalised for {node}".format(
                node=self.current_node,
            )
        )

    def get_task(self):
        """
        Get the task ID based on the current selections.

        Returns:
            (int): The currently selected task ID.
        """
        if self.in_asset_mode():
            return int(self.sg_asset_menus.get("task").get_selection())
        elif self.in_shot_mode():
            return int(self.sg_shot_menus.get("shot_task").get_selection())

    def generate_uri(self):
        """
        Generate a URI based on the current context.

        Returns:
            str: The generated URI.

        Raises:
            RuntimeError: If we aren't in either asset mode or shot mode.
        """
        if farm.running_on_farm():
            return self.current_node.userData("uri") or ""

        if self.in_asset_mode():
            uri = self.generate_asset_uri()
        elif self.in_shot_mode():
            uri = self.generate_shot_uri()
        else:
            raise RuntimeError("Invalid mode. Must be either asset or shot.")

        self.current_node.setUserData("uri", uri)
        return uri

    def generate_asset_uri(self):
        """
        Generate a URI based on the current asset context.

        Returns:
            str: The generated URI.
        """
        return self.uri_builder.build_task_uri(
            self.sg_load.project.get("name"),
            "usd_asset_publish",
            self.get_task(),
            version=self.get_version(),
        )

    def generate_shot_uri(self):
        """
        Generate a URI based on the current shot context.

        Returns:
            str: The generated URI.
        """
        return self.uri_builder.build_task_uri(
            self.sg_load.project.get("name"),
            "usd_shot_publish",
            self.get_task(),
            version=self.get_version(),
        )

    def primitive_path(self):
        """
        Generate the prim path that should be used.

        Returns:
            str: The primitive path to use based on the current node context.

        Raises:
            RuntimeError: If we aren't in either asset mode or shot mode.
        """
        if farm.running_on_farm():
            return self.current_node.userData("prim_path") or ""

        prim_path = "/source"

        if self.in_asset_mode():
            asset = self.get_menu("asset").get_selection()
            if asset:
                prim_path = "/{asset}".format(
                    asset=self.sg_load.asset_name_from_id(int(asset)),
                )

        elif self.in_shot_mode():
            shot = self.get_menu("shot").get_selection()
            step = self.get_menu("shot_step").get_selection()
            task = self.get_menu("shot_task").get_selection()
            if shot and step and task:
                prim_path = "/{shot}_{step}_{task}".format(
                    shot=self.sg_load.shot_name_from_id(int(shot)),
                    step=self.sg_load.step_name_from_id(int(step), shot_id=int(shot)),
                    task=self.sg_load.task_name_from_id(int(task)),
                )
        else:
            raise RuntimeError("Invalid mode. Must be either asset or shot.")

        self.current_node.setUserData("prim_path", prim_path)
        return prim_path

    def refresh_cache(self):
        """Refresh the turret cache.

        Turret caches the results it gets from Shotgun, which can lead to
        problems with the cache getting stale. The cache can be refreshed by
        specifying a time in the query URI. By default we use the time the
        ShotgunLoad class gets created, unless the user refreshes the cache by
        using the refresh button on the node.
        """
        os.environ["USD_ASSET_TIME"] = str(time.time())

        # To allow for the slightly different filepath naming on
        # sglayer vs sgsublayer / sgreference
        parms = self.current_node.globParms("filepath*")
        if parms:
            # Force a refresh
            parms[0].pressButton()

        # Clear cached uri used in details label
        self.current_node.destroyCachedUserData("uri")

        # update the version menu
        self.update_version_menu(force=True)

    def get_usd_path(self):
        """Get the current real path for the URI being loaded.

        This is cached to the node.

        Returns:
            resolved_path(str): The path to the current USD URI.
        """
        # To allow for the slightly different filepath naming on
        # sglayer vs sgsublayer / sgreference
        parms = self.current_node.globParms("filepath*")
        if parms:
            uri = parms[0].eval()
        else:
            uri = ""

        resolved_path = ar.resolve_path(uri)
        return resolved_path


def get_shotgun_node(current_node):
    """Load the current instance of Shotgun Node.

    Load the instance from the given nodes cachedUserData.

    Args:
        current_node(hou.Node): The node to get the shotgun node for.

    Returns:
        rbl_pipe_houdini.shotgun.usdnode.ShotgunUSDNode: The ShotgunUSDNode
            instance for the given node.
    """
    return ShotgunUSDNode.get_shotgun_node(current_node)


def initialise(current_node, publish=False):
    """Initialise ShotgunLoad and ShotgunUSDNode for use with the given node.

    Create a new instance of ShotgunLoad if one doesn't already exist and store
    it in hou.session. Also create an instance of ShotgunUSDNode and store it
    in the cachedUserData for the node it's being requested from.

    Args:
        current_node(hou.Node): The node we have initialised from.
        publish(bool): Is the node a publish node.
    """
    ShotgunUSDNode.initialise(current_node)
