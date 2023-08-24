#!/usr/bin/env python

"""Houdini Pyblish UI."""

import hou

from rbl_pipe_core.pyblish import pyblishui


class HoudiniPyblishUI(pyblishui.PyblishUI):
    """Houdini Pyblish UI."""

    def __init__(self, title="Houdini Pyblish", size=None, position=None):
        """Initialise the Houdini Pyblish UI.

        Args:
            title(str): The window title to use for the pyblish UI.
            size(:obj:`tuple` of :obj:`int`, :obj:`int`): The size of the pyblish UI.
            position(:obj:`tuple` of :obj:`int`, :obj:`int`): The position of the
                pyblish UI. If unset, we will attempt to centre the UI around the mouse
                cursor.
        """
        if not position:
            position = self.__get_window_pos(size)

        super(HoudiniPyblishUI, self).__init__(
            title=title,
            size=size,
            position=position,
        )

    def __get_window_pos(self, size):
        """Determine the window position for the UI.

        Args:
            size(:obj:`tuple` of :obj:`int`, :obj:`int`): The size of the pyblish UI.

        Returns:
            (:obj:`tuple` of :obj:`int`, :obj:`int`): Window coordinates.
        """
        cursor = self.__get_cursor_pos()
        if size:
            width, height = size
            x_pos = cursor[0] - (width / 2)
            y_pos = cursor[1] - (height / 2)
            if x_pos < 0:
                x_pos = 0
            if y_pos < 0:
                y_pos = 0
            return (x_pos, y_pos)
        else:
            return cursor

    def __get_cursor_pos(self):
        """Get the cursor position from the Houdini UI.

        Returns:
            (:obj:`tuple` of :obj:`int`, :obj:`int`): Cursur coordinates.
        """
        hou_win = hou.ui.mainQtWindow()
        cursor_pos = hou_win.cursor().pos()
        return (cursor_pos.x(), cursor_pos.y())
