#!/usr/bin/env python

"""Pyblish Houdini Node Validator Tools."""

import logging
import os

import hou

import pyblish.api

from rbl_pipe_core.pyblish import validatewithautofix

from rbl_pipe_houdini.pyblish import houdinipyblishui
from rbl_pipe_houdini.utils import nodes


logger = logging.getLogger(__name__)


class ValidateNode(pyblish.api.InstancePlugin):
    """Pyblish validate node."""

    order = pyblish.api.ValidatorOrder + 0.2
    label = "Houdini Validate Node"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            self.log.info("Validating {path}.".format(path=node.path()))
            self.validate(node)

    def validate(self, node):
        """Validate the node.

        Args:
            node(hou.Node): The Houdini node being validated.

        Raises:
            NotImplementedError: No validate method could be found.
        """
        raise NotImplementedError("Validate method should be implemented.")


class ValidateFixNode(validatewithautofix.ValidateWithAutoFix):
    """Pyblish validate node with autofix."""

    order = pyblish.api.ValidatorOrder + 0.2
    label = "Houdini Validate Node"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        for node in instance:
            self.log.info("Validating {path}.".format(path=node.path()))
            self.validate(node)

    def validate(self, node):
        """Validate the node.

        Args:
            node(hou.Node): The Houdini node being validated.

        Raises:
            NotImplementedError: No validate method could be found.
        """
        raise NotImplementedError("validate method should be implemented.")

    @staticmethod
    def auto_fix(instance, action):
        """Run the auto-fix method.

        This attempts to run the pyblish_fix function on the node.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
            action: The pyblish action taking place.

        Raises:
            NotImplementedError: No auto_fix method could be found.
        """
        raise NotImplementedError("auto_fix method should be implemented.")


class PyblishNodeValidator:
    """A Pyblish based Houdini Node Validator."""

    all_nodes = {}

    def __init__(self, node_list, title="Houdini Node Validator"):
        """Initialise the Node Validator for the given list of Houdini nodes.

        Args:
            node_list(:obj:`list` of :obj:`str`): A list of Houdini node paths.
            title(:obj:`str`, optional): The title to use for the validator window.
        """
        self.node_list = node_list
        self.title = title

        # Make sure we don't already have plugins loaded from elsewhere
        pyblish.api.deregister_all_paths()
        pyblish.api.deregister_all_plugins()

    @classmethod
    def get_validate_plugins(cls, current_node):
        """Get any pyblish plugins for the given node.

        This is done by checking for the `pyblish_plugins` list in the node's
        PythonModule where the node author declares any plugins located on the node.

        Args:
            current_node(hou.Node): The Houdini node to check for plugins.

        Returns:
            plugins(:obj:`list` of :obj:`str`): A list of pyblish plugins on the node.
        """
        plugins = []
        if hasattr(current_node.hm(), "pyblish_plugins"):
            pyblish_plugins = getattr(current_node.hm(), "pyblish_plugins")
            if isinstance(pyblish_plugins, list):
                plugins.extend(pyblish_plugins)

        return plugins

    @classmethod
    def get_simple_validate(cls, current_node):
        """Determine if the given node has a validate function implemented.

        Args:
            current_node(hou.Node): The houdini node to check.

        Returns:
            (bool): Does the validate function exist?
        """
        if hasattr(current_node.hm(), "pyblish_validate"):
            validate = getattr(current_node.hm(), "pyblish_validate")
            if callable(validate):
                return True
        return False

    @classmethod
    def can_validate(cls, node_list):
        """Check if the given list of nodes can be validated.

        If at least one node has a validation method implemented then validation is
        possible and True will be returned.

        Args:
            node_list(:obj:`list` of :obj:`hou.Node`): A list of nodes that we want to
                check the validation status for.

        Returns:
            (bool): The validation status for the given nodes.
        """
        for node in node_list:
            if nodes.is_digital_asset(node.path()):
                plugins = cls.get_validate_plugins(node)
                if plugins:
                    return True
                if cls.get_simple_validate(node):
                    return True

        return False

    def generate_node_dict(self):
        """Generate a dictionary of Houdini nodes.

        Given the input node_list, generate a dictionary of Houdini nodes and their
        family.

        Returns:
            node_dict(dict): A python dictionary of Houdini node_paths along with any
                required data including their family.
        """
        node_dict = {}
        for node_path in self.node_list:
            family = []
            node = hou.node(node_path)

            if not nodes.is_digital_asset(node_path):
                logger.info("Skipping {node} - not a HDA.".format(node=node.name()))
                continue

            # Get any pyblish plugins stored on the node
            plugins = self.get_validate_plugins(node)
            if plugins:
                family.append(node.type().name())
                for plugin in plugins:
                    pyblish.api.register_plugin(getattr(node.hm(), plugin))

            if self.get_simple_validate(node):
                family.append("simple")

            family.append("generic")

            node_dict[node_path] = family

        return node_dict

    def validate(self):
        """Run the validation UI.

        Returns:
            (QWidget): The Pyblish UI.
        """
        # Setup the node list to be validated
        PyblishNodeValidator.all_nodes = self.generate_node_dict()

        # Register the application host
        pyblish.api.register_host("houdini")

        # Register the plugins
        python_root = os.path.abspath(__file__).rsplit("/lib/python", 1)[0]
        plugins = "lib/python/rbl_pipe_houdini/pyblish/plugins"
        pyblish.api.register_plugin_path(os.path.join(python_root, plugins))

        # Launch the UI
        pyblish_ui = houdinipyblishui.HoudiniPyblishUI(
            title=self.title,
            size=(800, 800),
        )
        return pyblish_ui.launch_ui()
