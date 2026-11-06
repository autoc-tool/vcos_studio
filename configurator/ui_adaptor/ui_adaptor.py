# This Python file uses the following encoding: utf-8
############################################################################
# Copyright (c) 2025 Li Auto Inc. and its affiliates
# Licensed under the Apache License, Version 2.0(the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############################################################################
from ui_adaptor.func_logic_layer.func_logic_layer import FuncLogicLayer
from ui_adaptor.func_logic_layer.merge_ecuc_logic import compare_ecuc, all_diff_string, merge_ecuc
from ui_adaptor.ui_interaction.ui_interaction import UiInteraction
from ui_adaptor.ui_interaction.worker import Task
from ui_adaptor.ui_interaction.ui_logger import logger


class UIAdaptor:

    def __init__(
        self, app, is_debug=False, project_path="", status_queue=None, save_timer_flag=False, message=None
    ) -> None:
        Task.is_debug = is_debug
        self.project_path = project_path
        self.message = message
        self.app = app
        self.status_queue = status_queue
        self.save_timer_flag = save_timer_flag
        self.init()

    def init(self):
        self.function_logic_layer = FuncLogicLayer()
        bsw_editor_ui_func = self.function_logic_layer.bsw_editor_ui_func
        self.main_action_list = {
            "open_project": {
                "action_func": self.function_logic_layer.open_project,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_plugin_dir_list": {
                "action_func": self.function_logic_layer.update_plugin_dir_list,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_studio_version_action": {
                "action_func": self.function_logic_layer.get_studio_version_func,
                "enable_task": False,
                "enable_progress": False,
            },
            "load_project_config_action": {
                "action_func": self.function_logic_layer.load_project_config,
                "enable_task": True,
                "enable_progress": True,
            },
            "studio_version_upgrade_action": {
                "action_func": self.function_logic_layer.studio_version_upgrade,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_secondary_module_enabled_state": {
                "action_func": self.function_logic_layer.get_secondary_module_enabled_state,
                "enable_task": False,
                "enable_progress": False,
            },
            "rte_tab_widget_currentChanged_action": {
                "action_func": self.function_logic_layer.get_mapping_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "vcos_bsw_rte_switch_tab_solt": {
                "action_func": self.function_logic_layer.vcos_bsw_rte_switch_tab,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_generate_configuration": {
                "action_func": self.function_logic_layer.get_generate_configuration,
                "enable_task": False,
                "enable_progress": False,
            },
            "generate_modules": {
                "action_func": self.function_logic_layer.generate_modules,
                "enable_task": True,
                "enable_progress": True,
            },
            "generator_action": {
                "action_func": self.function_logic_layer.generate_vcos_c_code,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_validation_configuration": {
                "action_func": self.function_logic_layer.get_validation_configuration,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_dependency_modules": {
                "action_func": self.function_logic_layer.get_dependency_modules,
                "enable_task": False,
                "enable_progress": False,
            },
            "validate_modules": {
                "action_func": self.function_logic_layer.validate_modules,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_vcos_swc_name_list_action": {
                "action_func": self.function_logic_layer.get_vcos_swc_name_list,
                "enable_task": False,
                "enable_progress": False,
            },
            "swc_generator_action": {
                "action_func": self.function_logic_layer.generate_vcos_swc_template,
                "enable_task": True,
                "enable_progress": True,
            },
            "update_action": {
                "action_func": self.function_logic_layer.update_vcos_service_arxml,
                "enable_task": True,
                "enable_progress": True,
            },
            "close_action": {
                "action_func": self.function_logic_layer.save_vcos_project_config_file,
                "enable_task": True,
                "enable_progress": True,
            },
            "save_action": {
                "action_func": self.function_logic_layer.save_vcos_project_config_file,
                "enable_task": True,
                "enable_progress": True,
            },
            "codegen_save_action": {
                "action_func": self.function_logic_layer.codegen_save_vcos_project_config_file,
                "enable_task": True,
                "enable_progress": True,
            },
            "export_action": {
                "action_func": self.function_logic_layer.export_ecuc_arxml_file,
                "enable_task": True,
                "enable_progress": True,
            },
            "validate_ecuc_and_asw_arxml": {
                "action_func": self.function_logic_layer.validate_ecuc_and_asw_arxml_files,
                "enable_task": True,
                "enable_progress": True,
            },
            "parse_files_ecuc_to_module_dict": {
                "action_func": self.function_logic_layer.parse_files_ecuc_to_module_dict,
                "enable_task": True,
                "enable_progress": True,
            },
            "judge_ecuc_config_has_difference": {
                "action_func": self.function_logic_layer.judge_config_has_diff,
                "enable_task": False,
                "enable_progress": False,
            },
            "import_all_types_arxml": {
                "action_func": self.function_logic_layer.import_files_logic.import_all_types_arxml,
                "enable_task": True,
                "enable_progress": True,
            },
            "load_studio_plugin_config_file_action": {
                "action_func": self.function_logic_layer.load_studio_plugin_config_file_action,
                "enable_task": False,
                "enable_progress": False,
            },
            "new_project_action": {
                "action_func": self.function_logic_layer.update_vcos_project_config_file,
                "enable_task": False,
                "enable_progress": False,
            },
            "project_setting_action": {
                "action_func": self.function_logic_layer.show_vcos_project_information,
                "enable_task": False,
                "enable_progress": False,
            },
            "project_update": {
                "action_func": self.function_logic_layer.project_update,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_sys_info": {
                "action_func": self.function_logic_layer.get_sys_info,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_prj_path": {
                "action_func": self.function_logic_layer.get_prj_path,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_save_as_vcos_prj": {
                "action_func": self.function_logic_layer.update_save_as_vcos_prj,
                "enable_task": False,
                "enable_progress": False,
            },
            "save_as_vcos_project": {
                "action_func": self.function_logic_layer.save_as_vcos_project_config_file,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_secondary_menu_cfg": {
                "action_func": self.function_logic_layer.get_secondary_menu_cfg,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_module_dependency_tab_list": {
                "action_func": self.function_logic_layer.get_module_dependency_tab_list,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_enable_modules": {
                "action_func": self.function_logic_layer.get_enable_modules,
                "enable_task": False,
                "enable_progress": False,
            },
            "save_system_arxml_arxml_action": {
                "action_func": self.function_logic_layer.save_system_arxml_arxml,
                "enable_task": True,
                "enable_progress": False,
            },
            # PortMapping begin
            "port_mapping_rte_right_click_connect": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_rte_right_click_connect,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_rte_right_click_disconnect": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_rte_right_click_disconnect,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_first_level_finish": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_first_level_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_rte_open_assistant": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_rte_open_assistant,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_first_level_next": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_first_level_next,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_second_level_next": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_second_level_next,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_third_level_double_click_component": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_third_level_double_click_component,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_third_level_double_click_port": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_third_level_double_click_port,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_third_level_finish": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_third_level_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_third_level_component_finish": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_third_level_component_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_third_level_port_finish": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_third_level_port_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_get_main_table_data": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_get_main_table_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "port_mapping_get_all_component_name_to_update": {
                "action_func": self.function_logic_layer.port_mapping_func.cbk_get_all_component_name_to_update,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_port_mapping_table_after_import_asw": {
                "action_func": self.function_logic_layer.port_mapping_func.update_port_mapping_table_after_import_asw,
                "enable_task": False,
                "enable_progress": False,
            },
            # PortMapping end
            # ServiceMapping begin
            "service_mapping_rte_right_click_connect": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_rte_right_click_connect,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_rte_right_click_disconnect": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_rte_right_click_disconnect,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_first_level_finish": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_first_level_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_rte_open_assistant": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_rte_open_assistant,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_first_level_next": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_first_level_next,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_second_level_next": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_second_level_next,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_third_level_double_click_component": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_third_level_double_click_component,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_third_level_double_click_port": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_third_level_double_click_port,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_third_level_finish": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_third_level_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_third_level_component_finish": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_third_level_component_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_third_level_port_finish": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_third_level_port_finish,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_get_main_table_data": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_get_main_table_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "service_mapping_get_all_service_component_name_to_update": {
                "action_func": self.function_logic_layer.service_mapping_func.cbk_get_all_service_component_name_to_update,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_service_mapping_table_after_import_asw": {
                "action_func": self.function_logic_layer.service_mapping_func.update_service_mapping_table_after_import_asw,
                "enable_task": False,
                "enable_progress": False,
            },
            # ServiceMapping end
            # DataMapping begin
            "data_mapping_get_main_table_data": {
                "action_func": self.function_logic_layer.data_mapping_func.cbk_get_main_table_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_rte_right_click_connect": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_editor_map_ui_data_from_editor_main_ui,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_editor_main_ui_right_click_remove_mapping": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_editor_main_ui_data_right_click_remove_mapping,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_first_level_finish": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_editor_main_ui_data_from_editor_map_ui,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_editor_map_ui_data_from_editor_signal_ui": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_editor_map_ui_data_from_editor_signal_ui,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_editor_signal_ui_data_from_editor_map_ui": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_editor_signal_ui_data_from_editor_map_ui,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_assistant_main_ui_data_open_assistant": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_assistant_main_ui_data_open_assistant,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_assistant_map_ui_data_after_selecting_port": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_assistant_map_ui_data_after_selecting_port,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_assistant_signal_ui_data": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_assistant_signal_ui_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_assistant_map_ui_data_after_selecting_signal": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_assistant_map_ui_data_after_selecting_signal,
                "enable_task": False,
                "enable_progress": False,
            },
            "data_mapping_editor_main_ui_data_after_assistant_mapping": {
                "action_func": self.function_logic_layer.data_mapping_func.get_data_mapping_editor_main_ui_data_after_assistant_mapping,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_flatextract_data_mapping_after_import": {
                "action_func": self.function_logic_layer.data_mapping_func.update_flatextract_data_mapping_after_import,
                "enable_task": False,
                "enable_progress": False,
            },
            # DataMapping end
            # module_management begin
            "apply_module_renaming": {
                "action_func": self.function_logic_layer.module_manage_logic.change_module_name,
                "enable_task": True,
                "enable_progress": True,
            },
            "add_modules_ui": {
                "action_func": self.function_logic_layer.module_manage_logic.init_module_management,
                "enable_task": False,
                "enable_progress": False,
            },
            "close_modules_ui": {
                "action_func": self.function_logic_layer.module_manage_logic.close_module_management,
                "enable_task": False,
                "enable_progress": False,
            },
            "apply_modules_change": {
                "action_func": self.function_logic_layer.module_manage_logic.apply_modules_change,
                "enable_task": True,
                "enable_progress": True,
            },
            "remove_modules": {
                "action_func": self.function_logic_layer.module_manage_logic.remove_modules,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_current_project_module_info": {
                "action_func": self.function_logic_layer.module_manage_logic.get_current_project_module_info,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_module_dependence": {
                "action_func": self.function_logic_layer.module_manage_logic.get_module_dependence,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_module_dependence_by": {
                "action_func": self.function_logic_layer.module_manage_logic.get_module_dependence_by,
                "enable_task": False,
                "enable_progress": False,
            },
            # module_management end
            # import files begin
            "get_imported_excel": {
                "action_func": self.function_logic_layer.import_files_logic.get_imported_excel,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_imported_com_excel": {
                "action_func": self.function_logic_layer.import_files_logic.get_imported_com_excel,
                "enable_task": False,
                "enable_progress": False,
            },
            "init_import_files_ui": {
                "action_func": self.function_logic_layer.import_files_logic.init_import_files_ui,
                "enable_task": True,
                "enable_progress": True,
            },
            "parser_dbc_and_get_original_data_action": {
                "action_func": self.function_logic_layer.import_files_logic.import_dbc,
                "enable_task": True,
                "enable_progress": True,
            },
            "parser_files_get_original_data_action": {
                "action_func": self.function_logic_layer.import_files_logic.import_files,
                "enable_task": True,
                "enable_progress": True,
            },
            "parser_replace_files_get_original_data_action": {
                "action_func": self.function_logic_layer.import_files_logic.replace_files,
                "enable_task": True,
                "enable_progress": True,
            },
            "node_selected_changed": {
                "action_func": self.function_logic_layer.import_files_logic.node_selected_changed,
                "enable_task": False,
                "enable_progress": False,
            },
            "remove_imported_files": {
                "action_func": self.function_logic_layer.import_files_logic.remove_files,
                "enable_task": False,
                "enable_progress": False,
            },
            "apply_dbc_ldf_import": {
                "action_func": self.function_logic_layer.import_files_logic.apply_dbc_ldf_import,
                "enable_task": True,
                "enable_progress": True,
            },
            "check_before_apply": {
                "action_func": self.function_logic_layer.import_files_logic.check_before_apply,
                "enable_task": True,
                "enable_progress": True,
            },
            "apply_diag_com_import": {
                "action_func": self.function_logic_layer.import_files_logic.apply_import,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_single_signal_state": {
                "action_func": self.function_logic_layer.import_files_logic.apply_cdd_signal,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_is_add_channel_name": {
                "action_func": self.function_logic_layer.import_files_logic.get_is_add_channel_name,
                "enable_task": False,
                "enable_progress": False,
            },
            "close_import_dbc_ldf_ui": {
                "action_func": self.function_logic_layer.import_files_logic.deinit_import_dbc_ldf_ui,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_dbc_ldf_content": {
                "action_func": self.function_logic_layer.import_files_logic.get_dbc_ldf_content,
                "enable_task": False,
                "enable_progress": False,
            },
            "init_import_cdd_ui": {
                "action_func": self.function_logic_layer.import_files_logic.init_import_cdd_ui,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_imported_diag_excel": {
                "action_func": self.function_logic_layer.import_files_logic.get_imported_diag_excel,
                "enable_task": False,
                "enable_progress": False,
            },
            "parser_cdd_and_update_ecuc_arxml_action": {
                "action_func": self.function_logic_layer.import_files_logic.apply_cdd_import,
                "enable_task": True,
                "enable_progress": True,
            },
            "parser_asw_arxml_and_update_arxml_action": {
                "action_func": self.function_logic_layer.import_files_logic.apply_asw_import,
                "enable_task": True,
                "enable_progress": True,
            },
            "parser_mcal_arxml_and_get_all_module_action": {
                "action_func": self.function_logic_layer.import_files_logic.get_all_module_of_mcal_arxml,
                "enable_task": False,
                "enable_progress": False,
            },
            "import_sidl_sdepl_dir": {
                "action_func": self.function_logic_layer.import_files_logic.import_sidl_sdepl_dir,
                "enable_task": True,
                "enable_progress": True,
            },
            "clear_initial_arxml_container": {
                "action_func": self.function_logic_layer.import_files_logic.clear_initial_container,
                "enable_task": False,
                "enable_progress": False,
            },
            "restore_possibility": {
                "action_func": self.function_logic_layer.import_files_logic.restore_possibility,
                "enable_task": False,
                "enable_progress": False,
            },
            # import files end
            # os auto configuration start
            "import_os_cfg": {
                "action_func": self.function_logic_layer.import_os_cfg,
                "enable_task": True,
                "enable_progress": True,
            },
            "export_os_cfg": {
                "action_func": self.function_logic_layer.export_os_cfg,
                "enable_task": True,
                "enable_progress": True,
            },
            # os auto configuration end
            # task mapping
            "task_mapping_post_update_os_ecuc": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_post_update_os_ecuc,
                "enable_task": True,
                "enable_progress": False,
            },
            "task_mapping_update_ui_all": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_update_ui_all,
                "enable_task": True,
                "enable_progress": False,
            },
            "task_mapping_tree_unmap": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_unmap_tree_items,
                "enable_task": False,
                "enable_progress": False,
            },
            "task_mapping_table_unmap": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_unmap_table_items,
                "enable_task": False,
                "enable_progress": False,
            },
            "task_mapping_get_item_index": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_get_item_index_by_id,
                "enable_task": False,
                "enable_progress": False,
            },
            "task_mapping_get_root_item": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_get_root_item,
                "enable_task": False,
                "enable_progress": False,
            },
            "task_mapping_get_item_list": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_get_item_list,
                "enable_task": False,
                "enable_progress": False,
            },
            "task_mapping_get_table_headers": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_get_table_headers,
                "enable_task": False,
                "enable_progress": False,
            },
            "task_mapping_remap_data": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_remap_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_all_runnnable_info": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_get_all_runnable_info,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_configured_vfb_trace_info": {
                "action_func": self.function_logic_layer.cbk_get_vfb_trace_info,
                "enable_task": False,
                "enable_progress": False,
            },
            "clear_vfb_trace_functions": {
                "action_func": self.function_logic_layer.vfb_trace_function.cbk_clear_vfb_trace_functions,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_runnable_pos_index": {
                "action_func": self.function_logic_layer.task_mapping_func.cbk_get_runnable_pos_index,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_task_col_in_table": {
                "action_func": self.function_logic_layer.task_mapping_func.get_task_col_in_table,
                "enable_task": False,
                "enable_progress": False,
            },
            # bsw editor
            "bsw_editor_get_the_show_data_of_the_container": {
                "action_func": bsw_editor_ui_func.bsw_editor_get_the_show_data_of_the_container,
                "enable_task": False,
                "enable_progress": False,
            },
            "sec_bsw_editor_get_the_show_data_of_the_container": {
                "action_func": bsw_editor_ui_func.sec_bsw_editor_get_the_show_data_of_the_container,
                "enable_task": False,
                "enable_progress": False,
            },
            "sec_get_bswm_mod_and_ecuc_obj": {
                "action_func": bsw_editor_ui_func.sec_get_bswm_mod_and_ecuc_obj,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_container_short_name_to_ecuc_arxml": {
                "action_func": bsw_editor_ui_func.update_container_short_name_to_ecuc_arxml,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_update_all_configuration_items_that_reference_this_ref": {
                "action_func": bsw_editor_ui_func.bsw_editor_update_all_configuration_items_that_reference_this_ref,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_get_all_internal_ref_targets_from_ecuc_arxml": {
                "action_func": bsw_editor_ui_func.bsw_editor_get_all_internal_ref_targets_from_ecuc_arxml,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_get_all_foreign_ref_targets_from_foreign_arxml": {
                "action_func": bsw_editor_ui_func.bsw_editor_get_all_foreign_ref_targets_from_foreign_arxml,
                "enable_task": False,
                "enable_progress": False,
            },
            "filter_referenced_configurations": {
                "action_func": bsw_editor_ui_func.cbk_filter_referenced_configurations,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_editing_finished_and_write_to_ecuc_arxml": {
                "action_func": bsw_editor_ui_func.bsw_editor_editing_finished_and_write_to_ecuc_arxml,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_module_container_pre_cfg": {
                "action_func": bsw_editor_ui_func.update_module_container_pre_cfg,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_module_container_pre_cfg": {
                "action_func": bsw_editor_ui_func.get_module_container_pre_cfg,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_add_param_item_and_write_to_ecuc_arxml": {
                "action_func": bsw_editor_ui_func.bsw_editor_add_param_item_and_write_to_ecuc_arxml,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_remove_param_item_and_write_to_ecuc_arxml": {
                "action_func": bsw_editor_ui_func.bsw_editor_remove_param_item_and_write_to_ecuc_arxml,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_set_user_defined": {
                "action_func": bsw_editor_ui_func.bsw_editor_set_user_defined,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_remove_user_defined": {
                "action_func": bsw_editor_ui_func.bsw_editor_remove_user_defined,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_set_is_lock": {
                "action_func": bsw_editor_ui_func.bsw_editor_set_is_lock,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_remove_is_lock": {
                "action_func": bsw_editor_ui_func.bsw_editor_remove_is_lock,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_get_admin_data": {
                "action_func": bsw_editor_ui_func.bsw_editor_get_admin_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_set_integer_format": {
                "action_func": bsw_editor_ui_func.bsw_editor_set_integer_format,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_all_ref_configuration_items_by_ref_target": {
                "action_func": bsw_editor_ui_func.bsw_editor_all_ref_configuration_items_by_ref_target,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_update_bsw_module_data": {
                "action_func": bsw_editor_ui_func.bsw_editor_update_bsw_module_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_update_bsw_module_data_and_view": {
                "action_func": bsw_editor_ui_func.bsw_editor_update_bsw_module_data,
                "enable_task": True,
                "enable_progress": False,
            },
            "bsw_editor_update_bsw_module_data_with_progress": {
                "action_func": bsw_editor_ui_func.bsw_editor_update_bsw_module_data,
                "enable_task": True,
                "enable_progress": True,
            },
            "bsw_editor_update_bsw_modules": {
                "action_func": bsw_editor_ui_func.bsw_editor_update_modules,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_all_element_items": {
                "action_func": bsw_editor_ui_func.get_all_element_items,
                "enable_task": True,
                "enable_progress": False,
            },
            "open_arxml_file": {
                "action_func": bsw_editor_ui_func.open_arxml_file,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_update_linked_cfg_item": {
                "action_func": bsw_editor_ui_func.bsw_editor_update_linked_cfg_item,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_input_push_stack": {
                "action_func": bsw_editor_ui_func.bsw_editor_input_push_stack,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_qreference_push_stack": {
                "action_func": bsw_editor_ui_func.bsw_editor_qreference_push_stack,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_qstring_push_stack": {
                "action_func": bsw_editor_ui_func.bsw_editor_qstring_push_stack,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_container_outline_push_stack": {
                "action_func": bsw_editor_ui_func.bsw_editor_container_outline_push_stack,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_container_push_stack": {
                "action_func": bsw_editor_ui_func.bsw_editor_container_push_stack,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_undo_slot": {
                "action_func": bsw_editor_ui_func.bsw_editor_undo,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_editor_redo_slot": {
                "action_func": bsw_editor_ui_func.bsw_editor_redo,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_schedule_table_data": {
                "action_func": bsw_editor_ui_func.get_schedule_table_data,
                "enable_task": True,
                "enable_progress": True,
            },
            "generate_schedule_table_cfg": {
                "action_func": bsw_editor_ui_func.generate_schedule_table_cfg,
                "enable_task": True,
                "enable_progress": True,
            },
            "generate_schedule_table_cfg_by_jitter": {
                "action_func": bsw_editor_ui_func.generate_schedule_table_cfg_by_jitter,
                "enable_task": True,
                "enable_progress": True,
            },
            "generate_all_schedule_table_cfg": {
                "action_func": bsw_editor_ui_func.generate_all_schedule_table_cfg,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_schedule_table_task_dict": {
                "action_func": bsw_editor_ui_func.get_schedule_table_task_dict,
                "enable_task": False,
                "enable_progress": False,
            },
            "save_schedule_table_ui_data": {
                "action_func": bsw_editor_ui_func.save_schedule_table_ui_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "clear_schedule_table_ui_cache": {
                "action_func": bsw_editor_ui_func.clear_schedule_table_ui_cache,
                "enable_task": False,
                "enable_progress": False,
            },
            "clear_jitter_opt_history": {
                "action_func": bsw_editor_ui_func.clear_jitter_opt_history,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_jitter_opt_history_time": {
                "action_func": bsw_editor_ui_func.get_jitter_opt_history_time,
                "enable_task": False,
                "enable_progress": False,
            },
            "rollback_jitter_opt_history": {
                "action_func": bsw_editor_ui_func.rollback_jitter_opt_history,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_used_os_alarm_infos_by_task_ref": {
                "action_func": bsw_editor_ui_func.get_used_os_alarm_infos_by_task_ref,
                "enable_task": False,
                "enable_progress": False,
            },
            "set_used_alarm_offset_by_mapping_ref": {
                "action_func": bsw_editor_ui_func.set_used_alarm_offset_by_mapping_ref,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_create_container_dialog_show_data": {
                "action_func": bsw_editor_ui_func.get_create_container_dialog_show_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_init_function_settings": {
                "action_func": bsw_editor_ui_func.get_init_function_settings,
                "enable_task": False,
                "enable_progress": False,
            },
            "bsw_edit_reset_initialization": {
                "action_func": bsw_editor_ui_func.reset_initialization,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_sec_bsw_management_configuration": {
                "action_func": bsw_editor_ui_func.get_sec_bsw_management_configuration,
                "enable_task": False,
                "enable_progress": False,
            },
            "sec_bsw_editor_update_state_to_bswm_common_data": {
                "action_func": bsw_editor_ui_func.update_state_to_bswm_common_data,
                "enable_task": False,
                "enable_progress": False,
            },
            "sec_bsw_editor_check_container_of_bswm_ecuc": {
                "action_func": bsw_editor_ui_func.check_container_of_bswm_ecuc,
                "enable_task": False,
                "enable_progress": False,
            },
            "sec_get_init_functions_that_have_been_initialized_in_ecum": {
                "action_func": bsw_editor_ui_func.sec_get_init_functions_that_have_been_initialized_in_ecum,
                "enable_task": False,
                "enable_progress": False,
            },
            # bsw editor end
            # export
            "export_mapping_info_to_excel": {
                "action_func": self.function_logic_layer.export_file_func.export_mapping_info_to_excel,
                "enable_task": False,
                "enable_progress": False,
            },
            # export end
            "delete_file_lock_action": {
                "action_func": self.function_logic_layer.delete_file_lock,
                "enable_task": False,
                "enable_progress": False,
            },
            "add_file_lock_action": {
                "action_func": self.function_logic_layer.add_file_lock,
                "enable_task": False,
                "enable_progress": False,
            },
            # validation
            "validation_param": {
                "action_func": self.function_logic_layer.validation_func.cbk_validate_param,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_container": {
                "action_func": self.function_logic_layer.validation_func.cbk_validate_container,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_get_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_get_validation_logs,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_get_module_fail_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_get_module_failed_validation_logs,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_container_validation_fail_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_get_container_validation_fail_logs,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_fail_logs_to_ui_dict": {
                "action_func": self.function_logic_layer.validation_func.cbk_validation_fail_logs_to_ui_dict,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_get_cached_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_get_cached_logs,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_save_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_save_validation_logs_to_file,
                "enable_task": True,
                "enable_progress": False,
            },
            "validation_load_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_load_validation_logs_from_file,
                "enable_task": True,
                "enable_progress": False,
            },
            "validation_get_ignored_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_get_ignored_logs,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_save_ignored_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_save_ignored_logs_to_file,
                "enable_task": True,
                "enable_progress": False,
            },
            "validation_load_ignored_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_load_ignored_logs_from_file,
                "enable_task": True,
                "enable_progress": False,
            },
            "validation_update_ignored_logs": {
                "action_func": self.function_logic_layer.validation_func.cbk_update_ignored_logs,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_remove_container": {
                "action_func": self.function_logic_layer.validation_func.update_validation_log_pass,
                "enable_task": False,
                "enable_progress": False,
            },
            "validation_update_modify_container_name": {
                "action_func": self.function_logic_layer.validation_func.cbk_validation_update_modify_container_name,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_arxml_value_by_one_click_solution": {
                "action_func": self.function_logic_layer.validation_func.cbk_update_arxml_value_by_one_click_solution,
                "enable_task": False,
                "enable_progress": False,
            },
            "create_container_by_one_click_solution": {
                "action_func": self.function_logic_layer.validation_func.cbk_create_container_by_one_click_solution,
                "enable_task": False,
                "enable_progress": False,
            },
            "set_repopulate_value_by_one_click_solution": {
                "action_func": self.function_logic_layer.validation_func.cbk_set_repopulate_value_by_one_click_solution,
                "enable_task": False,
                "enable_progress": False,
            },
            "delete_reference_by_one_click_solution": {
                "action_func": self.function_logic_layer.validation_func.cbk_delete_reference_by_one_click_solution,
                "enable_task": False,
                "enable_progress": False,
            },
            "update_mode_info": {
                "action_func": self.function_logic_layer.update_mode_info,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_module_type": {
                "action_func": self.function_logic_layer.get_module_type,
                "enable_task": False,
                "enable_progress": False,
            },
            "get_vcos_version": {
                "action_func": self.function_logic_layer.get_vcos_version,
                "enable_task": False,
                "enable_progress": False,
            },
            "compare_ecuc": {
                "action_func": compare_ecuc,
                "enable_task": False,
                "enable_progress": False,
            },
            "all_diff_string": {
                "action_func": all_diff_string,
                "enable_task": False,
                "enable_progress": False,
            },
            # [Task analysis] part start
            "task_analysis_ui": {
                "action_func": self.function_logic_layer.task_analysis_func.task_analysis_ui_info,
                "enable_task": False,
                "enable_progress": False,
            },
            "gen_cheddar_with_cet": {
                "action_func": self.function_logic_layer.task_analysis_func.gen_cheddar_with_cet,
                "enable_task": True,
                "enable_progress": True,
            },
            "schedulability_analysis": {
                "action_func": self.function_logic_layer.task_analysis_func.schedulability_analysis,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_ftrace_task_irq_info": {
                "action_func": self.function_logic_layer.task_analysis_func.get_ftrace_task_irq_info,
                "enable_task": True,
                "enable_progress": True,
            },
            # [Task analysis] part finish
            "merge_ecuc": {
                "action_func": merge_ecuc,
                "enable_task": True,
                "enable_progress": True,
            },
            "check_mcal_module_codegen_cmd_line_tool_exist": {
                "action_func": self.function_logic_layer.check_mcal_module_codegen_cmd_line_tool_exist,
                "enable_task": False,
                "enable_progress": False,
            },
            "parse_rte_codegen_dict": {
                "action_func": self.function_logic_layer.parse_rte_codegen_dict,
                "enable_task": False,
                "enable_progress": False,
            },
            "periodic_save_configuration_action": {
                "action_func": self.function_logic_layer.periodic_save_configuration,
                "enable_task": True,
                "enable_progress": False,
            },
            "project_close_handle_action": {
                "action_func": self.function_logic_layer.check_save_project_thread,
                "enable_task": True,
                "enable_progress": True,
            },
            "get_periodic_save_time_action": {
                "action_func": self.function_logic_layer.get_periodic_save_time,
                "enable_task": False,
                "enable_progress": False,
            },
            "set_periodic_save_time_action": {
                "action_func": self.function_logic_layer.set_periodic_save_time,
                "enable_task": False,
                "enable_progress": False,
            },
        }
        self.ui_interaction = UiInteraction(
            self.app,
            self.project_path,
            self.call_back,
            status_queue=self.status_queue,
            save_timer_flag=self.save_timer_flag,
            message=self.message,
        )

    def call_back(self, *args, **kwargs):
        if len(args) == 0 or not self.main_action_list.get(args[0]):
            logger.error(f"{args} The number of parameters is wrong, or {args} is lost in main_action_list")
            return

        main_action = self.main_action_list[args[0]]
        if (
            main_action.get("action_func", None) is None
            or main_action.get("enable_task", None) is None
            or main_action.get("enable_progress", None) is None
        ):
            logger.error(f"{args[0]} is lost in main_action_list")
            return

        active_func = main_action.get("action_func")
        is_enable_task = main_action.get("enable_task")
        if not callable(active_func):
            logger.error(f"{active_func} is not callable")
            return
        if is_enable_task is False:
            result = active_func(*(args[1:]))
            if callable(kwargs.get("result_callback")):
                kwargs["result_callback"](result)
            else:
                return result
        else:
            Task(
                active_func,
                *(args[1:]),
                result_callback=kwargs.get("result_callback", None),
                error_callback=kwargs.get("error_callback", None),
                finished_callback=kwargs.get("finished_callback", None),
                enable_progress=main_action.get("enable_progress", None),
            )
