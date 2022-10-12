#!/usr/bin/env python

import os

from rbl_pipe_core.util import config


def get_config():
    """Load config file for this repository.

    Returns:
        (rbl_pipe_core.util.config.Config): The config object for the repository.
    """
    basedir = os.path.abspath(__file__).rsplit("/lib/python", 1)[0]
    config_file = os.path.join(basedir, "config", "rbl_pipe_houdini.json")
    return config.ConfigRepo.get(config_file)
