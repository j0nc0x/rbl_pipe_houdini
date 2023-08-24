name = "rbl_pipe_houdini"

version = "2.1.0"

authors = [
    "Jonathan Cox",
    "Gary Nisbet",
]

requires = [
    "~houdini-19+",
    "rbl_pipe_python_extras-1.4+<2",
    "rbl_pipe_core-0.11+<1",
    "rbl_pipe_usd-0.13+<1",
    "rbl_pipe_sg-0.23+<1",
]


def commands():
    env.PYTHONPATH.prepend("{root}/rbl_pipe_houdini/lib/python")
