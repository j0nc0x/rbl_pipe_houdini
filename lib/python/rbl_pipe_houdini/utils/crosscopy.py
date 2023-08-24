#!/usr/bin/env python

"""Cross copies nodes from current scene to library."""

import getpass
import json
import logging
import os
import time

import hou

from rbl_pipe_core.util import filesystem
from rbl_pipe_core.util import get_project

from rbl_pipe_houdini.utils import dialog
from rbl_pipe_houdini.utils import get_config

# Logger
logger = logging.getLogger(__name__)

# Username
user = getpass.getuser()

# Project
show = get_project()


def get_category_library_path(category, show):
    """
    Get the path for a specific library.

    Args:
        category(str): The node type category
        show(str): Project code

    Returns:
        category(str): The path on disk to the library category

    """
    config = get_config()
    sg_root = config.get("cross_copy_root")
    library_location = "code/houdini/pastebin"
    path = os.path.join(sg_root, show, library_location, category)
    ensure_dir(path)
    return path


def get_cpio_path(user, category, show):
    """
    Create the path to write the copied items too.

    Args:
        user(str): The username
        category(str): The node type category
        show(str): Project name

    Returns:
        path(str): The path to save the cpio file too

    """
    cat_library = get_category_library_path(category, show)
    filename = "{}_{}_{}.cpio".format(user, time.strftime("%Y%m%d_%H%M%S"), category)
    path = os.path.join(cat_library, user, filename)
    return path


def get_child_category(node):
    """Get category of the node.

    Args:
        node(hou.Node): The houdini node

    Returns:
        child_category(str): The node category
    """
    child_category = node.childTypeCategory().name()
    return child_category


def ensure_dir(filepath):
    """Create directory if it doesn't exist.

    Args:
        filepath(str): Directory filepath
    """
    directory = os.path.dirname(filepath)
    filesystem.create_directory(directory)


def get_category_json(category, show):
    """Get the filepath for each library.

    Args:
        category(str): Node category.
        show(str): Project name

    Returns:
        json_filepath(str): Filepath of json library path
    """
    json_filepath = os.path.join(
        get_category_library_path(category, show), "{}.json".format(category)
    )
    if os.path.exists(json_filepath):
        return json_filepath
    else:
        write_json_dictionary({}, json_filepath)
        return json_filepath


def write_json_dictionary(dictionary, filepath):
    """Write out the dictionary to a json file.

    Args:
        dictionary(dict): The different files in the library
        filepath(str): Filepath to write dictionary too

    Raises:
        RuntimeError: If writing the json fails
    """
    ensure_dir(filepath)

    old_mask = os.umask(0o007)
    try:
        with open(filepath, "w") as fp:
            json.dump(dictionary, fp, sort_keys=True, indent=4)
    except Exception as e:
        message = "ERROR: Failed to create json: '{}': {}".format(
            filepath,
            e,
        )
        raise RuntimeError(message)
    else:
        logger.info("Directory created: {path}".format(path=filepath))
    finally:
        os.umask(old_mask)


def read_json_dictionary(filepath):
    """Extract the dictionary from a json file.

    Args:
        filepath(str): Filepath of the json file.

    Returns:
        d(dict): Dictionary from json file
    """
    with open(filepath) as fh:
        jsondata = fh.read()

    return json.loads(jsondata)


def write_json(cpio_filepath, user, time, description, category):
    """
    Format the dictionary and writing it to json.

    Args:
        cpio_filepath(str): Path of cpio file
        user(str): Username
        time(str): String formatted time
        description(str): User description for copy
        category(str): Parent node category
    """
    json_filepath = get_category_json(category, show)

    copy_dict = {}

    if json_filepath:
        copy_dict = read_json_dictionary(json_filepath)

    copy_dict[cpio_filepath] = {
        "user": user,
        "time": time,
        "description": description,
        "show": show,
    }

    write_json_dictionary(copy_dict, json_filepath)


def copy_nodes(path=None):
    """Copy nodes to cpio file on disk in library.

    Args:
        path(str): The location to save the nodes too

    Raises:
        Warning: If  no nodes are selected

    """
    # Get selected node and parent
    nodes = hou.selectedNodes()
    if len(nodes) < 1:
        raise Warning("Please select some nodes")
    parent_node = nodes[0].parent()

    category = get_child_category(parent_node)

    if not path:
        path = get_cpio_path(user, category, show)

    ensure_dir(path)

    ui_input = hou.ui.readInput("What has been copied?")

    # Save the cpio file from houdini
    parent_node.saveItemsToFile(nodes, path)

    # Update the json file with the new filepath
    write_json(path, user, time.strftime("%Y%m%d_%H%M%S"), ui_input[1], category)

    # Print out the nodes we copies
    names = [x.name() for x in nodes]
    message = "Saved these nodes {}".format(names)
    dialog.display_message(message)


def paste_nodes():
    """Cross paste nodes from cpio file on disk.

    Raises:
        Warning: When no library exists for current category
    """
    # Find the network editor pane and it's parent node
    pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    parent_node = pane.pwd()

    category = get_child_category(parent_node)

    json_filepath = get_category_json(category, show)

    if not json_filepath:
        raise Warning("There is not library for {}".format(category))

    dictionary = read_json_dictionary(json_filepath)

    if len(dictionary) == 0:
        raise Warning("There are no saved clips for {}".format(category))

    keys = list(dictionary.keys())

    names = []

    for key in keys:
        d = dictionary[key]
        t = time.strftime(
            "%b %d %Y - %H:%M:%S", time.strptime(d["time"], "%Y%m%d_%H%M%S")
        )
        names.append(" | ".join([d["user"], t, d["description"]]))

    choices = hou.ui.selectFromList(names)

    bounds = pane.visibleBounds()

    for c in choices:
        path = keys[c]

        # Load items in
        c1 = parent_node.children()
        parent_node.loadItemsFromFile(path)
        c2 = parent_node.children()

        # Calculate the new nodes
        new_children = list(set(c2) - set(c1))

        # Calculate offset
        offset = bounds.center() - new_children[0].position()

        # Offset to centre of the pane
        for n in new_children:
            n.move(offset)

        # Log the file we pasted from
        logger.info("Loaded nodes from {}".format(path))

        # Display the new nodes
        nodes = hou.selectedNodes()
        names = [x.name() for x in nodes]
        dialog.display_message("Loaded these nodes {}".format(names))
