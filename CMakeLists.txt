cmake_minimum_required(VERSION 2.8)

include(RezBuild)

file(GLOB_RECURSE py_files "lib/python/*.py")
rez_install_files(
    ${py_files}
    DESTINATION rbl_pipe_houdini
)

file(GLOB_RECURSE config "config/*")
rez_install_files(
    ${config}
    DESTINATION rbl_pipe_houdini
)
