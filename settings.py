"""
This file is part of Giswater plugin example
The program is free software: you can redistribute it and/or modify it under the terms of the GNU 
General Public License as published by the Free Software Foundation, either version 3 of the License, 
or (at your option) any later version.

Author(s): Iván Moreno, Nestor Ibáñez

"""
# -*- coding: utf-8 -*-

import configparser, os, sys, glob, importlib

# Pointer to the module object instance itself
this = sys.modules[__name__]

# we can explicitly make assignments on it
this.giswater_folder = None
this.tools_db = None
this.tools_log = None
this.tools_os = None
this.tools_qgis = None
this.tools_qt = None
this.tools_gw = None
this.dialog = None
this.toolbox = None
this.task = None


def init_plugin():

    if this.giswater_folder is not None:
        print("Variable giswater_folder already set")
        return

    this.giswater_folder = get_giswater_folder()
    if this.giswater_folder is None:
        print("Giswater plugin folder not found")
        return

    # Define imports from Giswater modules
    this.tools_db = importlib.import_module('.tools_db', package=f'{this.giswater_folder}.lib')
    this.tools_log = importlib.import_module('.tools_log', package=f'{this.giswater_folder}.lib')
    this.tools_os = importlib.import_module('.tools_os', package=f'{this.giswater_folder}.lib')
    this.tools_qgis = importlib.import_module('.tools_qgis', package=f'{this.giswater_folder}.lib')
    this.tools_qt = importlib.import_module('.tools_qt', package=f'{this.giswater_folder}.lib')
    this.tools_gw = importlib.import_module('.tools_gw', package=f'{this.giswater_folder}.core.utils')
    this.dialog = importlib.import_module('.dialog', package=f'{this.giswater_folder}.core.toolbars')
    this.toolbox = importlib.import_module('.toolbox_btn', package=f'{this.giswater_folder}.core.toolbars.utilities')
    this.task = importlib.import_module('.task', package=f'{this.giswater_folder}.core.threads')


def get_giswater_folder(filename_to_find='metadata.txt'):
    """ Find and return Giswater plugin folder name """

    # Get QGIS plugin root folder from environment variables
    qgis_plugin_root_folder = None
    try:
        if sys.platform == "win32":
            qgis_plugin_root_folder = os.environ['QGIS_PLUGINPATH']
        elif sys.platform == "linux":
            qgis_plugin_root_folder = os.environ['QGIS_PLUGINPATH']
        elif sys.platform == "darwin":
            qgis_plugin_root_folder = os.environ['QGIS_PLUGINPATH']
    except KeyError:
        # Key not found
        pass

    # Get QGIS plugin root folder from qgis plugin path
    if qgis_plugin_root_folder is None:
        qgis_plugin_root_folder = os.path.dirname(os.path.dirname(__file__))

    # Find @filename recursively inside this folder
    for filename in glob.glob(f"{qgis_plugin_root_folder}/**/{filename_to_find}", recursive=True):
        parser = configparser.ConfigParser()
        parser.read(filename)
        if not parser.has_section('general'): continue
        if not parser.has_option('general', 'name'): continue
        if parser['general']['name'] == 'giswater':
            giswater_folder_name = os.path.basename(os.path.dirname(filename))
            return giswater_folder_name

    return None


