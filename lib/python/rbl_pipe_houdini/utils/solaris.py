#!/usr/bin/env python

"""Houdini solaris utility functions."""

import logging
import os

import hou

from rbl_pipe_core.util import filesystem

from rbl_pipe_houdini.utils import dialog
from rbl_pipe_houdini.utils import nodes

from rbl_pipe_usd.resolve import ar
from rbl_pipe_usd.utils import rendersettings


logger = logging.getLogger(__name__)


def stage_available(node_path):
    """Check if the USD stage is available for the given node.

    Args:
        node_path(str): The Houdini scene path to the node we want to inspect.

    Returns:
        bool: Whether the stage can be loaded
    """
    node = nodes.node_at_path(node_path)

    if not node:
        return False

    stage = False

    # There seems to be a bug where the stage isn't instantly availble once a Houdini
    # scene finishes loading. It is normally available after a couple of attempts, so
    # adding this workaround for now.
    count = 0
    while not stage and count < 100:
        count += 1
        stage = node.stage()
        logger.debug("Attempt {count} to load stage.".format(count=count))

    if stage:
        logger.info("Stage loaded after {count} attempts.".format(count=count))
    else:
        logger.warning("Stage cannot be loaded. Check the Houdini Update Mode")
        return False

    return True


def is_implicit_ref(path):
    """
    Check if the given path is a Houdini implicit asset reference.

    Args:
        path(str): The path we want to check.

    Returns:
        (bool): Is the path an implicit reference.
    """
    return path.startswith("op:")


def get_references(node_path):
    """Get any external references for the USD stage based on the given node.

    Args:
        node_path(str): The Houdini scene path to the node we want to inspect.

    Returns:
        external_references(list): A list of any external references in the USD
        stage.
    """
    if not stage_available(node_path):
        return []

    node = nodes.node_at_path(node_path)
    stage = node.stage()
    root = stage.GetRootLayer()

    external_references = []

    for i in root.subLayerPaths:
        layer = root.Find(i)
        external = layer.externalReferences
        if external:
            external_references.extend(layer.externalReferences)

    external_references.sort()
    return external_references


def implicit_references(node_path, external_references=None):
    """Get any implicit references for the USD stage based on the given node.

    Args:
        node_path(str): The Houdini scene path to the node we want to inspect.
        external_references(list): A list of references to use. Otherwise the
            references will be generated for the given node, before being
            filtered into implicit references.

    Returns:
        implicit(list): A list of any implicit references in the USD stage.
    """
    if external_references is None:
        external_references = get_references(node_path)

    if not external_references:
        logger.info(
            "No external references found for {node_path}".format(
                node_path=node_path,
            )
        )
        return []

    implicit = [ref for ref in external_references if is_implicit_ref(ref)]

    return implicit


def file_references(node_path, external_references=None):
    """Get any file references for the USD stage based on the given node.

    Args:
        node_path(str): The Houdini scene path to the node we want to inspect.
        external_references(list): A list of references to use. Otherwise the
            references will be generated for the given node, before being
            filtered into implicit references.

    Returns:
        file_refs(list): A list of any file references in the USD stage.
    """
    if external_references is None:
        external_references = get_references(node_path)

    if not external_references:
        logger.info(
            "No external references found for {node_path}".format(
                node_path=node_path,
            )
        )
        return []

    file_refs = [
        ref
        for ref in external_references
        if not ar.is_asset_ref(ref) and not is_implicit_ref(ref)
    ]

    return file_refs


def turret_references(node_path, external_references=None):
    """Get any turret references for the USD stage based on the given node.

    Args:
        node_path(str): The Houdini scene path to the node we want to inspect.
        external_references(list): A list of references to use. Otherwise the
            references will be generated for the given node, before being
            filtered into implicit references.

    Returns:
        turret_refs(list): A list of any Turret references in the USD stage.
    """
    if external_references is None:
        external_references = get_references(node_path)

    if not external_references:
        logger.info(
            "No external references found for {node_path}".format(
                node_path=node_path,
            )
        )
        return []

    turret_refs = [ref for ref in external_references if ar.is_asset_ref(ref)]

    return turret_refs


def display_usd_filepaths(node_path, prim_path):
    """Display the USD filepaths for the given node_path and usd prim_path.

    Args:
        node_path(str): The Houdini scene path to the node we want to inspect.
        prim_path(str): The USD Scene graph path to the prim that we want to
            inspect.

    Returns:
        None
    """
    # Check we can actually access the stage
    if not stage_available(node_path):
        dialog.display_message(
            "Stage is not available.",
            title="USD Path Inspector",
            severity=hou.severityType.Error,
        )
        return

    # Access the usd stage and get the prim stack
    node = nodes.node_at_path(node_path)
    stage = node.stage()
    prim = stage.GetPrimAtPath(prim_path)
    prim_stack = prim.GetPrimStack()

    msg = []
    for ps in prim_stack:
        if ps.layer.realPath:
            msg.append(
                "File Path: {path}".format(
                    path=ps.layer.realPath,
                )
            )

    # Remove any duplicates
    msg = list(set(msg))

    if msg:
        msg.insert(
            0,
            "The following USD file information was found from the selected \
                prim path {path}:\n".format(
                path=prim_path
            ),
        )
    else:
        msg.insert(
            0,
            "No USD file information could be found for the selected \
                path ({path})".format(
                path=prim_path
            ),
        )

    full_msg = "\n".join(msg)
    dialog.display_message(
        full_msg,
        title="USD Path Inspector",
    )


def __get_layer_paths(node_path, usd_path):
    """Evaluate the USD stage at the given node path for any layer save paths.

    Houdini writes metadata about the save paths for layers under
    /HoudiniLayerInfo, so we can read this and assemble a list of paths that
    will be written to by the stage.

    Args:
        node_path(str): The Houdini scene path to the LOP node we want to
            inspect.
        usd_path(str): The file path to the USD file that is being written.

    Returns:
        unique_save_paths(list): A list of any file paths that will be written
            to for the given stage.

    Raises:
        RuntimeError: Unexpected character found in node name.
    """
    # Check we can actually access the stage
    if not stage_available(node_path):
        dialog.display_message(
            "Stage is not available.",
            severity=hou.severityType.Error,
        )
        return

    # Access the usd stage and get the layer stack
    node = nodes.node_at_path(node_path)
    stage = node.stage()
    session_layer = stage.GetSessionLayer()

    save_paths = []

    for layer in session_layer.GetLoadedLayers():
        # We ae only interested in layers that have the /HoudiniLayerInfo prim
        layer_info = layer.GetPrimAtPath("/HoudiniLayerInfo")
        if layer_info and layer_info.customData:
            save_control = layer_info.customData.get("HoudiniSaveControl")
            save_path = layer_info.customData.get("HoudiniSavePath")
            creator_node = layer_info.customData.get("HoudiniCreatorNode")
            editor_nodes = layer_info.customData.get("HoudiniEditorNodes")

            logger.debug("Save Control: {a}".format(a=save_control))
            logger.debug("Save Path: {a}".format(a=save_path))
            logger.debug("Creator Node: {a}".format(a=creator_node))
            logger.debug("Editor Nodes: {a}".format(a=editor_nodes))

            if save_control == "Explicit":
                path_record = {}
                if save_path:
                    path_record["path"] = save_path
                    path_record["type"] = "explicit"
                else:
                    if not creator_node.startswith("/"):
                        raise RuntimeError(
                            "Creator node starts with unexpected \
                                character: {node}".format(
                                node=creator_node,
                            )
                        )
                    creator_node_usd = "{node}.usd".format(
                        node=creator_node[1:],
                    )
                    usd_dir = os.path.dirname(usd_path)
                    path_record["path"] = os.path.join(
                        usd_dir,
                        creator_node_usd,
                    )
                    path_record["type"] = "implicit"

                save_paths.append(path_record)

    # Make sure all paths are unique
    unique_save_paths = []
    for path in save_paths:
        all_paths = [unique_path.get("path") for unique_path in unique_save_paths]
        if path.get("path") not in all_paths:
            unique_save_paths.append(path)

    return unique_save_paths


def includes_implicit_layer_paths(node_path, usd_path):
    """
    Check if any implicit layers will be authored for the given node path.

    Args:
        node_path(str): The Houdini scene path to the LOP node we want to
            inspect.
        usd_path(str): The file path to the USD file that is being written.

    Returns:
            bool: Are there any implicit layers.
    """
    if get_implicit_layer_paths(node_path, usd_path):
        return True

    return False


def get_explicit_layer_paths(node_path, usd_path):
    """
    Get all of the explicit layer paths for the given node path.

    Args:
        node_path(str): The Houdini scene path to the LOP node we want to
            inspect.
        usd_path(str): The file path to the USD file that is being written.

    Returns:
        layer_paths(list): A list of any explicit file paths that will be
        written to for the given stage.
    """
    return [
        path.get("path")
        for path in __get_layer_paths(node_path, usd_path)
        if path.get("type") == "explicit"
    ]


def get_implicit_layer_paths(node_path, usd_path):
    """
    Get all of the implicit layer paths for the given node path.

    Args:
        node_path(str): The Houdini scene path to the LOP node we want to
            inspect.
        usd_path(str): The file path to the USD file that is being written.

    Returns:
        layer_paths(list): A list of any explicit file paths that will be
        written to for the given stage.
    """
    return [
        path.get("path")
        for path in __get_layer_paths(node_path, usd_path)
        if path.get("type") == "implicit"
    ]


def create_usd_directories(node_path, usd_path):
    """
    Create all directories required for a usd write.

    Args:
        node_path(str): The Houdini scene path to the LOP node we want to
            create directories based upon.
        usd_path(str): The filepath to the main USD file being written.
    """
    # Check we can actually access the stage
    if not stage_available(node_path):
        dialog.display_message(
            "Stage is not available.",
            severity=hou.severityType.Error,
        )
        return

    usd_dirs = []

    # Always include the master usd itself
    usd_dir = os.path.dirname(usd_path)
    usd_dirs.append(usd_dir)

    # Add any explicit render USDs
    layer_paths = __get_layer_paths(node_path, usd_path)

    usd_dirs.extend(
        [os.path.dirname(layer_path.get("path")) for layer_path in layer_paths]
    )

    # Remove any duplicates
    usd_dirs = list(set(usd_dirs))

    # Make sure all directories are created with the correct permissions
    for dir in usd_dirs:
        filesystem.create_directory(dir)


def get_render_output_paths(
    node_path,
    render_settings_path,
    override_image_path=None,
):
    """
    Get the output paths for a given usd render.

    Args:
        node_path(str): The Houdini scene path to the LOP node we want to get
            the output paths based upon.
        render_settings_path(str): The path to the render settings for the
            render we want to get output paths for.
        override_image_path(str): The image path if overriden directly outside
            the render settings (ie. through husk).

    Returns:
        list: A list of render image paths.
    """
    if override_image_path:
        return [override_image_path]

    # Check we can actually access the stage
    if not stage_available(node_path):
        dialog.display_message(
            "Stage is not available.",
            severity=hou.severityType.Error,
        )
        return []

    # Access the usd stage
    node = nodes.node_at_path(node_path)
    stage = node.stage()

    return rendersettings.get_output_paths(
        stage,
        render_settings_path,
        frame=hou.frame(),
    )


def create_render_directories(
    node_path,
    render_settings_path,
    override_image_path=None,
):
    """
    Create all directories required for a usd render.

    Args:
        node_path(str): The Houdini scene path to the LOP node we want to
            create directories based upon.
        render_settings_path(str): The path to the render settings for the
            render we want to create output paths for.
        override_image_path(str): The image path if overriden directly outside
            the render settings (ie. through husk).
    """
    render_paths = get_render_output_paths(
        node_path,
        render_settings_path,
        override_image_path=override_image_path,
    )

    for path in render_paths:
        dir_name = os.path.dirname(path)
        if dir_name:
            filesystem.create_directory(dir_name)
        else:
            logger.warning(
                "Skipping invalid directory: {dirname}".format(
                    dirname=dir_name,
                )
            )
