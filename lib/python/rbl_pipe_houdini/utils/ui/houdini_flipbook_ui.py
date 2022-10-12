#!/usr/bin/env python

"""Flipbook UI code."""

import logging

from PySide2 import QtCore
from PySide2.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import hou

from rbl_pipe_houdini.utils import flipbook


logger = logging.getLogger(__name__)


class FlipbookUI(QWidget):
    """Create's the UI for flipbooks."""

    def __init__(self, parent=None):
        """Initialise the Flipbook Class.

        Args:
            parent: The window to parent the Flipbook UI to.
        """
        QWidget.__init__(self, parent, QtCore.Qt.WindowStaysOnTopHint)

        # Sets up the UI
        self.setup_ui()

        # Try to keep it on top
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        # Setups up the flipbook class
        self.flipbook = flipbook.Flipbook()

        # Updates the output path
        self.update_path()

    def setup_ui(self):
        """Set up the ui."""
        # ---------- Setup Window ----------
        outer_lyt = QVBoxLayout()

        self.setWindowTitle("Ripbook")
        self.setGeometry(480, 300, 400, 110)  # x, y, width, height - position on screen
        self.setMinimumSize(720, 160)

        # ---------- Description ----------

        self.description_lay = QHBoxLayout()

        # Description label
        self.label = QLabel("Use this to run and submit a Flipbook", self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.description_separator = self.create_hseparator()

        self.description_lay.addWidget(self.label)

        # ---------- Frame Range ----------

        self.frame_range_row = QHBoxLayout()

        # Start Frame
        self.start_lbl = QLabel("Frame Range:")
        self.start_frame = QLineEdit(hou.text.expandString("$FSTART"))
        self.start_frame.setInputMask("####")
        self.start_frame.setFixedWidth(40)

        # Start Frame
        self.end_frame = QLineEdit(hou.text.expandString("$FEND"))
        self.end_frame.setInputMask("####")
        self.end_frame.setFixedWidth(40)

        # Add to layout
        self.frame_range_row.addWidget(self.start_lbl)
        self.frame_range_row.addWidget(self.start_frame)
        self.frame_range_row.addWidget(self.end_frame)

        # ---------- Resolution ----------

        # Resolution X
        self.resx_lbl = QLabel("  Resolution:")
        self.resx = QLineEdit("1920")
        self.resx.setInputMask("####")
        self.resx.setFixedWidth(40)

        # Resolution Y
        self.resy = QLineEdit("1080")
        self.resy.setInputMask("####")
        self.resy.setFixedWidth(40)

        # Add to layout
        self.frame_range_row.addWidget(self.resx_lbl)
        self.frame_range_row.addWidget(self.resx)
        self.frame_range_row.addWidget(self.resy)

        # ---------- Variant ----------

        self.variant_lbl = QLabel("  Name:")
        self.filename = QLineEdit(self.get_task())
        self.filename.setMaximumWidth(250)
        self.filename.editingFinished.connect(self.update_ui)

        self.version_lbl = QLabel("  Version:")
        self.version = QLineEdit("1")
        self.version.setInputMask("##")
        self.version.setFixedWidth(60)
        self.version.editingFinished.connect(self.update_ui)

        self.frame_range_row.addWidget(self.version_lbl)
        self.frame_range_row.addWidget(self.version)
        self.frame_range_row.addWidget(self.variant_lbl)
        self.frame_range_row.addWidget(self.filename)

        # ---------- Path ----------

        self.path_lay = QHBoxLayout()

        self.button_separator = self.create_hseparator()

        self.path = QLabel("path")
        self.path.setAlignment(QtCore.Qt.AlignCenter)

        self.path_lay.addWidget(self.path)

        self.path_bottom_separator = self.create_hseparator()

        # ---------- Flipbook Functions ----------

        self.functions_lay = QHBoxLayout()

        # Set up running the flipbook
        self.btn_run = QPushButton("Run Flipbook", self)
        self.btn_run.clicked.connect(self.run_flipbook)

        self.cbox_hip_save = QCheckBox("Backup")
        self.cbox_hip_save.setChecked(True)
        self.cbox_hip_save.setStyleSheet(
            "QCheckBox"
            "{"
            "border : 0px solid black;"
            "margin-left:5px;"
            "margin-right:0px;"
            "}"
        )

        self.cbox_rv = QCheckBox("RV")
        self.cbox_rv.setChecked(True)
        self.cbox_rv.setStyleSheet(
            "QCheckBox"
            "{"
            "border : 0px solid black;"
            "margin-left:5px;"
            "margin-right:0px;"
            "}"
        )

        self.btn_copy = QPushButton("Copy Path", self)
        self.btn_copy.clicked.connect(self.copy_path)

        # Set up flipbook submission
        self.btn_upload = QPushButton("Upload Flipbook", self)
        self.btn_upload.clicked.connect(self.upload_flipbook)

        self.btn_rv = QPushButton("RV", self)
        self.btn_rv.clicked.connect(self.rv)

        self.vert_separator = self.create_vseparator()

        self.upload_label = QLabel("Comment:")
        self.upload_comment = QLineEdit("My cool flipbook")

        self.functions_lay.addWidget(self.btn_run)
        self.functions_lay.addWidget(self.cbox_hip_save)
        self.functions_lay.addWidget(self.cbox_rv)
        self.functions_lay.addWidget(self.btn_copy)
        self.functions_lay.addWidget(self.btn_rv)
        self.functions_lay.addWidget(self.vert_separator)
        self.functions_lay.addWidget(self.btn_upload)
        self.functions_lay.addWidget(self.upload_label)
        self.functions_lay.addWidget(self.upload_comment)

        # ---------- Building the UI ----------

        outer_lyt.addLayout(self.description_lay)
        outer_lyt.addWidget(self.description_separator)
        outer_lyt.addLayout(self.frame_range_row)
        outer_lyt.addWidget(self.button_separator)
        outer_lyt.addLayout(self.path_lay)
        outer_lyt.addWidget(self.path_bottom_separator)
        outer_lyt.addLayout(self.functions_lay)

        self.setLayout(outer_lyt)

    def create_hseparator(self):
        """Create a horizontal separator.

        Returns:
            (QFrame): A horizontal separator.
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Raised)
        return separator

    def create_vseparator(self):
        """Create a vertical separator.

        Returns:
            (QFrame): A vertical separator.
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Raised)
        return separator

    def run_flipbook(self):
        """Run the flipbook."""
        # Updates from the UI
        self.update_ui()

        # Run the flipbook
        self.flipbook.run()

        # Raise the window to the top again
        self.raise_()

    def copy_path(self):
        """Copy the image path to the clipboard."""
        # Assigns text to clipboard
        path = self.path.text().replace("$F4", "####")
        QApplication.clipboard().setText(path)
        logger.info("Setting the clipboard to: {path}".format(path=path))

    def update_path(self):
        """Update the path."""
        self.path.setText(self.flipbook.get_path())

    def update_ui(self):
        """Update the flipbook module with the data from the ui."""
        # Grab frame range
        frame_range = [int(self.start_frame.text()), int(self.end_frame.text())]

        # Update the values from UI
        self.flipbook.update_from_ui(
            frame_range=frame_range,
            version=int(self.version.text()),
            filename=self.filename.text(),
            save=self.cbox_hip_save.isChecked(),
            openrv=self.cbox_rv.isChecked(),
            resolution=((int(self.resx.text()), int(self.resy.text()))),
        )

        self.update_path()

    def rv(self):
        """Run rv on the output sequence."""
        self.update_ui()
        self.flipbook.launch_rv(force=True)

    def upload_flipbook(self):
        """Upload the flipbook to shotgun."""
        self.flipbook.submit(comment=self.upload_comment.text())
        self.close_event()

    def close_event(self):
        """Unparent it when the UI is closed."""
        self.setParent(None)
        self.close()

    def get_task(self):
        """Get the task from the filename.

        Returns:
            (str): The task name.
        """
        try:
            path = hou.hipFile.path()
            split = path.split("/")[-1].split("_")
            task = "_".join([split[-3], split[-2]])
            return task
        except IndexError:
            return "default"

    def open_event(self):
        """Handle the open event."""
        self.flipbook.update()


def run():
    """Run the UI."""
    # Storing the dialog in hou.session so it doesn't get cleaned up
    if not hasattr(hou.session, "dialog"):
        hou.session.dialog = FlipbookUI()
        hou.session.dialog.setParent(hou.qt.mainWindow(), QtCore.Qt.Window)
    hou.session.dialog.show()
    hou.session.dialog.update_ui()
    hou.session.dialog.open_event()
    hou.session.dialog.raise_()
