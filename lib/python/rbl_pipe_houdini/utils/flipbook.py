#!/usr/bin/env python

"""Flipbook tools."""

import glob
import logging
import os
import subprocess
import time

import hou

from rbl_pipe_houdini.utils import get_config

import toolutils


logger = logging.getLogger(__name__)


class Flipbook(object):
    """Define the flipbook object."""

    def __init__(self):
        """Set the default values."""
        # Set default values
        self.frame_range = hou.playbar.frameRange()
        self.hip_path = hou.getenv("HIP")
        self.resolution = (1920, 1080)
        self.folder = "flipbook"

        # Setup
        self.filename = "default"
        self.version = 1

        # Run the updates
        self.update_viewer()
        self.update_viewport()
        self.update_output_path()

        self.update_flipbook_settings()

    def update_viewer(self):
        """Update based on the current scene."""
        self.viewer = toolutils.sceneViewer()

    def update_viewport(self):
        """Update based on the current viewport."""
        self.current_viewport = self.viewer.curViewport()

    def update_output_path(self):
        """Update the output path."""
        file_version = "{filename}_v{version:03d}".format(
            filename=self.filename, version=self.version
        )
        self.output_root = os.path.join(self.hip_path, self.folder, file_version)
        self.output_path = "{root}/{name}.$F4.jpg".format(
            root=self.output_root, name=file_version
        )

    def update_flipbook_settings(self):
        """Update the settings."""
        flipbook_settings = self.viewer.flipbookSettings().stash()
        flipbook_settings.frameRange(self.frame_range)
        flipbook_settings.resolution(self.resolution)
        flipbook_settings.output(self.output_path)
        flipbook_settings.outputToMPlay(False)

        self.flipbook_settings = flipbook_settings

    def run(self):
        """Run the flipbook."""
        # Make sure all settings are latest
        self.update_flipbook_settings()
        self.update_viewport()

        # Validate where to save
        self.validation()

        # Saves a backup if enabled
        self.save_backup()

        # Run the flipbook to save out
        self.viewer.flipbook(self.current_viewport, self.flipbook_settings)

        # Opens the flipbook in rv if enabled
        self.launch_rv()

        # Prints out the save file
        logger.info("Saving flipbook to: {path}".format(path=self.output_path))

    def validation(self):
        """Validate the save location, to make sure we don't overwrite anything.

        Raises:
            Warning: There are no ripbook files in the folder.
        """
        # Default value
        exists = False

        # Check if anything exists ##

        # Check if folder exists
        if not os.path.exists(self.output_root):
            os.makedirs(self.output_root)
            os.chmod(self.output_root, 0o770)
        else:

            # Finds all files if they exist
            files = glob.glob("{dir}/*.jpg".format(dir=self.output_root))

            # Check if any files in the folder
            if len(files) > 0:

                # Get the frame numbers, presumes they're written out in file.$F4.jpg
                # format.
                try:
                    frames = [int(x.split(".")[-2]) for x in files]
                except IndexError:
                    raise Warning("There are non ripbook files in your folder")

                # Check if any files match the frame range
                for f in range(self.frame_range[0], self.frame_range[1]):
                    if f in frames:
                        exists = True

        # If the files already exist, checks if you want to overwrite them
        if exists:
            if not (
                hou.ui.displayConfirmation(
                    "This flipbook version already exists, do you want to overwrite it?"
                )
            ):
                hou.ui.displayMessage(
                    "The latest version is {vers}, please choose a higher one".format(
                        vers=self.max_version()
                    )
                )
                raise Warning("This version didn't want to be overwritten")

    def save_backup(self):
        """Save a backup file in the flipbook directory.

        Returns:
            (str): The filepath that was saved to.

        Raises:
            Warning: Houdini session is not saved.
        """
        # Check if the ui has set to save
        if not self.save:
            return None

        # Exit if session is not saved
        if hou.hipFile.hasUnsavedChanges():
            hou.ui.displayMessage(
                "Please save your hip file if you want to create a backup"
            )
            raise Warning("Houdini session is not saved")
        # Get current filepath
        og_file = hou.hipFile.path()

        # Define filepath
        hip_filename = "{root}/hip/{hipname}_{time}.hip".format(
            root=self.output_root,
            hipname=hou.text.expandString("$HIPNAME"),
            time=time.strftime("%Y%m%d%H%M%S"),
        )

        # Check to see it exists before saving
        if os.path.isfile(hip_filename):
            if hou.ui.displayConfirmation(
                "That hip file already exists, do you want to overwrite it?"
            ):
                hou.hipFile.save(file_name=hip_filename, save_to_recent_files=False)

        # Return filename to original
        hou.hipFile.setName(og_file)

        return hip_filename

    def max_version(self):
        """Calculate the current max version based on the folders.

        Returns:
            (int): The maximum version.
        """
        versions = glob.glob("{path}*".format(path=self.output_root.rsplit("_", 1)[0]))
        versions = [int(x.split("_")[-1][1:]) for x in versions]
        return max(versions)

    def update_from_ui(self, **kwargs):
        """Update the values from the current ui settings.

        Args:
            **kwargs: Arbitrary keyword arguments.
        """
        # Loops through and sets the values
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Update the path from the new values
        self.update_output_path()

    def launch_rv(self, force=False):
        """RV from the current filepath.

        Args:
            force(:obj:bool, optional): Force RV to open.

        Returns:
            (None)
        """
        # Checks to see if we run rv
        if not self.openrv or force:
            return None

        # Gets the rv path
        path = self.output_path.replace("$F4", "####")

        # Run rv
        config = get_config()
        rv_bin = config.get("flipbook_rv_bin")
        arg_str = "{} {}".format(rv_bin, path)
        subprocess.Popen(arg_str, shell=True)

    # Upload the flipbook to shotgun
    def submit(self, comment="Default", path=None):
        """Fake the publish using slate.

        Would be better if we could do it without going through slate, but works for
        now.

        Args:
            comment(:obj:`str`, optional): The comment to use when publishing.
            path(:obj:`str`, optional): The path to publish to.
        """
        # Check if we want to overwrite the path
        if path is None:
            path = self.output_path

        # Create nodes to upload
        node = hou.node("/obj")
        ropnet = node.createNode("ropnet")
        slate = ropnet.createNode("slate")
        dispatcher = slate.createOutputNode("dispatcher")

        # Disconnect parms
        slate.parm("f1").deleteAllKeyframes()
        slate.parm("f2").deleteAllKeyframes()

        # Set values on slate
        parm_dict = {
            "image_sequence": path,
            "comment": comment,
            "f1": self.frame_range[0],
            "f2": self.frame_range[1],
        }

        slate.setParms(parm_dict)

        # Set dispatcher settings
        dispatcher.setParms({"job_name": "`$HIPNAME`_Flipbook"})

        logger.info(
            "Submitting: {path} Comment: {comment}".format(
                path=path, comment=comment
            )
        )

        # Run and destroy ropnet
        dispatcher.parm("submit").pressButton()
        ropnet.destroy()

    def get_path(self):
        """Update and grab the path.

        Returns:
            (str): The output path.
        """
        self.update_from_ui()
        return self.output_path

    def update(self):
        """Update the environment, called on re-open."""
        self.hip_path = hou.getenv("HIP")


def run_flipbook():
    """Start the flipbook tool."""
    flipbook = Flipbook()
    flipbook.run()
