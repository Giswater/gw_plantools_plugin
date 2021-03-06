"""
This file is part of Giswater 3
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import os
from functools import partial

from qgis.core import QgsApplication, QgsLayoutExporter, QgsProject
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QLabel

from ...threads.composer_pages import GwComposerPages
from ...ui.ui_manager import CompPagesUi
from .... import global_vars
from ....settings import tools_qgis, tools_qt, tools_gw, dialog, tools_os, tools_log, tools_db


class MassiveComposer(dialog.GwAction):

    def __init__(self, icon_path, action_name, text, toolbar, action_group):
        super().__init__(icon_path, action_name, text, toolbar, action_group)
        self.iface = global_vars.iface

    def clicked_event(self):

        dlg_comp = CompPagesUi()
        tools_gw.load_settings(dlg_comp)
        self.populate_cmb_composers(dlg_comp.cmb_composers)

        # Load user values
        last_path = tools_gw.get_config_parser('composer_pages', 'folder_path', 'user', 'session', plugin=global_vars.user_folder_name)
        tools_qt.set_widget_text(dlg_comp, dlg_comp.txt_path, last_path)
        last_prefix = tools_gw.get_config_parser('composer_pages', 'prefix', 'user', 'session', plugin=global_vars.user_folder_name)
        tools_qt.set_widget_text(dlg_comp, dlg_comp.txt_prefix, last_prefix)
        single = tools_os.set_boolean(tools_gw.get_config_parser('composer_pages', 'single', 'user', 'session', plugin=global_vars.user_folder_name))
        tools_qt.set_checked(dialog, dlg_comp.chk_single, single)

        # Set signals
        dlg_comp.btn_close.clicked.connect(partial(tools_gw.close_dialog, dlg_comp))
        dlg_comp.btn_path.clicked.connect(partial(self.get_folder_dialog, dlg_comp, dlg_comp.txt_path))
        dlg_comp.btn_accept.clicked.connect(partial(self.generate_pdfs, dlg_comp))
        dlg_comp.rejected.connect(partial(self.save_user_values, dlg_comp))
        dlg_comp.rejected.connect(partial(tools_gw.close_dialog, dlg_comp))

        self.dlg_comp = dlg_comp

        tools_gw.open_dialog(dlg_comp, dlg_name='dlg_comp_x_pages')


    def save_user_values(self, dialog):
        """ Save last user values """
        folder_path = tools_qt.get_text(dialog, dialog.txt_path)
        tools_gw.set_config_parser('composer_pages', 'folder_path', f"{folder_path}", plugin=global_vars.user_folder_name)
        last_composer = tools_qt.get_combo_value(dialog, dialog.cmb_composers, 0)
        tools_gw.set_config_parser('composer_pages', 'last_composer', f"{last_composer}", plugin=global_vars.user_folder_name)
        prefix = tools_qt.get_text(dialog, dialog.txt_prefix, False, False)
        tools_gw.set_config_parser('composer_pages', 'prefix', f"{prefix}", plugin=global_vars.user_folder_name)
        single = tools_qt.is_checked(dialog, dialog.chk_single)
        tools_gw.set_config_parser('composer_pages', 'single', f"{single}", plugin=global_vars.user_folder_name)


    def get_folder_dialog(self, dialog, widget):
        """ Get folder dialog """

        # Check if selected folder exists. Set default value if necessary
        folder_path = tools_qt.get_text(dialog, widget)
        if folder_path in (None, 'null') or not os.path.exists(folder_path):
            folder_path = os.path.expanduser("~")

        # Open dialog to select folder
        os.chdir(folder_path)
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.Directory)
        message = "Select folder"
        folder_path = file_dialog.getExistingDirectory(
            parent=None, caption=tools_qt.tr(message), directory=folder_path)
        if folder_path:
            tools_qt.set_widget_text(dialog, widget, str(folder_path))


    def populate_cmb_composers(self, combo):
        """
        :param combo: QComboBox to populate with composers and set with last composer if exist
        :return:
        """

        index = 0
        records = []
        layout_manager = QgsProject.instance().layoutManager()
        layouts = layout_manager.layouts()  # QgsPrintLayout
        if len(layouts) < 1: return
        for layout in layouts:
            elem = [index, layout.name()]
            records.append(elem)
            index = index + 1
        tools_qt.fill_combo_values(combo, records, 1, add_empty=True)
        last_composer = tools_gw.get_config_parser('composer_pages', 'last_composer', 'user', 'session', plugin=global_vars.user_folder_name)
        tools_qt.set_combo_value(combo, f'{last_composer}', 0)


    def generate_pdfs(self, dialog):
        folder_path = self.manage_folder_path(dialog)
        self.generate_composer_pages(dialog, folder_path)


    def manage_folder_path(self, dialog):

        folder_path = tools_qt.get_text(dialog, dialog.txt_path)
        if folder_path is None or folder_path == 'null' or not os.path.exists(folder_path):
            self.get_folder_dialog(dialog, dialog.txt_path)
            folder_path = tools_qt.get_text(dialog, dialog.txt_path)

        return folder_path


    def generate_composer_pages(self, dialog, path):

        # Check 'v_edit_plan_psector.atlas_id' values
        sql = "SELECT atlas_id FROM v_edit_plan_psector"
        rows = tools_db.get_rows(sql, log_info=False)
        for row in rows:
            if row[0] is not None:
                try:
                    int(row[0])
                except ValueError:
                    message = "All the values in the column 'atlas_id' from the table 'plan_psector' have to be INTEGER. " \
                              "This is not the case for your table, please fix this before continuing."
                    tools_qgis.show_warning(message)
                    return
            else:
                message = "The table 'plan_psector' contains NULL values in the column 'atlas_id'. " \
                          "Please fix this before continuing."
                tools_qgis.show_warning(message)
                return

        # Get user current selectors
        form = f'"currentTab":"tab_psector"'
        extras = f'"selectorType":"selector_basic", "filterText":""'
        body = tools_gw.create_body(form=form, extras=extras)
        current_selectors = tools_gw.execute_procedure('gw_fct_getselectors', body)

        # Remove all psectors from selectors and getting first time json with all psectors
        extras = f'"selectorType":"selector_basic", "tabName":"tab_psector", "checkAll":"False", "disableParent":"False", "addSchema":"NULL", "useAtlas":true'
        body = tools_gw.create_body(extras=extras)
        result = tools_gw.execute_procedure("gw_fct_setselectors", body, log_sql=True)

        # Get layout manager object
        layout_manager = QgsProject.instance().layoutManager()

        # Get our layout
        layout_name = tools_qt.get_text(dialog, dialog.cmb_composers)
        layout = layout_manager.layoutByName(layout_name)

        # Open Composer
        designer = self.iface.openLayoutDesigner(layout)
        atlas = layout.atlas()

        prefix = tools_qt.get_text(dialog, dialog.txt_prefix, False, False)
        if prefix not in (None, ''):
            prefix += " "

        is_single = tools_qt.is_checked(dialog, dialog.chk_single)

        if not designer.atlasPreviewEnabled():
            designer.setAtlasPreviewEnabled(True)
        if not atlas.enabled():
            atlas.setEnabled(True)
        layer = tools_qgis.get_layer_by_tablename("v_edit_plan_psector")
        if atlas.coverageLayer() != layer:
            message = "Generation of atlas uses v_edit_plan_psector as coverage layer ordered by atlas_id column. " \
                      "Please update the atlas' coverage layer before continuing."
            tools_qgis.show_warning(message)
            # TODO: set the coverage layer here with "atlas.setCoverageLayer(layer)". It doesn't work for some reason.
            designer.close()
            return

        # Create task
        description = f"Composer pages function"
        self.composer_task = GwComposerPages(description, result, layout, designer, prefix, path, is_single)
        self.composer_task.time_changed.connect(self._set_remaining_time)
        self.composer_task.change_btn_accept.connect(self._enable_cancel_btn)
        QgsApplication.taskManager().addTask(self.composer_task)
        QgsApplication.taskManager().triggerTask(self.composer_task)
        self.composer_task.task_finished.connect(partial(self.restore_user_selectors, current_selectors))


    def restore_user_selectors(self, current_selectors):
        """ Restore user selectors """
        qgis_project_add_schema = tools_qgis.get_plugin_settings_value('gwAddSchema')
        for form_tab in current_selectors['body']['form']['formTabs']:
            if form_tab['tableName'] != "selector_psector":
                continue
            for field in form_tab['fields']:
                _id = field['psector_id']
                extras = (f'"selectorType":"selector_basic", "tabName":"tab_psector", '
                          f'"id":"{_id}", "isAlone":"False", "value":"{field["value"]}", '
                          f'"addSchema":"{qgis_project_add_schema}"')
                body = tools_gw.create_body(extras=extras)
                tools_gw.execute_procedure('gw_fct_setselectors', body)


    def _enable_cancel_btn(self, enable):
        if enable:
            self.dlg_comp.btn_accept.clicked.disconnect()
            self.dlg_comp.btn_accept.setText(f"Cancel")
            self.dlg_comp.btn_accept.clicked.connect(self.composer_task.stop_task)
            self.dlg_comp.btn_close.hide()
        else:
            self.dlg_comp.btn_close.show()
            self.dlg_comp.btn_accept.clicked.disconnect()
            self.dlg_comp.btn_accept.setText(f"Accept")
            self.dlg_comp.btn_accept.clicked.connect(partial(self.generate_pdfs, self.dlg_comp))

    def _set_remaining_time(self, time):
        lbl_time = self.dlg_comp.findChild(QLabel, 'lbl_time')
        lbl_time.setText(time)

