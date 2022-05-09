"""
This file is part of Giswater 3
The program is free software: you can redistribute it and/or modify it under the terms of the GNU 
General Public License as published by the Free Software Foundation, either version 3 of the License, 
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import configparser
import os.path
import sys

from qgis.PyQt.QtCore import QObject, QSettings
from qgis.PyQt.QtWidgets import QActionGroup, QDockWidget, QToolBar
from qgis.core import Qgis

from .plugin_toolbar import PluginToolbar
from .core.toolbars import buttons
from . import global_vars

from .settings import tools_qgis, tools_os, tools_log, tools_gw


class GWComposerPlugin(QObject):

    def __init__(self, iface):
        """ Constructor
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Initialize instance attributes
        super(GWComposerPlugin, self).__init__()
        self.iface = iface
        self.plugin_toolbars = {}
        self.buttons = {}
        self.srid = None
        self.load_project = None
        self.dict_toolbars = {}
        self.dict_actions = {}
        self.actions_not_checkable = None
        self.available_layers = []
        self.btn_add_layers = None
        self.update_sql = None
        self.action = None
        self.action_info = None
        self.toolButton = None


    def unload(self, remove_modules=True):
        """ Removes plugin menu items and icons from QGIS GUI
            :param @remove_modules is True when plugin is disabled or reloaded
        """
        # Check if any button is loaded and remove them from the toolbar
        if self.buttons:
            for button in list(self.buttons.values()):
                button.action.setVisible(False)
                del button


    def initGui(self):
        """ Create the menu entries and toolbar icons inside the QGIS GUI """

        # Connect signals
        self.iface.projectRead.connect(self._project_read)
        self.iface.newProjectCreated.connect(self.unload)

        # Initialize plugin
        self.init_plugin()


    def init_plugin(self):
        """ Plugin main initialization function """

        # Initialize plugin global variables
        self.plugin_dir = os.path.dirname(__file__)
        self.icon_folder = self.plugin_dir + os.sep + 'icons' + os.sep + 'toolbars' + os.sep
        self.plugin_name = self.get_plugin_metadata('name', 'giswater')
        setting_file = os.path.join(self.plugin_dir, 'config', 'init.config')
        if not os.path.exists(setting_file):
            message = f"Config file not found at: {setting_file}"
            self.iface.messageBar().pushMessage("", message, 1, 20)
            return

        if Qgis.QGIS_VERSION_INT < 32000:
            message = f"The plugin {self.plugin_name} is only compatible with QGIS 3.20 or newer. It will be disabled."
            tools_qgis.show_message(message)
            return

        global_vars.init_global(self.iface, self.iface.mapCanvas(), self.plugin_dir, self.plugin_name, None)
        giswater_plugin_name = tools_qgis.get_plugin_metadata('name', 'giswater')
        get_major_version = tools_qgis.get_major_version()
        global_vars.roaming_user_dir = f'{tools_os.get_datadir()}{os.sep}{giswater_plugin_name}{os.sep}{get_major_version}'

        self.settings = QSettings(setting_file, QSettings.IniFormat)
        self.settings.setIniCodec(sys.getfilesystemencoding())

        self.qgis_settings = QSettings()
        self.qgis_settings.setIniCodec(sys.getfilesystemencoding())

        # Check if user config folder exists
        user_folder_name = self.plugin_name.replace('gw_', '').replace('_plugin', '')
        tools_gw.manage_user_config_folder(f"{global_vars.roaming_user_dir}{os.sep}{user_folder_name}")
        global_vars.user_folder_name = user_folder_name

        self._project_read()


    def _project_read(self):

        if not self._check_project(True):
            return

        # Manage section 'actions_list' of config file
        self.manage_section_actions_list()

        # Manage section 'toolbars' of config file
        self.manage_section_toolbars()

        # PROJECT_READ
        self.manage_toolbars()



    def _check_project(self, show_warning):
        """ Check if loaded project is valid for Giswater """

        # Check if table 'v_edit_node' is loaded
        self.layer_node = tools_qgis.get_layer_by_tablename("v_edit_node")
        if not self.layer_node and show_warning:
            layer_arc = tools_qgis.get_layer_by_tablename("v_edit_arc")
            layer_connec = tools_qgis.get_layer_by_tablename("v_edit_connec")
            if layer_arc or layer_connec:
                title = "Giswater tools plugin cannot be loaded"
                msg = "QGIS project seems to be a Giswater project, but layer 'v_edit_node' is missing"
                tools_qgis.show_warning(msg, 20, title=title)
                return False
            return False
        return True


    def manage_toolbars(self):
        """ Manage actions of the custom plugin toolbars.
        project_type in ('ws', 'ud')
        """

        self.create_toolbar('plan')

        # Manage action group of every toolbar
        parent = self.iface.mainWindow()
        for plugin_toolbar in list(self.plugin_toolbars.values()):
            ag = QActionGroup(parent)
            for index_action in plugin_toolbar.list_actions:
                button_def = self.settings.value(f"buttons_def/{index_action}")
                button_tooltip = self.settings.value(f"buttons_tooltip/{index_action}")
                if button_def:
                    text = f'{button_tooltip}'
                    icon_path = self.icon_folder + plugin_toolbar.toolbar_id + os.sep + index_action + ".png"
                    button = getattr(buttons, button_def)(icon_path, button_def, text, plugin_toolbar.toolbar, ag)
                    self.buttons[index_action] = button


    def create_toolbar(self, toolbar_id):

        list_actions = self.settings.value(f"toolbars/{toolbar_id}")
        if list_actions is None:
            return

        if type(list_actions) != list:
            list_actions = [list_actions]

        toolbar_name = f'toolbar_{toolbar_id}_name'
        plugin_toolbar = PluginToolbar(toolbar_id, toolbar_name, True)

        # Check if there is a giswater toolbar suiting for the plugin buttons
        toolbars = [toolbar for toolbar in self.iface.mainWindow().findChildren(QToolBar) if toolbar.objectName() and 'giswater' in toolbar.objectName().lower() and toolbar_id in toolbar.objectName().lower()]
        if toolbars:
            plugin_toolbar.toolbar = toolbars[0]
            plugin_toolbar.name = toolbars[0].objectName()
        # If the toolbar is ToC, add it to the Layes docker toolbar, else create a new toolbar
        elif toolbar_id == "toc":
            plugin_toolbar.toolbar = self.iface.mainWindow().findChild(QDockWidget, 'Layers').findChildren(QToolBar)[0]
        else:
            plugin_toolbar.toolbar = self.iface.addToolBar(toolbar_name)
            plugin_toolbar.toolbar.setObjectName(toolbar_name)

        plugin_toolbar.list_actions = list_actions
        self.plugin_toolbars[toolbar_id] = plugin_toolbar


    def manage_section_actions_list(self):
        """ Manage section 'actions_list' of config file """

        # Dynamically get parameters defined in section 'actions_list'
        section = 'actions_not_checkable'
        self.settings.beginGroup(section)
        list_keys = self.settings.allKeys()
        self.settings.endGroup()

        for key in list_keys:
            list_values = self.settings.value(f"{section}/{key}")
            if list_values:
                self.dict_actions[key] = list_values
            else:
                print(f"Parameter not set in section '{section}' of config file: '{key}'")

        # Get list of actions not checkable (normally because they open a form)
        aux = []
        for list_actions in self.dict_actions.values():
            for elem in list_actions:
                aux.append(elem)

        self.actions_not_checkable = sorted(aux)


    def manage_section_toolbars(self):
        """ Manage section 'toolbars' of config file """

        # Dynamically get parameters defined in section 'toolbars'
        section = 'toolbars'
        self.settings.beginGroup(section)
        list_keys = self.settings.allKeys()
        self.settings.endGroup()
        for key in list_keys:
            list_values = self.settings.value(f"{section}/{key}")
            if list_values:
                # Check if list_values has only one value
                if type(list_values) is str:
                    list_values = [list_values]
                self.dict_toolbars[key] = list_values
            else:
                print(f"Parameter not set in section '{section}' of config file: '{key}'")


    def get_plugin_metadata(self, parameter, default_value):
        """ Get @parameter from metadata.txt file """

        # Check if metadata file exists
        metadata_file = os.path.join(self.plugin_dir, 'metadata.txt')
        if not os.path.exists(metadata_file):
            message = f"Metadata file not found: {metadata_file}"
            print(message)
            return default_value

        value = None
        try:
            metadata = configparser.ConfigParser()
            metadata.read(metadata_file)
            value = metadata.get('general', parameter)
        except configparser.NoOptionError:
            message = f"Parameter not found: {parameter}"
            print(message)
            value = default_value
        finally:
            return value

