#!/usr/bin/env python

"""SG node menu."""

import logging

from rbl_pipe_houdini.menu import nodemenu

logger = logging.getLogger(__name__)


class SGMenu(nodemenu.HoudiniHDAMenu):
    """Class to handle node menus generated from SG data."""

    def __init__(self, sg_context, parm):
        """
        Initialise the SG menu for the given context and parm.

        Args:
            sg_context(rbl.pipe.houdini.shotgun.context): The current context.
            parm(hou.Parm): The parm to base the menu around.
        """
        self.sg_context = sg_context
        super(SGMenu, self).__init__(parm)

    def get_selection(self, force=False):
        """Get the selection from the menu.

        Args:
            force(:obj:`bool`, optional): Should a forced update from SG be performed.

        Returns:
            The selection from the menu.
        """
        overriden = self.is_overriden()
        selection = self.sg_context.parm_value_from_context(self.parm.name())

        if force and selection:
            return str(selection)
        elif not overriden and selection:
            return str(selection)
        else:
            return super(SGMenu, self).get_selection()

    def is_overriden(self):
        """Check if the context is overriden for this parm.

        Returns:
            (bool): Is the parm context overriden.
        """
        if self.override_parm:
            if self.override_parm.eval() == 1:
                return True
            else:
                return False
        elif self.sg_context.legacy_auto_mode():
            return False
        else:
            return True
