#!/usr/bin/env python

"""Class to handle Houdini HDA parm menus."""

import logging

logger = logging.getLogger(__name__)


class HoudiniHDAMenu(object):
    """Simple HDA menu class that uses a dictionary as its source."""

    def __init__(self, parm):
        """Initialise the menu class for the given parm.

        Args:
            parm(hou.Parm): The parameter to initialise the menu for.
        """
        self.parm = parm
        self.node = self.parm.node()
        self.override_parm = self.__get_override_parm()
        self.menu = []
        self.value = None

    def __get_override_parm(self):
        """Get the override parm (if one exists) for the current menu.

        Returns:
            (hou.Parm): The override parm for the current menu.
        """
        override_parm_name = "override_{parm}".format(parm=self.parm.name())
        return self.parm.node().parm(override_parm_name)

    def is_overriden(self):
        """Check if this menu instance is overriden.

        Returns:
            (bool): Is the current menu overriden.
        """
        if self.override_parm:
            if self.override_parm.eval() == 1:
                return True
            else:
                return False
        return True

    def get_menu(self):
        """Get the menu list for the current instance.

        Returns:
            self.menu(list): The current menu list.
        """
        return self.menu

    def generate_menu(self, data_dicts, name, label, reverse=False, force=False):
        """Generate the menu items.

        Given a dictionary of data build a menu using the specified keys for name and
        label.

        Args:
            data_dicts(list): A list of dictionaries used to generate the menu.
            name(str): Name of the key within the dictionary used for the name part of
                the menu.
            label(str): Name of the key within the dictionary used for the label part of
                the menu.
            reverse(:obj:`bool`, optional): Should the order of the data/menu be
                reversed.
            force(:obj:`bool`, optional): Force data to be loaded from SG.
        """
        selection = self.get_selection(force=force)
        editable = self.node.isEditableInsideLockedHDA()

        if not editable:
            if selection:
                data_dicts = [
                    item for item in data_dicts if str(item.get(name)) == selection
                ]
            else:
                data_dicts = [data_dicts[0]]

        if reverse:
            data_dicts = reversed(data_dicts)

        self.menu = []
        for item in data_dicts:
            self.menu.append(str(item.get(name)))
            self.menu.append(str(item.get(label)))

        if selection in self.menu[::2]:
            self.set_value(str(selection))
        elif self.menu:
            self.set_value(str(self.menu[0]))

        # Refresh the UI - can't use nodes.force_ui_refresh / pressButton as that forces
        # cascading menu callbacks to be run.
        current = self.parm.isShowingExpression()
        self.parm.showExpression(current)

    def get_selection(self):
        """Get the selection from the menu.

        Returns:
            (str) The selection from the menu.
        """
        if self.parm:
            selection = self.parm.eval()
        else:
            logger.warning("Menu {parm} doesn't exist".format(parm=self.parm))
            return None

        if selection and selection != "None":
            return selection
        elif self.menu:
            return self.menu[0]
        else:
            return None

    def set_value(self, value):
        """Set the value for the menu.

        If it is editable we set the parm value, but we always maintain the value
        parameter in this class.

        Args:
            value: The value to set.
        """
        self.value = value
        if self.parm.node().isEditableInsideLockedHDA():
            self.parm.set(str(self.value))
        else:
            logger.info("Cannot set value as node is not editable.")
