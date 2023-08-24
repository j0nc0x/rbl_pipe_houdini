#!/usr/bin/env python

"""A simple Houdini node validator."""

import pyblish.api

from rbl_pipe_core.pyblish import validatewithautofix


class SimpleNodeValidator(validatewithautofix.ValidateWithAutoFix):
    """Pyblish plugin to provide a simple HDA validation.

    To be used `pyblish_validate` should be implemented on the HDAs PythonModule. A
    simple fix function can be provided by also implementing `pyblish_fix`.
    """

    families = ["simple"]
    order = pyblish.api.ValidatorOrder + 0.1
    label = "Houdini Node - Simple Validator"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            if not self.has_validate_method(node):
                self.log.info(
                    "Skipping - no validate function exists for {node}.".format(
                        node=node.type().name()
                    )
                )
                continue
            node.hm().pyblish_validate(node)
            self.log.info(
                "Simple Node Validator succeeded for {node}".format(node=node.path())
            )

    @staticmethod
    def has_validate_method(node):
        """Determine if the given node has a validate function implemented.

        Args:
            node(hou.Node): The houdini node to check.

        Returns:
            (bool): Does the validate function exist?
        """
        if hasattr(node.hm(), "pyblish_validate"):
            validate = getattr(node.hm(), "pyblish_validate")
            if callable(validate):
                return True
        return False

    @classmethod
    def auto_fix(cls, instance, action):
        """Run the auto-fix method.

        This attempts to run the pyblish_fix function on the node.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
            action: The pyblish action taking place.
        """
        for node in instance:
            if not cls.has_fix_method(node):
                action.log.info(
                    "Skipping - no fix function exists for {node}.".format(
                        node=node.type().name()
                    )
                )
                continue
            node.hm().pyblish_fix(node)

    @staticmethod
    def has_fix_method(node):
        """Determine if the given node has a fix function implemented.

        Args:
            node(hou.Node): The houdini node to check.

        Returns:
            (bool): Does the fix function exist.
        """
        if hasattr(node.hm(), "pyblish_fix"):
            fix = getattr(node.hm(), "pyblish_fix")
            if callable(fix):
                return True
        return False
