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
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import xmltodict
import os
from basic_func_module.path_handler.path_converter import PathConverter_Adaptor


class ProjectXmlInfoHandler:

    @classmethod
    def dict_to_xml(cls, parent, data):
        for key, value in data.items():
            child = ET.SubElement(parent, key)
            if isinstance(value, dict):
                cls.dict_to_xml(child, value)
            else:
                child.text = str(value)

    @classmethod
    def load_xml_file(cls, project_file_path):
        project_file_path = os.path.join(os.path.dirname(project_file_path), "vcos_project.xml")
        if not os.path.isfile(project_file_path):
            return None
        # 读取XML文件
        with open(project_file_path, "r") as file:
            xml_data = file.read()

        data = xmltodict.parse(xml_data)
        ProjectXmlInfoHandler.to_abs_paths(data["root"], project_file_path)
        return data["root"]

    @classmethod
    def save_xml_file(cls, project_file_path, info_dict):
        if info_dict is None:
            return False
        if "asw_component" not in info_dict:
            return False
        ProjectXmlInfoHandler.to_rel_paths(info_dict, project_file_path)
        xml_file_path = os.path.join(os.path.dirname(project_file_path), "vcos_project.xml")
        try:
            root = ET.Element("root")
            cls.dict_to_xml(root, info_dict)
            xml_data = ET.ElementTree(root)
            xml_data.write(xml_file_path, encoding="utf-8", xml_declaration=True)
            dom = minidom.parse(xml_file_path)
            formatted_xml = dom.toprettyxml(indent="    ")

            with open(xml_file_path, "w", encoding="utf-8") as file:
                file.write(formatted_xml)
            return True
        except Exception:
            return False

    @classmethod
    def to_abs_paths(cls, info_dict, project_path):
        if "asw_component" in info_dict and info_dict["asw_component"]:
            ProjectXmlInfoHandler.asw_arxml_path_to_abs_paths_converter(info_dict["asw_component"], project_path)

    @classmethod
    def asw_arxml_path_to_abs_paths_converter(cls, asw_info_dict, project_path):
        """
        递归方法优化config_path等工程配置的路径转化
        """
        if not asw_info_dict:
            asw_info_dict = {}
            return

        file_func = PathConverter_Adaptor.to_abs
        for key, value in asw_info_dict.items():
            asw_info_dict[key] = file_func(asw_info_dict[key], project_path)

    @classmethod
    def to_rel_paths(cls, info_dict, project_path):
        if "asw_component" in info_dict:
            if not info_dict["asw_component"]:
                info_dict["asw_component"] = {}
            else:
                ProjectXmlInfoHandler.asw_arxml_path_to_rel_paths_converter(info_dict["asw_component"], project_path)

    @classmethod
    def asw_arxml_path_to_rel_paths_converter(cls, asw_component, project_path):
        """
        递归方法优化config_path等工程配置的路径转化
        """
        func = PathConverter_Adaptor.to_rel

        if asw_component is None:
            asw_component = {}
            return

        for key, value in asw_component.items():
            if asw_component[key] and os.path.exists(asw_component[key]):
                asw_component[key] = func(asw_component[key], project_path)
