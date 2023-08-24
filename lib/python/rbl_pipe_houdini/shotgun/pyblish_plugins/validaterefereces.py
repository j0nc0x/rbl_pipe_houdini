#!/usr/bin/env python

"""Validate USD references."""

import pyblish.api

from rbl_pipe_houdini.shotgun import usdpublishnode
from rbl_pipe_houdini.utils import solaris


class ValidateReferences(pyblish.api.InstancePlugin):
    """Pyblish plugin to validate the references within the published USD."""

    order = pyblish.api.ValidatorOrder
    label = "Validate References"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            sg_node = usdpublishnode.get_shotgun_node(node)
            self.validate_references(sg_node)

    def validate_references(self, sg_node):
        """Run the validation on the USD stage.

        Args:
            sg_node(ShotgunNode): The SG node instance we are validating.
        """
        in_node = sg_node.current_node.node("IN")
        references = solaris.get_references(in_node.path())

        implicit = solaris.implicit_references(
            in_node.path(),
            external_references=references,
        )
        # Process Houdini OP implicit refs
        for ref in implicit:
            self.log.info(
                "Unpublished Impicit Reference: {ref}".format(
                    ref=ref,
                )
            )

        # Process other file refs
        file_references = solaris.file_references(
            in_node.path(),
            external_references=references,
        )
        for ref in file_references:
            self.log.info(
                "Unpublished File Reference: {ref}".format(
                    ref=ref,
                )
            )

        # Process turret refs
        turret_references = solaris.turret_references(
            in_node.path(),
            external_references=references,
        )
        for ref in turret_references:
            self.log.info("Turret Reference: {ref}".format(ref=ref))
