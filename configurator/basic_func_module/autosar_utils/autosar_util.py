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
import os
import gc
import copy
import psutil
import weakref
from typing import List, Dict, Union, Optional
from lxml import etree
from xml.dom import minidom
from io import StringIO
from multiprocessing import Pool
from autosar44 import autosar44
from basic_func_module.autosar_utils import utils, types
from basic_func_module.base_logger import logger
from basic_func_module.autosar_utils.fields_type_3950_patch import FIELDSType3950Patch


class Register:

    @classmethod
    def init(cls):
        FIELDSType3950Patch.init()
        cls.init_record_mothod_register()
        cls.init_identifier_property_register()

    @staticmethod
    def register_object_method(obj, name=""):
        """
        Mount a dynamic method to an object.
        """

        def register_wrapper(method):
            method_name = name
            if name == "":
                method_name = method.__name__
            setattr(obj, method_name, method)
            return method

        return register_wrapper

    @staticmethod
    def remove_tag(tag):
        if not AutosarUtil.ar_tags.get(tag):
            AutosarUtil.ar_tags.pop(tag, None)

    @staticmethod
    def remove_path(path):
        if not AutosarUtil.ar_paths.get(path):
            AutosarUtil.ar_paths.pop(path, None)

    @staticmethod
    def recursive_update_path(root_id, container, old_path, new_path):
        containers = getattr(container, "SUB_CONTAINERS", getattr(container, "CONTAINERS", ""))
        for container_value in getattr(containers, "ECUC_CONTAINER_VALUE", []):
            short_name = getattr(getattr(container_value, "SHORT_NAME", ""), "valueOf_")
            if not short_name:
                continue
            old_path_tmp = f"{old_path}/{short_name}"
            new_path_tmp = f"{new_path}/{short_name}"
            Register.update_path(container_value, root_id, old_path_tmp, new_path_tmp)

    @staticmethod
    def update_path(container, root_id, old_path, new_path):
        obj = AutosarUtil.ar_paths.get(old_path, {}).pop(root_id, None)
        if obj is None:
            return None
        if len(AutosarUtil.ar_paths.get(old_path, {})) == 0:
            AutosarUtil.ar_paths.pop(old_path, None)
        if new_path not in AutosarUtil.ar_paths:
            AutosarUtil.ar_paths[new_path] = weakref.WeakValueDictionary()
            obj.finalize = weakref.finalize(obj, Register.remove_path, path=new_path)
        old_obj = AutosarUtil.ar_paths[new_path].get(root_id)
        if old_obj and hasattr(old_obj, "finalize"):
            old_obj.finalize.detach()
        AutosarUtil.ar_paths[new_path][root_id] = obj
        Register.recursive_update_path(root_id, container, old_path, new_path)
        return obj

    @staticmethod
    def set_value(identifier, name):
        if name is None:
            identifier.__dict__["valueOf_"] = name
            return
        first_call = True
        if not identifier.valueOf_:
            identifier.__dict__["valueOf_"] = name
        else:
            first_call = False
        parent = identifier.get_parent()
        if parent is None:
            return
        if parent.__dict__.get("SHORT_NAME") is None:
            return
        root_id = id(identifier.get_root())
        old_path = None
        if not first_call:
            old_path = identifier.get_path()
            identifier.__dict__["valueOf_"] = name
        if first_call and not AutosarUtil.ar_index:
            return
        new_path = identifier.get_path()
        if old_path and old_path in AutosarUtil.ar_paths:
            obj = Register.update_path(parent, root_id, old_path, new_path)
            if obj is None:
                return
            if obj != parent:
                logger.debug("parent inconsistency!")
        else:
            if new_path not in AutosarUtil.ar_paths:
                AutosarUtil.ar_paths[new_path] = weakref.WeakValueDictionary()
                parent.finalize = weakref.finalize(parent, Register.remove_path, path=new_path)
            old_obj = AutosarUtil.ar_paths[new_path].get(root_id)
            if old_obj and hasattr(old_obj, "finalize"):
                old_obj.finalize.detach()
            AutosarUtil.ar_paths[new_path][root_id] = parent

    @staticmethod
    def get_value(identifier):
        return identifier.__dict__.get("valueOf_")

    @staticmethod
    def get_tag(obj):
        if "original_tagname_" not in obj.__dict__:
            return None
        return obj.__dict__["original_tagname_"]

    @staticmethod
    def set_tag(obj, tag):
        obj.__dict__["original_tagname_"] = tag
        if not AutosarUtil.ar_index:
            return
        if tag is None:
            return
        if tag not in AutosarUtil.ar_tags:
            AutosarUtil.ar_tags[tag] = {}
        parent = obj.get_parent()
        if parent is None:
            return
        root_id = id(obj.get_root())
        if root_id not in AutosarUtil.ar_tags[tag]:
            AutosarUtil.ar_tags[tag][root_id] = weakref.WeakKeyDictionary()
            weakref.finalize(obj, Register.remove_tag, tag=tag)
        AutosarUtil.ar_tags[tag][root_id][obj] = None

    @staticmethod
    def get_parent(obj):
        if "parent_object_" not in obj.__dict__:
            return None
        return obj.__dict__["parent_object_"]

    @staticmethod
    def set_parent(obj, parent):
        obj.__dict__["parent_object_"] = parent
        if not AutosarUtil.ar_index:
            return
        if parent is None:
            return
        tag = obj.__dict__.get("original_tagname_")
        if tag is not None:
            Register.set_tag(obj, tag)
        short_name = obj.__dict__.get("valueOf_")
        if short_name is not None:
            Register.set_value(obj, short_name)

    @staticmethod
    def init_record_mothod_register():
        for obj in autosar44.__dict__.values():
            if not hasattr(obj, "build"):
                continue
            _build = obj.build
            varnames = _build.__code__.co_varnames
            if varnames[0] == "self" and varnames[1] == "node":

                def wrapper_build(*args, build=_build, parent=None, **kwargs):
                    if parent and args[0].get_parent() is None:
                        Register.set_parent(args[0], parent)
                    res = build(*args, **kwargs)
                    if not AutosarUtil.ar_index:
                        return res
                    tag = args[1].tag.split("}")[-1]
                    root_id = id(args[0].get_root())
                    if tag == "AUTOSAR":
                        AutosarUtil.ar_root_ids[root_id] = args[0]
                    elif tag == "SHORT-NAME":
                        short_name = args[1].text
                        parent_path = args[0].get_path()
                        if parent_path == "/":
                            path = f"/{short_name}"
                        else:
                            path = f"{parent_path}/{short_name}"
                        parent = res.get_parent()
                        if path not in AutosarUtil.ar_paths:
                            AutosarUtil.ar_paths[path] = weakref.WeakValueDictionary()
                            parent.finalize = weakref.finalize(parent, Register.remove_path, path=path)
                        if root_id not in AutosarUtil.ar_paths[path]:
                            AutosarUtil.ar_paths[path][root_id] = parent
                        else:
                            logger.debug(f"{path} is duplicate!")
                    return res

                setattr(obj, "build", wrapper_build)
            _init = obj.__init__
            varnames = _init.__code__.co_varnames
            if varnames[0] == "self":
                obj.original_tagname_ = property(Register.get_tag, Register.set_tag)
                obj.parent_object_ = property(Register.get_parent, Register.set_parent)

    @staticmethod
    def init_identifier_property_register():
        autosar44.IDENTIFIER.valueOf_ = property(Register.get_value, Register.set_value)  # type: ignore


class AutosarUtil:
    """
    This class provides a convenient way to import and export arxml.
    The arxml parsed by this class supports the ref path find function.
    Example:

        autosar = AutosarUtil.import_arxml("test.arxml")
        runnable = autosar.find("/ComponentTypes/Test_Swc/Test_Swc_InternalBehavior/Test_Swc_Init_Runnable")
    """

    Register.init()
    ar_index = True
    ar_packages = {}
    ar_tags = {}
    ar_paths = {}
    ar_root_ids = weakref.WeakValueDictionary()

    NAME_SPACES = {"AR": "http://autosar.org/schema/r4.0"}
    TAG_PATTERN = autosar44.Tag_pattern_  # type: ignore
    TAG_CLASS_MAPPING = {
        "AUTOSAR": autosar44.AUTOSAR,  # type: ignore
        "AR_PACKAGE": autosar44.AR_PACKAGE,  # type: ignore
        "ECUC-CONTAINER-VALUE": autosar44.ECUC_CONTAINER_VALUE,  # type: ignore
    }
    EXPOTED_TAG = ["AR_PACKAGE", "ECUC_MODULE_CONFIGURATION_VALUES", "ECUC_CONTAINER_VALUE"]
    EXPOTED_FLAG = "VCOS:ExportedElementRoot"

    @staticmethod
    @Register.register_object_method(autosar44, "parsexml_")
    def _parsexml(infile, parser=None, **kwargs):
        if parser is None:
            # Use the lxml ElementTree compatible parser so that, e.g.,
            #   we ignore comments.
            try:
                parser = etree.ETCompatXMLParser(remove_blank_text=True, recover=True)
            except AttributeError:
                # fallback to xml.etree
                parser = etree.XMLParser()
        try:
            if isinstance(infile, os.PathLike):
                infile = os.path.join(infile)
        except AttributeError:
            pass
        doc = etree.parse(infile, parser=parser, **kwargs)
        return doc

    @staticmethod
    @Register.register_object_method(autosar44, "parsexmlstring_")
    def _parsexmlstring(instring: str, parser=None, **kwargs):
        if parser is None:
            # Use the lxml ElementTree compatible parser so that, e.g.,
            #   we ignore comments.
            try:
                parser = etree.ETCompatXMLParser(remove_blank_text=True, recover=True)
            except AttributeError:
                # fallback to xml.etree
                parser = etree.XMLParser()
        element = etree.fromstring(instring.encode(encoding="utf-8"), parser=parser, **kwargs)
        return element

    @classmethod
    def parse_arxml(cls, path, using_index=True, saving_node=True):
        """
        Parse arxml and return AUTOSAR object.
        """
        with cls.index_guard(using_index, saving_node):
            autosar = autosar44.parse(path, silence=True, print_warnings=True)
            return autosar

    @classmethod
    def parse_arxml_string(cls, string, using_index=True, saving_node=True):
        """
        Parse arxml and return AUTOSAR object.
        """
        with cls.index_guard(using_index, saving_node):
            autosar = autosar44.parseString(string, silence=True, print_warnings=True)
            return autosar

    @staticmethod
    def create_value(valueOf):
        value = autosar44.VERBATIM_STRING(valueOf_=valueOf)
        return value

    @staticmethod
    def save_arxml(autosar, path):
        dir_name = os.path.dirname(os.path.abspath(path))
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
        utils.convert_arxml_string_escape_characters(autosar)
        arxml_string = AutosarUtil.get_arxml_string(autosar)
        dom = minidom.parseString(arxml_string)
        pretty_xml_as_string = dom.toprettyxml(indent="  ")
        with open(path, "w+", encoding="utf-8") as f:
            f.write(pretty_xml_as_string)

        return True

    @staticmethod
    def class_to_xml(autosar):
        utils.convert_arxml_string_escape_characters(autosar)
        arxml_string = AutosarUtil.get_arxml_string(autosar)
        dom = minidom.parseString(arxml_string)
        pretty_xml_as_string = dom.toprettyxml(indent="  ")
        return pretty_xml_as_string

    @staticmethod
    def get_arxml_string(autosar, is_root=True) -> str:
        str_io = StringIO()
        namespaceprefix = ""
        namespacedef = ""
        if is_root:
            str_io.write('<?xml version="1.0" encoding="utf-8"?>\n')
            namespacedef = (
                'xmlns="http://autosar.org/schema/r4.0" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xsi:schemaLocation="http://autosar.org/schema/r4.0 AUTOSAR_00046.xsd"'
            )
        autosar.export(str_io, 0, namespaceprefix, namespacedef, pretty_print=False)
        ret = str_io.getvalue()
        str_io.close()
        return ret

    @classmethod
    def get_arxml_file_from_path(cls, arxml_path):
        """ "
        load and parse all ARXML files under the arxml_path
        """
        # get all arxml file path
        arxml_file_list = []
        if not os.path.exists(arxml_path):
            return arxml_file_list
        for dirpath, _, filenames in os.walk(arxml_path):
            for filename in filenames:
                if filename.split(".")[-1] == "arxml":
                    arxml_file_list.append(os.path.join(dirpath, filename))
        return arxml_file_list

    @classmethod
    def open_index(cls):
        cls.ar_index = True

    @classmethod
    def close_index(cls):
        cls.ar_index = False

    @classmethod
    def index_guard(cls, using_index=False, saving_node=False):

        class IndexGuard:

            def __init__(self, using_index, saving_node):
                self.using_index = using_index
                self.saving_node = saving_node

            def __enter__(self):
                if not self.using_index:
                    AutosarUtil.close_index()
                if not self.saving_node:
                    autosar44.SaveElementTreeNode = False  # type: ignore

            def __exit__(self, exc_type, exc_val, exc_tb):
                AutosarUtil.open_index()
                autosar44.SaveElementTreeNode = True  # type: ignore

        return IndexGuard(using_index, saving_node)

    @classmethod
    def gc_guard(cls):

        class GCGuard:

            def __init__(self):
                self.threshold = gc.get_threshold()

            def __enter__(self):
                gc.collect()
                gc.set_threshold(0)
                gc.disable()

            def __exit__(self, exc_type, exc_val, exc_tb):
                gc.set_threshold(*self.threshold)
                gc.collect()
                gc.enable()

        return GCGuard()

    @classmethod
    def trigger_gc(cls):
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            gc.collect(2)
        elif memory.percent > 60:
            gc.collect(1)
        elif memory.percent > 30:
            gc.collect(0)

    @classmethod
    def update_autosar(cls, autosar_obj, using_index=True, saving_node=True):
        arxml_string = cls.get_arxml_string(autosar_obj)
        with cls.index_guard(using_index, saving_node):
            autosar_obj = cls.parse_arxml_string(arxml_string)
        return autosar_obj

    @classmethod
    def get_component_and_arxml_file_path(cls, service_arxml_file, asw_autosar_class):
        component_arxml_path_dict_info = {}
        sw_component_types = asw_autosar_class.find_nodes("APPLICATION-SW-COMPONENT-TYPE")
        sw_component_types += asw_autosar_class.find_nodes("ECU-ABSTRACTION-SW-COMPONENT-TYPE")
        sw_component_types += asw_autosar_class.find_nodes("SERVICE-SW-COMPONENT-TYPE")
        for sw_component_type in sw_component_types:
            sw_component_name = utils.get_short_name(sw_component_type)
            component_arxml_path_dict_info.update({sw_component_name: service_arxml_file})
        return component_arxml_path_dict_info

    @classmethod
    def get_root_tag(cls, root_node):
        tag, root_class = None, None
        if root_node is None or not isinstance(root_node, etree._Element) or root_node.tag is None:
            return tag, root_class
        tag = cls.TAG_PATTERN.match(root_node.tag).groups()[-1]
        root_class = cls.TAG_CLASS_MAPPING.get(tag)
        return tag, root_class

    @classmethod
    def build_arxml_obj(cls, string, parent):
        using_index = True
        if parent is None:
            using_index = False
        with cls.index_guard(using_index):
            root_node = cls._parsexmlstring(string)
            root_tag, root_class = cls.get_root_tag(root_node)
            if root_class is None:
                return None
            root_obj = root_class.factory()  # type: ignore
            root_obj.set_tag(root_tag)
            root_obj.build(root_node, parent=parent)
        return root_obj

    @classmethod
    def export_ecuc_arxml(cls, data):
        """
        Export AUTOSAR ECUC objects as ARXML strings.
        """
        return cls.export_arxml(data)

    @classmethod
    def export_arxml(cls, data) -> str:
        """
        Export AUTOSAR objects as ARXML strings.
        """
        if not isinstance(data, list):
            data = [data]
        elif len(data) == 0:
            return ""
        tag_set = set()
        for node in data:
            if node is None:
                continue
            cls.add_annotation_value(node, cls.EXPOTED_FLAG)
            tag_set.add(node.get_tag())
        node = cls.ar_root_ids.get(id(data[0].get_root()))
        arxml_str = cls.export_arxml_with_annotation(node, list(tag_set))
        for node in data:
            cls.remove_annotation_value(node, cls.EXPOTED_FLAG)
        return arxml_str

    @classmethod
    def export_arxml_with_annotation(cls, data, tag_list) -> str:
        if data is None:
            return ""
        try:
            arxml_str = cls.get_arxml_string(data)
            arxml_root = etree.fromstring(arxml_str.encode())
            if arxml_root is None:
                return ""
            keep_element_1 = {}
            for tag in tag_list:
                ar_tag = f".//AR:{tag}"
                elements = [e for e in arxml_root.iterfind(ar_tag, cls.NAME_SPACES)]
                for e in elements:
                    annotation_origins = e.iterfind("AR:ANNOTATIONS//AR:ANNOTATION-ORIGIN", cls.NAME_SPACES)
                    for annotation_origin in annotation_origins:
                        if annotation_origin is not None and annotation_origin.text == cls.EXPOTED_FLAG:
                            keep_element_1[e] = True
                            break
                    else:
                        keep_element_1[e] = False
            keep_element_2 = {}
            for tag in tag_list:
                ar_tag = f".//AR:{tag}"
                parent_tag = f"{{{cls.NAME_SPACES['AR']}}}{tag}"
                for e in reversed(keep_element_1):
                    keep = keep_element_1[e]
                    if not keep or e.tag != parent_tag:
                        continue
                    keep_element_2[e] = True
                    keep_element_2.update({ancestor: True for ancestor in e.iterancestors(parent_tag)})
                    keep_element_2.update({descendant: True for descendant in e.iterfind(ar_tag, cls.NAME_SPACES)})
            for e in keep_element_1.keys():
                if e in keep_element_2:
                    continue
                e.getparent().remove(e)
            export_arxml_str = etree.tostring(arxml_root, encoding="unicode")
            return export_arxml_str
        except Exception:
            logger.exception("copy ecuc arxml error!")
        return ""

    @classmethod
    def append_container_value_with_string(cls, parent, container_string):
        """
        Append ecuc container value ARXML strings to parent.
        """
        if parent is None or not isinstance(container_string, str) or len(container_string) == 0:
            return False, None
        ecuc_container_values = getattr(parent, "ECUC_CONTAINER_VALUE", None)
        if not isinstance(ecuc_container_values, list):
            return False, None
        open_pos = container_string.find("<SHORT-NAME>") + 12
        if open_pos == 11:
            return False, None
        close_pos = container_string.find("</SHORT-NAME>")
        if close_pos == -1:
            return False, None
        base_short_name = container_string[open_pos:close_pos]
        i = 0
        short_name = base_short_name
        parent_path = parent.get_path()
        while parent.find(f"{parent_path}/{short_name}"):
            i += 1
            short_name = f"{base_short_name}_{i}"
        container_string = container_string[:open_pos] + short_name + container_string[close_pos:]
        try:
            new_container_value = cls.build_arxml_obj(container_string, parent)
        except Exception:
            logger.debug(f"append_container_value: {parent_path}\n{container_string}")
            return False, None
        if new_container_value is None:
            return False, None
        cls.remove_annotation_value(new_container_value, cls.EXPOTED_FLAG)
        ecuc_container_values.append(new_container_value)
        return True, new_container_value

    @classmethod
    def append_container_values_with_string(cls, parent, arxml_string):
        arxml_data = cls.parse_arxml_string(arxml_string)
        return cls.append_container_values_with_object(parent, arxml_data)

    @classmethod
    def append_container_values_with_object(cls, parent, data):
        """
        Append ecuc container value objects to parent.
        """
        paths = cls.get_exported_arxml_paths(data)
        if len(paths) == 0:
            return []
        path_list = paths[0].split("/")
        if len(path_list) < 3:
            return []
        container_values = []
        for path in paths:
            container_value = data.find(path)
            container_value_str = cls.get_arxml_string(container_value, is_root=False)
            ret, new_container_node = cls.append_container_value_with_string(parent, container_value_str)
            if not ret:
                container_values.append(None)
                logger.warning(f"Append container value {utils.utils.get_short_name(container_value)} failed!")
                continue
            container_values.append(new_container_node)
        return container_values

    @classmethod
    def get_exported_arxml_paths(cls, data) -> List[str]:
        """
        Get path of exported AUTOSAR objects.
        """
        nodes = data.find_nodes("ANNOTATION-ORIGIN")
        paths = [node.get_path() for node in nodes if utils.get_valueOf(node) == cls.EXPOTED_FLAG]
        return paths

    @classmethod
    def refresh_containers(cls, data):
        if data.get_tag() != "CONTAINERS":
            logger.error("Invalid data")
            return False

        # Export ecuc container value string list
        arxml_str = cls.export_ecuc_arxml(data.ECUC_CONTAINER_VALUE)
        # Remove old objs
        for container_value in reversed(data.ECUC_CONTAINER_VALUE):
            cls.remove_container_value(data.ECUC_CONTAINER_VALUE, container_value)
        # Append new objs build from exported string
        res_list = cls.append_container_values_with_string(data, arxml_str)
        if res_list:
            return True
        else:
            logger.error("Error occurs when append new ECUC-CONTAINER-VALUE")
            return False

    @classmethod
    def validate_exported_arxml(cls, arxml_str: str, parent_def_ref="") -> bool:
        """
        Validate whether the exported ARXML string can be pasted.
        """
        if len(arxml_str) == 0:
            return False
        arxml_root = None
        # arxml_schema = None
        # try:
        #     from base_library.file_validation.arxml_validator import ArxmlFileValidator
        #     arxml_schema = getattr(ArxmlFileValidator(), "arxml_schema", None)
        # except Exception:
        #     pass
        try:
            arxml_root = etree.fromstring(arxml_str.encode())
            if arxml_root is None:
                return False
            # if arxml_schema:
            #     arxml_schema._clear_error_log()
            #     result = arxml_schema.validate(arxml_root)
            #     if result is False:
            #         return False
            iter = arxml_root.iterfind(".//AR:ANNOTATION-ORIGIN", cls.NAME_SPACES)
            ecuc_list = [e.getparent().getparent().getparent() for e in iter if cls.EXPOTED_FLAG == e.text]
            if len(ecuc_list) == 0:
                return False
            level = -1
            for ecuc in ecuc_list:
                if (def_ref := ecuc.find("AR:DEFINITION-REF", cls.NAME_SPACES)) is None:
                    return False
                if level == -1:
                    parent_def_ref_list = parent_def_ref.split("/")
                    def_ref_list = def_ref.text.split("/")
                    if parent_def_ref_list[:-1] != def_ref_list[:-1] and parent_def_ref_list != def_ref_list[:-1]:
                        return False
                    level = def_ref.text.count("/")
                elif level != def_ref.text.count("/"):
                    return False
        except Exception:
            return False
        return True

    @classmethod
    def merge_service_component_from_arxml(cls, service_arxml_folder):
        component_arxml_path_dict_info = {}
        service_arxml_file_list = AutosarUtil.get_arxml_file_from_path(service_arxml_folder)
        if len(service_arxml_file_list) < 1 or not os.path.exists(service_arxml_file_list[0]):
            return None, {}
        services_autosar = AutosarUtil.parse_arxml(service_arxml_file_list[0])
        for service_arxml_file in service_arxml_file_list[1:]:
            if os.path.exists(service_arxml_file):
                service_autosar = AutosarUtil.parse_arxml(service_arxml_file)
                try:
                    services_autosar.AR_PACKAGES.AR_PACKAGE[0].AR_PACKAGES.AR_PACKAGE.extend(
                        service_autosar.AR_PACKAGES.AR_PACKAGE[0].AR_PACKAGES.AR_PACKAGE
                    )
                    service_swc_component_info = AutosarUtil.get_component_and_arxml_file_path(
                        service_arxml_file, service_autosar
                    )
                    component_arxml_path_dict_info.update(service_swc_component_info)
                except Exception:
                    print(f"invalid Servcice component arxml {service_arxml_file}")
        services_autosar = AutosarUtil.update_autosar(services_autosar)
        cls.trigger_gc()
        return services_autosar, component_arxml_path_dict_info

    @classmethod
    def merge_all_asw_arxml(cls, asw_autosar_dict):
        asw_autosar = asw_autosar_dict.get("asw")
        platform_autosar = asw_autosar_dict.get("platform")
        services_autosar = asw_autosar_dict.get("service_component")
        if platform_autosar is None:
            return False
        try:
            asw_autosar_string = cls._merge_all_asw_arxml(asw_autosar, services_autosar, platform_autosar)
            asw_autosar_dict["asw"] = cls.parse_arxml_string(asw_autosar_string)
            cls.trigger_gc()
        except Exception as e:
            logger.exception(e)
            return False
        else:
            cls.trigger_gc()
        return True

    @classmethod
    def _merge_all_asw_arxml(cls, asw_autosar, services_autosar, platform_autosar):
        if asw_autosar and services_autosar:
            asw_autosar = cls.merge_autosar([asw_autosar, platform_autosar])
            merged_ar = asw_autosar.find("/AUTOSAR")
            if merged_ar is None:
                merged_ar = services_autosar.find("/AUTOSAR")
                asw_autosar.AR_PACKAGES.AR_PACKAGE.append(merged_ar)
            else:
                for service_swc in asw_autosar.find_nodes("SERVICE-SW-COMPONENT-TYPE"):
                    service_swc_ref = service_swc.get_path()
                    service_package_ref = "/".join(service_swc_ref.split("/")[:3])
                    old_service_package = asw_autosar.find(service_package_ref)
                    if old_service_package not in merged_ar.AR_PACKAGES.AR_PACKAGE:
                        continue
                    merged_ar.AR_PACKAGES.AR_PACKAGE.remove(old_service_package)
                for service_swc in services_autosar.find_nodes("SERVICE-SW-COMPONENT-TYPE"):
                    service_swc_ref = service_swc.get_path()
                    service_package_ref = "/".join(service_swc_ref.split("/")[:3])
                    new_service_package = services_autosar.find(service_package_ref)
                    if new_service_package in merged_ar.AR_PACKAGES.AR_PACKAGE:
                        continue
                    merged_ar.AR_PACKAGES.AR_PACKAGE.append(new_service_package)
        elif asw_autosar is None and services_autosar:
            asw_autosar = cls.merge_autosar([services_autosar, platform_autosar])
        elif asw_autosar and services_autosar is None:
            asw_autosar = cls.merge_autosar([asw_autosar, platform_autosar])
        asw_autosar_string = cls.get_arxml_string(asw_autosar)
        return asw_autosar_string

    @classmethod
    def merge_autosar(cls, autosars: List[object], need_merged_packages=None, using_index=True):
        merged_autosar = None
        if len(autosars) == 0:
            return merged_autosar
        merged_autosar_string = ""
        autosar_string_list = [AutosarUtil.get_arxml_string(autosar) for autosar in autosars]
        with Pool(1) as pool:
            p = psutil.Process(pid=pool._pool[0].pid)
            p.cpu_affinity([0])
            merged_autosar_string = pool.apply(cls._merge_autosar, args=(autosar_string_list, need_merged_packages))
        # merged_autosar_string = cls._merge_autosar(autosars, need_merged_packages)
        if merged_autosar_string:
            merged_autosar = cls.parse_arxml_string(merged_autosar_string, using_index)
        return merged_autosar

    @classmethod
    def _merge_autosar(cls, autosar_string_list: List[str], need_merged_packages=None):
        if len(autosar_string_list) == 0:
            return
        merged_autosar = autosar44.AUTOSAR()
        merged_autosar.AR_PACKAGES = autosar44.AR_PACKAGESType5()
        asw_package_dict = {}
        asw_element_dict = {}
        for autosar in autosar_string_list:
            if not autosar:
                continue
            try:
                autosar = cls.parse_arxml_string(autosar, False)
                for ar_package in autosar.AR_PACKAGES.AR_PACKAGE:
                    package_path = ar_package.get_path()
                    package_name = utils.get_short_name(ar_package)
                    if isinstance(need_merged_packages, list) and package_name not in need_merged_packages:
                        continue
                    asw_package = asw_package_dict.get(package_path)
                    if asw_package is None:
                        merged_autosar.AR_PACKAGES.AR_PACKAGE.append(ar_package)
                        asw_package_dict[package_path] = ar_package
                        cls.update_merged_package_info(ar_package, asw_package_dict, asw_element_dict)
                    else:
                        cls.merge_packages(asw_package, ar_package, asw_package_dict, asw_element_dict)
                        cls.merge_elements(asw_package, ar_package, asw_element_dict)
            except Exception as e:
                raise Exception(f"Merge {autosar.get_source_path()} Error!") from e
            finally:
                cls.trigger_gc()
        merged_autosar_string = cls.get_arxml_string(merged_autosar)
        return merged_autosar_string

    @classmethod
    def merge_module_arxml(cls, bsw_ecuc_arxml_list: List[object]):
        if len(bsw_ecuc_arxml_list) == 0:
            return
        bsw_ecuc_arxml_list = copy.deepcopy(bsw_ecuc_arxml_list)
        merged_bsw_ecuc_autosar = bsw_ecuc_arxml_list[0]
        for bsw_ecuc_obj in bsw_ecuc_arxml_list[1:]:
            try:
                merged_bsw_module_element = merged_bsw_ecuc_autosar.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS
                curr_bsw_module_element = bsw_ecuc_obj.AR_PACKAGES.AR_PACKAGE[0].ELEMENTS
                merged_bsw_module_element.ECUC_MODULE_CONFIGURATION_VALUES.extend(
                    curr_bsw_module_element.ECUC_MODULE_CONFIGURATION_VALUES
                )
            except Exception as e:
                module_name = utils.get_short_name(bsw_ecuc_obj.AR_PACKAGES.AR_PACKAGE[0])
                raise Exception(f"Merge {module_name} arxml files Error!") from e
        cls.update_autosar(merged_bsw_ecuc_autosar)
        return merged_bsw_ecuc_autosar

    @classmethod
    def parse_bsw_module_class_list(cls, bsw_obj):
        ecuc_module_dict = {}
        for ar_package in getattr(getattr(bsw_obj, "AR_PACKAGES", None), "AR_PACKAGE", []):
            module_cfg_objs = getattr(getattr(ar_package, "ELEMENTS", None), "ECUC_MODULE_CONFIGURATION_VALUES", [])
            for module_obj in module_cfg_objs:
                full_structure_autosar = autosar44.AUTOSAR()
                full_structure_autosar.AR_PACKAGES = cls.create_ar_packages(full_structure_autosar)
                ar_package = cls.create_ar_package(
                    short_name="ActiveEcuC",
                    elements=autosar44.ELEMENTSType2(),
                    parent=full_structure_autosar.AR_PACKAGES,
                )
                ar_package.ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES.append(module_obj)
                full_structure_autosar.AR_PACKAGES.AR_PACKAGE.append(ar_package)
                full_structure_autosar = cls.update_autosar(full_structure_autosar)
                ecuc_module_dict.update({utils.get_short_name(module_obj): full_structure_autosar})

        return ecuc_module_dict

    @classmethod
    def merge_arxml(
        cls, asw_autosars: Dict[str, object], arxml_files: List[str], need_merged_packages=None, using_index=True
    ):
        if len(arxml_files) == 0:
            return False, {}
        component_arxml_path_dict_info = {}
        merged_autosar_string = ""
        with Pool(1) as pool:
            p = psutil.Process(pid=pool._pool[0].pid)
            p.cpu_affinity([0])
            merged_autosar_string, component_arxml_path_dict_info = pool.apply(
                cls._merge_arxml, args=(arxml_files, need_merged_packages)
            )
        if merged_autosar_string:
            asw_autosars["asw"] = cls.parse_arxml_string(merged_autosar_string, using_index)
        return True, component_arxml_path_dict_info

    @classmethod
    def _merge_arxml(cls, arxml_files, need_merged_packages=None):
        merged_autosar = autosar44.AUTOSAR()
        merged_autosar.AR_PACKAGES = autosar44.AR_PACKAGESType5()
        asw_package_dict = {}
        asw_element_dict = {}
        component_arxml_path_dict_info = {}
        for arxml_file in arxml_files:
            if not os.path.exists(arxml_file):
                raise Exception(f"{arxml_file} file not exists!")
            autosar = cls.parse_arxml(arxml_file)
            try:
                for ar_package in autosar.AR_PACKAGES.AR_PACKAGE:
                    package_path = ar_package.get_path()
                    package_name = utils.get_short_name(ar_package)
                    if isinstance(need_merged_packages, list) and package_name not in need_merged_packages:
                        continue
                    asw_package = asw_package_dict.get(package_path)
                    if not asw_package:
                        merged_autosar.AR_PACKAGES.AR_PACKAGE.append(ar_package)
                        asw_package_dict[package_path] = ar_package
                        cls.update_merged_package_info(ar_package, asw_package_dict, asw_element_dict)
                    else:
                        cls.merge_packages(asw_package, ar_package, asw_package_dict, asw_element_dict)
                        cls.merge_elements(asw_package, ar_package, asw_element_dict)
                service_swc_component_info = AutosarUtil.get_component_and_arxml_file_path(arxml_file, autosar)
                component_arxml_path_dict_info.update(service_swc_component_info)
            except Exception as e:
                raise Exception(f"Merge {arxml_file} Error!") from e
            finally:
                cls.trigger_gc()
        merged_autosar_string = cls.get_arxml_string(merged_autosar)
        return merged_autosar_string, component_arxml_path_dict_info

    @classmethod
    def update_merged_package_info(cls, package, target_package_dict, target_element_dict):
        sub_packages = cls.get_subpackages(package)
        target_package_dict.update(map(lambda x: (x.get_path(), x), sub_packages))
        elements = cls.get_elements(package)
        target_element_dict.update(dict(map(lambda x: (x.get_path(), x), elements)))
        for sub_package in sub_packages:
            cls.update_merged_package_info(sub_package, target_package_dict, target_element_dict)

    @classmethod
    def merge_packages(cls, target_package, source_package, target_package_dict, target_element_dict):
        source_subpackages = cls.get_subpackages(source_package)
        for source_subpackage in source_subpackages:
            sub_package_path = source_subpackage.get_path()
            target_subpackage = target_package_dict.get(sub_package_path)
            if target_subpackage is None:
                if target_package.AR_PACKAGES is None:
                    target_package.AR_PACKAGES = autosar44.AR_PACKAGESType3()
                target_package.AR_PACKAGES.AR_PACKAGE.append(source_subpackage)
                target_package_dict[sub_package_path] = source_subpackage
                cls.update_merged_package_info(source_subpackage, target_package_dict, target_element_dict)
            else:
                cls.merge_packages(target_subpackage, source_subpackage, target_package_dict, target_element_dict)
                cls.merge_elements(target_subpackage, source_subpackage, target_element_dict)

    @classmethod
    def merge_elements(cls, target_package, source_package, target_element_dict):
        source_elements = cls.get_elements(source_package)
        for source_element in source_elements:
            if target_package.ELEMENTS is None:
                target_package.ELEMENTS = autosar44.ELEMENTSType2()
            element_path = source_element.get_path()
            object_name = type(source_element).__name__
            target_element_list = getattr(target_package.ELEMENTS, object_name)
            target_element = target_element_dict.get(element_path)
            if target_element is None:
                target_element_list.append(source_element)
                target_element_dict[element_path] = source_element
            elif object_name.endswith("SW_COMPONENT_TYPE"):
                source_arxml_path = source_element.get_source_path()
                target_arxml_path = target_element.get_source_path()
                # target_element_list.remove(target_element)
                raise Exception(
                    f"The <{element_path}>SWC in {source_arxml_path} and {target_arxml_path} is duplicated!"
                )
            else:
                pass
                # source_path = source_element.get_source_path()
                # target_path = target_element.get_source_path()
                # print(f"The {object_name}<{element_path}>in {source_path} and {target_path} is duplicated!")

    @staticmethod
    def get_subpackages(ar_package):
        if not hasattr(ar_package, "AR_PACKAGES"):
            return []
        if ar_package.AR_PACKAGES is None:
            return []
        return ar_package.AR_PACKAGES.AR_PACKAGE

    @staticmethod
    def get_elements(ar_package):
        elements = []
        if not hasattr(ar_package, "ELEMENTS"):
            return elements
        if ar_package.ELEMENTS is None:
            return elements
        interfaces = []
        interfaces.extend(ar_package.ELEMENTS.CLIENT_SERVER_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.MODE_SWITCH_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.NV_DATA_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.PARAMETER_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.PERSISTENCY_FILE_PROXY_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.PERSISTENCY_KEY_VALUE_DATABASE_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.PHM_HEALTH_CHANNEL_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.PHM_SUPERVISED_ENTITY_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.REST_SERVICE_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.SENDER_RECEIVER_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.SERVICE_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.TIME_SYNCHRONIZATION_MASTER_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.TIME_SYNCHRONIZATION_PURE_LOCAL_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.TIME_SYNCHRONIZATION_SLAVE_INTERFACE)
        interfaces.extend(ar_package.ELEMENTS.TRIGGER_INTERFACE)

        sw_component_types = []
        sw_component_types.extend(ar_package.ELEMENTS.ADAPTIVE_APPLICATION_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.APPLICATION_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.COMPLEX_DEVICE_DRIVER_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.ECU_ABSTRACTION_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.NV_BLOCK_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.PARAMETER_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.SENSOR_ACTUATOR_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.SERVICE_PROXY_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.SERVICE_SW_COMPONENT_TYPE)
        sw_component_types.extend(ar_package.ELEMENTS.COMPOSITION_SW_COMPONENT_TYPE)

        data_types = []
        data_types.extend(ar_package.ELEMENTS.APPLICATION_ARRAY_DATA_TYPE)
        data_types.extend(ar_package.ELEMENTS.APPLICATION_ASSOC_MAP_DATA_TYPE)
        data_types.extend(ar_package.ELEMENTS.APPLICATION_PRIMITIVE_DATA_TYPE)
        data_types.extend(ar_package.ELEMENTS.APPLICATION_RECORD_DATA_TYPE)
        data_types.extend(ar_package.ELEMENTS.IMPLEMENTATION_DATA_TYPE)

        elements.extend(interfaces)
        elements.extend(sw_component_types)
        elements.extend(data_types)
        elements.extend(ar_package.ELEMENTS.UNIT)
        elements.extend(ar_package.ELEMENTS.COMPU_METHOD)
        elements.extend(ar_package.ELEMENTS.DATA_CONSTR)
        elements.extend(ar_package.ELEMENTS.SW_BASE_TYPE)
        elements.extend(ar_package.ELEMENTS.DATA_TYPE_MAPPING_SET)
        elements.extend(ar_package.ELEMENTS.SWC_IMPLEMENTATION)
        elements.extend(ar_package.ELEMENTS.MODE_DECLARATION_GROUP)
        return elements

    @classmethod
    def remove_connector(cls, ar, short_name):
        ar_ecu_compositions = ar.find_nodes("COMPOSITION-SW-COMPONENT-TYPE")
        if len(ar_ecu_compositions) == 0:
            return
        for ar_ecu_composition in ar_ecu_compositions:
            if not ar_ecu_composition.CONNECTORS:
                break
            for assembly_connector in ar_ecu_composition.CONNECTORS.ASSEMBLY_SW_CONNECTOR:
                if assembly_connector.SHORT_NAME.valueOf_ == short_name:
                    ar_ecu_composition.CONNECTORS.ASSEMBLY_SW_CONNECTOR.remove(assembly_connector)
                    break

    @classmethod
    def remove_module_value(cls, ecuc_module_value: list, value):
        cls.remove_value_from_list(ecuc_module_value, value)
        if hasattr(value, "CONTAINERS") and value.CONTAINERS is None:
            return
        containers = value.CONTAINERS.ECUC_CONTAINER_VALUE
        for container in containers:
            cls.update_ar_paths_and_ar_tags(containers, container)
            cls.traversal_container(container)

    @classmethod
    def traversal_container(cls, containers):
        if hasattr(containers, "SUB_CONTAINERS") and containers.SUB_CONTAINERS is None:
            return
        sub_containers = containers.SUB_CONTAINERS.ECUC_CONTAINER_VALUE
        if sub_containers:
            for sub_container in sub_containers:
                cls.update_ar_paths_and_ar_tags(sub_containers, sub_container)
                cls.traversal_sub_container(sub_container)

    @classmethod
    def traversal_sub_container(cls, containers):
        if hasattr(containers, "SUB_CONTAINERS") and containers.SUB_CONTAINERS is None:
            return
        sub_containers = containers.SUB_CONTAINERS.ECUC_CONTAINER_VALUE
        if sub_containers:
            for sub_container in sub_containers:
                cls.update_ar_paths_and_ar_tags(sub_containers, sub_container)
                cls.traversal_sub_container(sub_container)

    @classmethod
    def update_ar_paths_and_ar_tags(cls, value_list: list, value):
        if value in value_list:
            tag = value.get_tag()
            old_path = value.get_path()
            root_id = id(value.get_root())
            cls.ar_paths.get(old_path, {}).pop(root_id, None)
            if len(cls.ar_paths.get(old_path, {})) == 0:
                cls.ar_paths.pop(old_path, None)
            tags = cls.ar_tags.get(tag, {}).get(root_id, {})
            if value in tags:
                tags.pop(value)
            if len(cls.ar_tags.get(tag, {}).get(root_id, set())) == 0:
                cls.ar_tags.get(tag, {}).pop(root_id, None)

    @classmethod
    def remove_container_value(cls, ecuc_container_value: list, value):
        cls.remove_value_from_list(ecuc_container_value, value)

    @classmethod
    def remove_value_from_list(cls, value_list: list, value):
        if value in value_list:
            if hasattr(value, "finalize"):
                value.finalize.detach()
            value_list.remove(value)
            tag = value.get_tag()
            old_path = value.get_path()
            root_id = id(value.get_root())
            cls.ar_paths.get(old_path, {}).pop(root_id, None)
            if len(cls.ar_paths.get(old_path, {})) == 0:
                cls.ar_paths.pop(old_path, None)
            tags = cls.ar_tags.get(tag, {}).get(root_id, {})
            if value in tags:
                tags.pop(value)
            if len(cls.ar_tags.get(tag, {}).get(root_id, set())) == 0:
                cls.ar_tags.get(tag, {}).pop(root_id, None)

    @classmethod
    def remove_node_value(cls, values: list, value):
        if value not in values:
            return
        values.remove(value)
        root_id = id(value.get_root())
        tag = value.get_tag()
        tags = cls.ar_tags.get(tag, {}).get(root_id, {})
        if value in tags:
            tags.pop(value)
        if len(cls.ar_tags.get(tag, {})) == 0:
            cls.ar_tags.pop(tag, None)
        if not utils.get_short_name(value):
            return
        path = value.get_path()
        cls.ar_paths.get(path, {}).pop(root_id, None)
        if len(cls.ar_paths.get(path, {})) == 0:
            cls.ar_paths.pop(path, None)

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def find(node, path: str, local=True) -> Union[List[object], object, None]:
        """
        查找ARXML中的所有满足path的short name, 返回查找到的AUTOSAR对象。
        node: 待查找的AUTOSAR对象。
        path: ARXML中short name组成的路径, 例如: /ActiveEcuC/Rte.
        local: TRUE, 只在当前node所属的ARXML中查找; FALSE, 在所有被加载的ARXML中查找。
        """
        if not path:
            return None
        ret = None
        if path[0] == "/" and not local:
            package_name = path.split("/")[1]
            if package_name != "" and package_name in AutosarUtil.ar_packages:
                package_dict = AutosarUtil.ar_packages[package_name]
                rets = []
                for package in package_dict.values():
                    ret = AutosarUtil.get_by_path(package, path, True)
                    if ret:
                        rets.append(ret)
                if len(rets) != 0:
                    ret = rets
        if ret is None:
            ret = AutosarUtil.get_by_path(node, path, local)
        return ret

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_root(node):
        xml_node = node.gds_elementtree_node_
        if xml_node is None:
            while node is not None:
                if isinstance(node, autosar44.AUTOSAR):
                    break
                if node.parent_object_ is None:
                    # logger.debug("Warning: parent_object_ is None!")
                    break
                node = node.parent_object_
                xml_node = node.gds_elementtree_node_
                if xml_node is not None:
                    break
            if xml_node is None:
                return None
        root_tree = xml_node.getroottree()
        root = root_tree.getroot()
        return root

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_path(node):
        pahts = []
        while node is not None:
            short_name = utils.get_short_name(node)
            node = node.parent_object_
            if short_name:
                pahts.append(short_name)
        pahts.reverse()
        return "/" + "/".join(pahts)

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_parent(node):
        return node.parent_object_

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_path_parent(node):
        parent = None
        while node is not None:
            node = node.parent_object_
            short_name = utils.get_short_name(node)
            if short_name:
                parent = node
                break
        return parent

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def set_parent(node, parent):
        node.parent_object_ = parent

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_tag(node):
        return node.original_tagname_

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def set_tag(node, tag):
        node.original_tagname_ = tag

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_errors(node) -> List[str]:
        return node.gds_collector_.get_messages()

    @staticmethod
    def get_by_path(node, path, local) -> Union[List[object], object, None]:
        if len(path) == 0:
            return None
        abs_path = ""
        if path[0] == "/":
            abs_path = path
        elif path.startswith("./"):
            abs_path = f"{node.get_path()}{path[1:]}"
        ret = None
        if local:
            root_id = id(node.get_root())
            ret = AutosarUtil.ar_paths.get(abs_path, {}).get(root_id)
        else:
            ret = []
            for root_id in AutosarUtil.ar_root_ids:
                _ret = AutosarUtil.ar_paths.get(abs_path, {}).get(root_id)
                if _ret is None:
                    continue
                ret.append(_ret)
            if len(ret) == 0:
                ret = None
        return ret

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def find_nodes(node, tag: str, local=True) -> list:
        """
        查找ARXML中的所有tag, 返回一个列表包含所有tag的AUTOSAR对象。
        node: 待查找的AUTOSAR对象。
        tag: ARXML中的tag, 例如: AR-PACKAGES.
        local: TRUE, 只在当前node所属的ARXML中查找; FALSE, 在所有被加载的ARXML中查找。
        """
        nodes = AutosarUtil.get_by_tag(node, tag, local)
        return nodes

    @staticmethod
    def get_by_tag(node, tag, local) -> list:
        nodes = []
        if local:
            root_id = id(node.get_root())
            nodes = [node for node in AutosarUtil.ar_tags.get(tag, {}).get(root_id, [])]
        else:
            nodes = [node for subnode in AutosarUtil.ar_tags.get(tag, {}).values() for node in subnode]
        return nodes

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_source_path(node):
        if hasattr(node, "gds_elementtree_node_") and hasattr(node.gds_elementtree_node_, "base"):
            return node.gds_elementtree_node_.base
        else:
            return None

    @staticmethod
    @Register.register_object_method(autosar44.GeneratedsSuper)
    def get_source_line(node):
        if hasattr(node, "gds_elementtree_node_") and hasattr(node.gds_elementtree_node_, "sourceline"):
            return node.gds_elementtree_node_.sourceline
        else:
            return -1

    @classmethod
    def parse_multi_textual_param_value(cls, container_dict, param_value):
        param_name = utils.get_definition_ref(param_value).split("/")[-1]
        if param_name not in container_dict:
            container_dict[param_name] = {}
            container_dict[param_name]["DefinitionRef"] = utils.get_definition_ref(param_value)
            container_dict[param_name]["Value"] = utils.get_value(param_value)
        else:
            if type(container_dict[param_name]["Value"]) is not list:
                container_dict[param_name]["Value"] = [container_dict[param_name]["Value"]]
            container_dict[param_name]["Value"].append(utils.get_value(param_value))

    @classmethod
    def parse_multi_reference_value(cls, container_dict, reference_value):
        reference_name = utils.get_definition_ref(reference_value).split("/")[-1]
        if reference_name not in container_dict:
            container_dict[reference_name] = {}
            container_dict[reference_name]["DefinitionRef"] = utils.get_definition_ref(reference_value)
            container_dict[reference_name]["ValueRef"] = utils.get_value_ref(reference_value)
        else:
            if type(container_dict[reference_name]["ValueRef"]) is not list:
                container_dict[reference_name]["ValueRef"] = [container_dict[reference_name]["ValueRef"]]
            container_dict[reference_name]["ValueRef"].append(utils.get_value_ref(reference_value))
        container_dict[reference_name]["reference_item_path"] = reference_value.get_path() + "/" + reference_name

    @classmethod
    def parse_multi_instance_reference_value(cls, container_dict, reference_value):
        reference_name = utils.get_definition_ref(reference_value).split("/")[-1]
        if reference_name not in container_dict:
            container_dict[reference_name] = {}
            container_dict[reference_name]["DefinitionRef"] = utils.get_definition_ref(reference_value)
            container_dict[reference_name]["ValueIRef"] = utils.get_value_iref(reference_value)
        else:
            if type(container_dict[reference_name]["ValueIRef"]) is not list:
                container_dict[reference_name]["ValueIRef"] = [container_dict[reference_name]["ValueIRef"]]
            container_dict[reference_name]["ValueIRef"].append(utils.get_value_iref(reference_value))
        container_dict[reference_name]["reference_item_path"] = reference_value.get_path() + "/" + reference_name

    @classmethod
    def to_container_value_dict(cls, container):
        container_dict = {}
        container_dict["DefinitionRef"] = utils.get_definition_ref(container)

        parameter_values = container.PARAMETER_VALUES
        if parameter_values:
            for add_info_param_value in parameter_values.ECUC_ADD_INFO_PARAM_VALUE:
                pass
            for numerical_param_value in parameter_values.ECUC_NUMERICAL_PARAM_VALUE:
                param_name = utils.get_definition_ref(numerical_param_value).split("/")[-1]
                container_dict[param_name] = {}
                container_dict[param_name]["DefinitionRef"] = utils.get_definition_ref(numerical_param_value)
                container_dict[param_name]["Value"] = utils.get_numerical_param_value(numerical_param_value)
            for textual_param_value in parameter_values.ECUC_TEXTUAL_PARAM_VALUE:
                cls.parse_multi_textual_param_value(container_dict, textual_param_value)
                # param_name = utils.get_definition_ref(textual_param_value).split("/")[-1]
                # container_dict[param_name] = {}
                # container_dict[param_name]["Value"] = utils.get_value(textual_param_value)

        reference_values = container.REFERENCE_VALUES
        if reference_values:
            for instance_reference_value in reference_values.ECUC_INSTANCE_REFERENCE_VALUE:
                cls.parse_multi_instance_reference_value(container_dict, instance_reference_value)
            for reference_value in reference_values.ECUC_REFERENCE_VALUE:
                cls.parse_multi_reference_value(container_dict, reference_value)
                # reference_name = utils.get_definition_ref(reference_value).split("/")[-1]
                # container_dict[reference_name] = {}
                # container_dict[reference_name]["ValueRef"] = utils.get_value_ref(reference_value)

        sub_containers = container.SUB_CONTAINERS
        if sub_containers:
            for sub_container in sub_containers.ECUC_CONTAINER_VALUE:
                container_dict[utils.get_short_name(sub_container)] = cls.to_container_value_dict(sub_container)

        return container_dict

    @classmethod
    def to_ecuc_module_configuration_values_dict(cls, module):
        module_dict = {}
        module_dict["DefinitionRef"] = utils.get_definition_ref(module)

        ecuc_container_value = getattr(getattr(module, "CONTAINERS", object()), "ECUC_CONTAINER_VALUE", [])
        for container in ecuc_container_value:
            module_dict[utils.get_short_name(container)] = cls.to_container_value_dict(container)

        return module_dict

    @classmethod
    def to_bsw_dict(cls, autosar):
        bsw_dict = {"ArPackages": {}}
        for ar_package in autosar.AR_PACKAGES.AR_PACKAGE:
            ar_package_dict = {}
            ar_package_name = utils.get_short_name(ar_package)

            for module in ar_package.ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES:
                ar_package_dict[utils.get_short_name(module)] = cls.to_ecuc_module_configuration_values_dict(module)

            bsw_dict["ArPackages"][ar_package_name] = ar_package_dict

        return bsw_dict

    @classmethod
    def create_container_value(cls, container_name, conf_def, parent, guess_name=None):
        container_value = autosar44.ECUC_CONTAINER_VALUE()
        container_value.SUB_CONTAINERS = autosar44.SUB_CONTAINERSType()
        container_value.SUB_CONTAINERS.set_parent(container_value)
        base_name = container_name
        tag = parent.get_tag()
        parent_container_value = []
        if tag == "ECUC-MODULE-CONFIGURATION-VALUES":
            if parent.CONTAINERS is None:
                parent.CONTAINERS = autosar44.CONTAINERSType2082()
                parent.CONTAINERS.set_parent(parent)
                parent.CONTAINERS.set_tag("CONTAINERS")
            container_value.set_parent(parent.CONTAINERS)
            parent_container_value = parent.CONTAINERS.ECUC_CONTAINER_VALUE
        elif tag == "ECUC-CONTAINER-VALUE":
            if parent.SUB_CONTAINERS is None:
                parent.SUB_CONTAINERS = autosar44.SUB_CONTAINERSType()
                parent.SUB_CONTAINERS.set_parent(parent)
                parent.SUB_CONTAINERS.set_tag("SUB-CONTAINERS")
            container_value.set_parent(parent.SUB_CONTAINERS)
            parent_container_value = parent.SUB_CONTAINERS.ECUC_CONTAINER_VALUE
        conf_tag = conf_def.get_tag()
        utils.set_definition_ref(container_value, conf_tag, conf_def.get_path())
        if conf_tag == "ECUC-PARAM-CONF-CONTAINER-DEF":
            cls.create_param_conf_container(conf_def, container_value)
        elif conf_tag == "ECUC-CHOICE-CONTAINER-DEF":
            pass
        else:
            print("Unprocessed branch")
        if guess_name:
            utils.set_short_name(container_value, guess_name)
        else:
            cls.set_unique_name(parent, container_value, base_name)
        container_value.set_tag("ECUC-CONTAINER-VALUE")
        container_value.SUB_CONTAINERS.set_tag("SUB-CONTAINERS")
        parent_container_value.append(container_value)
        return container_value

    @classmethod
    def create_container_by_path(cls, module_bsw_obj, module_mod_obj, eucu_path: str, mod_path: str) -> bool:
        if not module_bsw_obj or not module_mod_obj:
            logger.error("create container in func in_param error!")
            return False
        container_name = eucu_path.split("/")[-1]
        container_def_obj = module_mod_obj.find(mod_path)
        parent_path = "/".join(eucu_path.split("/")[:-1])
        parent_obj = module_bsw_obj.find(parent_path)
        if not parent_obj or not container_def_obj:
            logger.error("create container in get parent obj and container def error!")
            return False
        try:
            guess_name = cls.get_sub_container_guess_name(parent_obj, container_name, mod_path)
            cls.create_container_value(container_name, container_def_obj, parent_obj, guess_name)
        except Exception:
            logger.error("create container value in call interface error!")
            return False
        return True

    @classmethod
    def get_sub_container_guess_name(cls, parent_obj, base_name: str, mod_path: str):
        guess_name = base_name
        if not parent_obj:
            logger.error("get sub caontainer guess name error!")
            return guess_name
        child_name_set = set()

        if hasattr(parent_obj, "SUB_CONTAINERS") and parent_obj.SUB_CONTAINERS is not None:
            sub_containers = parent_obj.SUB_CONTAINERS.ECUC_CONTAINER_VALUE
            if sub_containers:
                for sub_container in sub_containers:
                    if not sub_container or utils.get_definition_ref(sub_container) != mod_path:
                        continue
                    sub_container_name = utils.get_short_name(sub_container)
                    child_name_set.add(sub_container_name)

        if hasattr(parent_obj, "CONTAINERS") and parent_obj.CONTAINERS is not None:
            sub_containers = parent_obj.CONTAINERS.ECUC_CONTAINER_VALUE
            if sub_containers:
                for sub_container in sub_containers:
                    if not sub_container or utils.get_definition_ref(sub_container) != mod_path:
                        continue
                    sub_container_name = utils.get_short_name(sub_container)
                    child_name_set.add(sub_container_name)
        i = 1
        while guess_name in child_name_set:
            guess_name = f"{base_name}_{i}"
            i += 1

        return guess_name

    @classmethod
    def set_unique_name(cls, parent, container_value, base_name):
        i = 1
        short_name = base_name
        parent_path = parent.get_path()
        while parent.find(f"{parent_path}/{short_name}"):
            short_name = f"{base_name}_{i:03}"
            i += 1
        utils.set_short_name(container_value, short_name)

    @classmethod
    def create_annotation_value(cls, label: Optional[str], origin_content: str):
        if label is not None:
            # TODO: 创建LABEL
            pass
        annotation_origin = autosar44.STRING(valueOf_=origin_content)
        new_annotation = autosar44.ANNOTATION(ANNOTATION_ORIGIN=annotation_origin)
        return new_annotation

    @classmethod
    def add_annotation_value(cls, parent, origin_content: str, label: Optional[str] = None):
        # If ANNOTATIONS tag is None, create ANNOTATIONS first
        if parent.ANNOTATIONS is None:
            parent.ANNOTATIONS = autosar44.ANNOTATIONSType2079()
        new_annotation = cls.create_annotation_value(label, origin_content)
        parent.ANNOTATIONS.ANNOTATION.append(new_annotation)
        new_annotation.set_parent(parent.ANNOTATIONS)

    @classmethod
    def add_admin_data_value(cls, parent, admin_data_config):
        # If ADMIN_DATA tag is None, creating ADMIN_DATA firstly
        if parent.ADMIN_DATA is None:
            parent.ADMIN_DATA = autosar44.ADMIN_DATA()
        admin_data_obj = parent.ADMIN_DATA
        cls.create_or_update_admin_data(admin_data_obj, admin_data_config)

    @classmethod
    def create_or_update_admin_data(cls, admin_data_obj, sdg_objs):
        """
        Create or update admin-data based on configuration.

        :param admin_data_obj: The admin-data object to be updated or into which new SDGs/SDs will be inserted.
        :param sdg_objs: A dictionary containing the SDG labels and respective SD values.
        """
        current_sdgs_obj = admin_data_obj.get_SDGS()
        if current_sdgs_obj is None:
            # If there are no existing SDGS, create one.
            current_sdgs_obj = autosar44.SDGSType50()
            admin_data_obj.set_SDGS(current_sdgs_obj)

        for sdg_label, sdg_value in sdg_objs.items():
            existing_sdg_obj = next((sdg for sdg in current_sdgs_obj.get_SDG() if sdg.get_GID() == sdg_label), None)
            if existing_sdg_obj is None:
                # If the SDG doesn't exist, create and insert it.
                new_sdg_obj = cls.create_sdg_obj(sdg_label, sdg_value)
                current_sdgs_obj.add_SDG(new_sdg_obj)
            else:
                # If the SDG does exist, update its SD values.
                cls.set_sd_value(existing_sdg_obj, sdg_value)

    @classmethod
    def create_sdgs_obj(cls, sdg_objs):
        """create sdgs object"""
        if not sdg_objs:
            return None
        sdgs_obj = autosar44.SDGSType50()
        for sdg_label, sdg_value in sdg_objs.items():
            sdg_obj = cls.create_sdg_obj(sdg_label, sdg_value)
            sdgs_obj.add_SDG(sdg_obj)
        return sdgs_obj

    @classmethod
    def create_sdg_obj(cls, sdg_label, sdg_value):
        """Recursively create sdg object with possible nested sdg's and finally sd."""
        # Create the current SDG
        sdg_obj = autosar44.SDG()
        sdg_obj.set_GID(sdg_label)

        # Determine if we are at a leaf (should create SD) or an intermediate node (should create nested SDG)
        if isinstance(sdg_value, dict) and "NAME" in sdg_value:
            # We are at a leaf, supposed to create SD
            sd_obj = cls.create_sd_obj("NAME", sdg_value["NAME"])
            sdg_obj.add_SD(sd_obj)
        else:
            # We are at an intermediate node, create nested SDGs
            for nested_sdg_label, nested_sdg_value in sdg_value.items():
                nested_sdg_obj = cls.create_sdg_obj(nested_sdg_label, nested_sdg_value)
                sdg_obj.add_SDG(nested_sdg_obj)  # Assumes existence of an add_SDG method analogous to add_SD

        return sdg_obj

    @classmethod
    def create_sdg_obj_common_data(cls, sdg_label, sdg_value):
        """Recursively create sdg object with possible nested sdg's and finally sd."""
        # Create the current SDG
        sdg_obj = autosar44.SDG()
        sdg_obj.set_GID(sdg_label)

        # Determine if we are at a leaf (should create SD) or an intermediate node (should create nested SDG)
        if isinstance(sdg_value, dict) and "VCOS2:Name" in sdg_value:
            # We are at a leaf, supposed to create SD
            sd_obj = cls.create_sd_obj("VCOS2:Name", sdg_value["VCOS2:Name"])
            sdg_obj.add_SD(sd_obj)
        if isinstance(sdg_value, dict) and "VCOS2:Value" in sdg_value:
            # We are at a leaf, supposed to create SD
            sd_obj = cls.create_sd_obj("VCOS2:Value", sdg_value["VCOS2:Value"])
            sdg_obj.add_SD(sd_obj)
        if isinstance(sdg_value, dict) and "VCOS2:BswModule" in sdg_value:
            # We are at a leaf, supposed to create SD
            sd_obj = cls.create_sd_obj("VCOS2:BswModule", sdg_value["VCOS2:BswModule"])
            sdg_obj.add_SD(sd_obj)
        return sdg_obj

    @classmethod
    def create_sd_obj(cls, sd_lable, sd_value):
        """create sd object"""
        sd_obj = autosar44.SD()
        sd_obj.set_GID(sd_lable)
        sd_obj.set_valueOf_(sd_value)
        return sd_obj

    @classmethod
    def set_sdgs_value(cls, admin_data_obj, sdg_objs):
        sdgs_obj = admin_data_obj.get_SDGS()
        for sdg_label, sdg_value in sdg_objs.items():
            for sdg_obj in sdgs_obj.get_SDG():
                is_found = False
                if sdg_obj.get_GID() == sdg_label:
                    cls.set_sd_value(sdg_obj, sdg_value)
                    is_found = True
                if is_found is True:
                    break

    @classmethod
    def set_sd_value(cls, sdg_obj, sdg_value):
        for sd_label, sd_value in sdg_value.items():
            for sd_obj in sdg_obj.get_SD():
                is_found = False
                if sd_obj.get_GID() == sd_label:
                    sd_obj.set_valueOf_(sd_value)
                    is_found = True
                if is_found is True:
                    break

    @classmethod
    def remove_annotation_value(cls, parent, origin_content: str):
        if parent.ANNOTATIONS is None:
            return
        for annotation in getattr(parent.ANNOTATIONS, "ANNOTATION", []):
            annotation_origin = getattr(annotation, "ANNOTATION_ORIGIN", None)
            if annotation_origin is not None and annotation_origin.valueOf_ == origin_content:
                parent.ANNOTATIONS.ANNOTATION.remove(annotation)
                break
        if not getattr(parent.ANNOTATIONS, "ANNOTATION", []):
            parent.ANNOTATIONS = None

    @classmethod
    def set_annotation_value(cls, parent, origin_content: str, label: Optional[str] = None):
        # If ANNOTATIONS tag is None, create ANNOTATIONS first
        if parent.ANNOTATIONS is None:
            parent.ANNOTATIONS = autosar44.ANNOTATIONSType2079()
        for annotation in parent.ANNOTATIONS.ANNOTATION:
            annotation_origin = annotation.get_ANNOTATION_ORIGIN()
            annotation_origin_value = annotation_origin.valueOf_
            post_item = origin_content.split(":")
            pre_item = annotation_origin_value.split(":")
            # 如果表示进制的annotation已经存在，则不创建
            if pre_item[0] == post_item[0]:
                annotation_origin.valueOf_ = origin_content
                return
        new_annotation = cls.create_annotation_value(label, origin_content)
        parent.ANNOTATIONS.ANNOTATION.append(new_annotation)
        new_annotation.set_parent(parent.ANNOTATIONS)

    @classmethod
    def create_sub_container_choice(cls, choice_name, conf_def, parent_container):
        sub_container = autosar44.ECUC_CONTAINER_VALUE()
        sub_container.SUB_CONTAINERS = autosar44.SUB_CONTAINERSType()
        sub_container.SUB_CONTAINERS.set_parent(sub_container)
        if parent_container.SUB_CONTAINERS is None:
            parent_container.SUB_CONTAINERS = autosar44.SUB_CONTAINERSType()
            parent_container.SUB_CONTAINERS.set_parent(parent_container)
            parent_container.SUB_CONTAINERS.set_tag("SUB-CONTAINERS")
        sub_container.set_parent(parent_container.SUB_CONTAINERS)
        parent_container.SUB_CONTAINERS.ECUC_CONTAINER_VALUE.append(sub_container)
        utils.set_short_name(sub_container, choice_name)
        sub_container.set_tag("ECUC-CONTAINER-VALUE")
        sub_container.SUB_CONTAINERS.set_tag("SUB-CONTAINERS")
        parent_def_ref = utils.get_definition_ref(parent_container)
        def_ref = f"{parent_def_ref}/{choice_name}"
        dest = conf_def.get_tag()
        utils.set_definition_ref(sub_container, dest, def_ref)
        cls.create_param_conf_container(conf_def, sub_container)
        return sub_container

    @staticmethod
    def is_visible(ecuc_container_value):
        for anno in getattr(getattr(ecuc_container_value, "ANNOTATIONS", None), "ANNOTATION", []):
            if anno.ANNOTATION_ORIGIN.valueOf_ == "InVisible":
                return False
        return True

    @staticmethod
    def is_automatic(ecuc_container_value):
        for anno in getattr(getattr(ecuc_container_value, "ANNOTATIONS", None), "ANNOTATION", []):
            if anno.ANNOTATION_ORIGIN.valueOf_ == "IsAutomatic":
                return True
        return False

    @staticmethod
    def is_auto_derived(ecuc_container_value):
        for anno in getattr(getattr(ecuc_container_value, "ANNOTATIONS", None), "ANNOTATION", []):
            if anno.ANNOTATION_ORIGIN.valueOf_ == "AutoDerived":
                return True
        return False

    @staticmethod
    def is_user_defined(ecuc_container_value):
        for anno in getattr(getattr(ecuc_container_value, "ANNOTATIONS", None), "ANNOTATION", []):
            if anno.ANNOTATION_ORIGIN.valueOf_ == "UserDefined":
                return True
        return False

    @classmethod
    def create_param_conf_container(cls, conf_def, child_data):
        # Add PARAMETERS
        cls.add_parameter_values(conf_def, child_data)
        # Add REFERENCES
        cls.add_reference_values(conf_def, child_data)

    @classmethod
    def add_parameter_values(cls, conf_def, child_data):
        parameters = []
        if conf_def.PARAMETERS:
            parameters += conf_def.PARAMETERS.ECUC_ADD_INFO_PARAM_DEF
            parameters += conf_def.PARAMETERS.ECUC_BOOLEAN_PARAM_DEF
            parameters += conf_def.PARAMETERS.ECUC_ENUMERATION_PARAM_DEF
            parameters += conf_def.PARAMETERS.ECUC_FLOAT_PARAM_DEF
            parameters += conf_def.PARAMETERS.ECUC_FUNCTION_NAME_DEF
            parameters += conf_def.PARAMETERS.ECUC_INTEGER_PARAM_DEF
            parameters += conf_def.PARAMETERS.ECUC_LINKER_SYMBOL_DEF
            parameters += conf_def.PARAMETERS.ECUC_MULTILINE_STRING_PARAM_DEF
            parameters += conf_def.PARAMETERS.ECUC_STRING_PARAM_DEF
            child_data.PARAMETER_VALUES = cls.create_parameter_values(parameters, child_data)

    @classmethod
    def get_ecuc_parameter_value(cls, ecuc_autosar_param_obj, ecuc_def_pararm_obj) -> bool:
        if ecuc_autosar_param_obj is None and not hasattr(ecuc_autosar_param_obj, "PARAMETER_VALUES"):
            return False
        parameter_values = []
        parameter_values.extend(ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_ADD_INFO_PARAM_VALUE)
        parameter_values.extend(ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE)
        parameter_values.extend(ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE)

        for parameter_value in parameter_values:
            if utils.get_definition_ref(parameter_value) != ecuc_def_pararm_obj.get_path():
                continue
            return utils.get_value(parameter_value)

    @classmethod
    def add_reference_values(cls, conf_def, child_data):
        references = []
        if conf_def.REFERENCES:
            references += conf_def.REFERENCES.ECUC_CHOICE_REFERENCE_DEF
            references += conf_def.REFERENCES.ECUC_FOREIGN_REFERENCE_DEF
            references += conf_def.REFERENCES.ECUC_INSTANCE_REFERENCE_DEF
            references += conf_def.REFERENCES.ECUC_REFERENCE_DEF
            references += conf_def.REFERENCES.ECUC_SYMBOLIC_NAME_REFERENCE_DEF
            child_data.REFERENCE_VALUES = cls.create_reference_values(references, child_data)

    @classmethod
    def create_parameter_values(cls, parameters, parent):
        parameter_values = autosar44.PARAMETER_VALUESType()
        parameter_values.set_parent(parent)
        parameter_values.set_tag("PARAMETER-VALUES")
        for parameter in parameters:
            cls.set_parameter(parameter_values, parameter)
        return parameter_values

    @classmethod
    def create_reference_values(cls, references, parent):
        reference_values = autosar44.REFERENCE_VALUESType()
        reference_values.set_parent(parent)
        reference_values.set_tag("REFERENCE-VALUES")
        for reference in references:
            cls.set_reference(reference_values, reference)
        return reference_values

    @classmethod
    def add_ecuc_parameter(cls, ecuc_autosar_param_obj, ecuc_def_pararm_obj, value) -> bool:
        if ecuc_autosar_param_obj is None and not hasattr(ecuc_autosar_param_obj, "PARAMETER_VALUES"):
            return False
        parameter_values = []
        parameter_values.extend(ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_ADD_INFO_PARAM_VALUE)
        parameter_values.extend(ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE)
        parameter_values.extend(ecuc_autosar_param_obj.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE)

        for parameter_value in parameter_values:
            if utils.get_destination_ref(parameter_value) != ecuc_def_pararm_obj.get_path():
                continue
            utils.set_value(parameter_value, value)
            return True
        parameter = AutosarUtil.set_parameter(ecuc_autosar_param_obj.PARAMETER_VALUES, ecuc_def_pararm_obj)
        utils.set_value(parameter, value)

        return True

    @staticmethod
    def set_parameter(obj, parameter):
        tag = parameter.get_tag()
        obj_tag = types.PARAMETERS_TYPE[tag]
        parameter_obj = types.PARAMETERS_CLASS[obj_tag]()
        parameter_obj.set_parent(obj)
        parameter_obj.set_tag(obj_tag)
        admin_data_cfg_value = utils.get_vcos_cfg_value(parameter)
        if admin_data_cfg_value is not None:
            utils.set_value(parameter_obj, admin_data_cfg_value)
        else:
            utils.set_value(parameter_obj, utils.get_default_value(parameter))
        utils.set_definition_ref(parameter_obj, tag, parameter.get_path())
        getattr(obj, obj_tag.replace("-", "_")).append(parameter_obj)
        return parameter_obj

    @staticmethod
    def set_reference(obj, reference):
        tag = reference.get_tag()
        obj_tag = types.REFERENCES_TYPE[tag]
        reference_obj = types.REFERENCES_CLASS[obj_tag]()
        reference_obj.set_parent(obj)
        reference_obj.set_tag(obj_tag)
        if tag == "ECUC-INSTANCE-REFERENCE-DEF":
            utils.set_value_iref(reference_obj, utils.get_default_value(reference))
        else:
            utils.set_value_ref(reference_obj, utils.get_default_value(reference))
        utils.set_definition_ref(reference_obj, tag, reference.get_path())
        getattr(obj, obj_tag.replace("-", "_")).append(reference_obj)
        return reference_obj

    @classmethod
    def create_sub_container_value(cls, container_name, cur_conf_def, parent, guess_name=None):
        return cls.create_container_value(container_name, cur_conf_def, parent, guess_name)

    @classmethod
    def create_ecuc_module_configuration_values(cls, module_name, cur_conf_def, parent):
        ecuc_conf_vals = autosar44.ECUC_MODULE_CONFIGURATION_VALUES()
        ecuc_conf_vals.set_tag("ECUC-MODULE-CONFIGURATION-VALUES")
        ecuc_conf_vals.set_parent(parent.ELEMENTS)
        ecuc_conf_vals.CONTAINERS = autosar44.CONTAINERSType2082()
        ecuc_conf_vals.CONTAINERS.set_parent(ecuc_conf_vals)
        ecuc_conf_vals.CONTAINERS.set_tag("CONTAINERS")
        utils.set_short_name(ecuc_conf_vals, module_name)
        utils.set_definition_ref(ecuc_conf_vals, cur_conf_def.get_tag(), cur_conf_def.get_path())
        parent_module_conf_val_list = parent.ELEMENTS.ECUC_MODULE_CONFIGURATION_VALUES
        parent_module_conf_val_list.append(ecuc_conf_vals)
        return ecuc_conf_vals

    @classmethod
    def get_by_path_from_dict(cls, data: dict, path: str):
        if path.startswith("/"):
            path = path[1:]
        keys = path.split("/")
        cur_data = data
        for key in keys:
            if key in cur_data:
                cur_data = cur_data[key]
            else:
                return None
        return cur_data

    @classmethod
    def create_ar_packages(cls, parent) -> autosar44.AR_PACKAGESType:
        packages = autosar44.AR_PACKAGESType()
        packages.set_parent(parent)
        return packages

    @classmethod
    def create_ar_package(cls, short_name: str, elements=None, subpackages=None, parent=None) -> autosar44.AR_PACKAGE:
        short_name_obj = autosar44.IDENTIFIER(valueOf_=short_name)
        package = autosar44.AR_PACKAGE(SHORT_NAME=short_name_obj, ELEMENTS=elements, AR_PACKAGES=subpackages)
        package.set_parent(parent)
        return package

    @classmethod
    def create_ar_elements(cls) -> autosar44.ELEMENTSType2:
        elements = autosar44.ELEMENTSType2()
        elements.set_tag("ELEMENTS")
        return elements

    @classmethod
    def create_ar_compu_method(cls, name, parent=None):
        cm_obj = autosar44.COMPU_METHOD()
        utils.set_short_name(cm_obj, name)
        cm_obj.set_tag("COMPU-METHOD")
        cm_obj.set_parent(parent)
        return cm_obj

    @classmethod
    def crate_compu_internal_to_phys(cls, parent=None):
        c_obj = autosar44.COMPU()
        c_obj.set_tag("COMPU-INTERNAL-TO-PHYS")
        c_obj.set_parent(parent)
        return c_obj

    @classmethod
    def create_compu_scales(cls, parent=None):
        cs_s_obj = autosar44.COMPU_SCALESType808()
        cs_s_obj.set_tag("COMPU-SCALES")
        cs_s_obj.set_parent(parent)
        return cs_s_obj

    @classmethod
    def create_compu_scale(cls, parent=None):
        cs_obj = autosar44.COMPU_SCALE()
        cs_obj.set_tag("COMPU-SCALE")
        cs_obj.set_parent(parent)
        return cs_obj

    @classmethod
    def create_desc(cls, text_list, parent=None):
        desc_obj = autosar44.MULTI_LANGUAGE_OVERVIEW_PARAGRAPH()
        desc_obj.set_tag("DESC")
        desc_obj.set_parent(parent)
        if not isinstance(text_list, list):
            text_list = [text_list]
        for text in text_list:
            text = autosar44.quote_xml(str(text))
            l_2_obj = autosar44.L_OVERVIEW_PARAGRAPH(L="FOR-ALL", valueOf_=str(text))
            mixed_container = autosar44.MixedContainer(
                autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", str(text)
            )
            l_2_obj.content_.append(mixed_container)
            l_2_obj.set_tag("L-2")
            l_2_obj.set_parent(desc_obj)
            desc_obj.L_2.append(l_2_obj)

        return desc_obj

    @classmethod
    def create_compu_const(cls, parent=None):
        cc_obj = autosar44.COMPU_CONST()
        cc_obj.set_tag("COMPU-CONST")
        cc_obj.set_parent(parent)
        return cc_obj

    @classmethod
    def create_compu_rational_coeffs(cls, parent=None):
        crc_obj = autosar44.COMPU_RATIONAL_COEFFS()
        crc_obj.set_tag("COMPU-RATIONAL-COEFFS")
        crc_obj.set_parent(parent)
        return crc_obj

    @classmethod
    def create_compu_numerator(cls, scale, offset, parent=None):
        cnd_obj = autosar44.COMPU_NOMINATOR_DENOMINATOR()
        cnd_obj.set_tag("COMPU-NUMERATOR")
        cnd_obj.set_parent(parent)

        nvvp_offset_obj = autosar44.NUMERICAL_VALUE_VARIATION_POINT(valueOf_=offset)
        nvvp_offset_obj.set_parent(cnd_obj)
        cnd_obj.V.append(nvvp_offset_obj)
        mixed_container = autosar44.MixedContainer(
            autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", str(offset)
        )
        nvvp_offset_obj.content_.append(mixed_container)

        nvvp_scale_obj = autosar44.NUMERICAL_VALUE_VARIATION_POINT(valueOf_=scale)
        nvvp_scale_obj.set_parent(cnd_obj)
        cnd_obj.V.append(nvvp_scale_obj)
        mixed_container = autosar44.MixedContainer(
            autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", str(scale)
        )
        nvvp_scale_obj.content_.append(mixed_container)

        return cnd_obj

    @classmethod
    def create_compu_denominator(cls, parent=None):
        cnd_obj = autosar44.COMPU_NOMINATOR_DENOMINATOR()
        cnd_obj.set_tag("COMPU-DENOMINATOR")
        cnd_obj.set_parent(parent)

        nvvp_obj = autosar44.NUMERICAL_VALUE_VARIATION_POINT(valueOf_=str(1))
        nvvp_obj.set_parent(cnd_obj)
        cnd_obj.V.append(nvvp_obj)
        mixed_container = autosar44.MixedContainer(
            autosar44.MixedContainer.CategoryText, autosar44.MixedContainer.TypeNone, "", str(1)
        )
        nvvp_obj.content_.append(mixed_container)

        return cnd_obj

    @classmethod
    def create_data_constr(cls, name, parent=None):
        dc_obj = autosar44.DATA_CONSTR()
        utils.set_short_name(dc_obj, name)
        dc_obj.set_tag("DATA-CONSTR")
        dc_obj.set_parent(parent)

        return dc_obj

    @classmethod
    def create_data_constr_rules(cls, parent=None):
        dcr_s_obj = autosar44.DATA_CONSTR_RULESType939()
        dcr_s_obj.set_tag("DATA-CONSTR-RULES")
        dcr_s_obj.set_parent(parent)

        return dcr_s_obj

    @classmethod
    def create_data_constr_rule(cls, low_lim, up_lim, parent=None):
        dcr_obj = autosar44.DATA_CONSTR_RULE()
        dcr_obj.set_tag("DATA-CONSTR-RULE")
        dcr_obj.set_parent(parent)

        ic_obj = autosar44.INTERNAL_CONSTRS()
        ic_obj.set_tag("INTERNAL-CONSTRS")
        ic_obj.set_parent(dcr_obj)
        dcr_obj.INTERNAL_CONSTRS = ic_obj

        utils.set_lower_limit(ic_obj, str(low_lim), "CLOSED")
        utils.set_upper_limit(ic_obj, str(up_lim), "CLOSED")

        return dcr_obj

    @classmethod
    def create_sw_base_type(cls, name, category, type_size, type_encoding, parent=None):
        sbt_obj = autosar44.SW_BASE_TYPE()
        sbt_obj.set_tag("SW-BASE-TYPE")
        sbt_obj.set_parent(parent)
        utils.set_short_name(sbt_obj, name)
        utils.set_category(sbt_obj, category)
        utils.set_base_type_size(sbt_obj, type_size)
        utils.set_base_type_encoding(sbt_obj, type_encoding)

        return sbt_obj

    ####################################################################################################################
    # Parse autosar ecuc function

    @classmethod
    def parse_os_info(cls, os_ecuc_obj):
        application_info_dict = {}
        isr_info_dict = {}
        task_info_dict = {}

        if getattr(os_ecuc_obj, "AR_PACKAGES", None) is None:
            return application_info_dict, isr_info_dict, task_info_dict
        if getattr(os_ecuc_obj.AR_PACKAGES, "AR_PACKAGE", None) is None or len(os_ecuc_obj.AR_PACKAGES.AR_PACKAGE) < 1:
            return application_info_dict, isr_info_dict, task_info_dict

        application_list = []
        isr_list = []
        task_list = []
        for ar_package in os_ecuc_obj.AR_PACKAGES.AR_PACKAGE:
            ecuc_container_list = ar_package.find_nodes("ECUC-CONTAINER-VALUE")
            for _ in ecuc_container_list:
                if utils.get_definition_ref(_).endswith("OsApplication"):
                    application_list.append(_)
                elif utils.get_definition_ref(_).endswith("OsIsr"):
                    isr_list.append(_)
                elif utils.get_definition_ref(_).endswith("OsTask"):
                    task_list.append(_)

        # Application information
        for app in application_list:
            app_name = utils.get_short_name(app)
            application_info_dict[app_name] = {"core_name": "", "isr_name_list": [], "task_name_list": []}
            for _ in app.REFERENCE_VALUES.ECUC_REFERENCE_VALUE:
                if utils.get_definition_ref(_).endswith("OsApplicationCoreRef"):
                    if utils.get_value_ref(_) is not None and utils.get_value_ref(_) != "":
                        application_info_dict[app_name]["core_name"] = utils.get_value_ref(_).split("/")[-1]
                elif utils.get_definition_ref(_).endswith("OsAppIsrRef"):
                    if utils.get_value_ref(_) is not None and utils.get_value_ref(_) != "":
                        application_info_dict[app_name]["isr_name_list"].append(utils.get_value_ref(_).split("/")[-1])
                elif utils.get_definition_ref(_).endswith("OsAppTaskRef"):
                    if utils.get_value_ref(_) is not None and utils.get_value_ref(_) != "":
                        application_info_dict[app_name]["task_name_list"].append(utils.get_value_ref(_).split("/")[-1])

        # ISR information
        for isr in isr_list:
            isr_name = utils.get_short_name(isr)
            isr_info_dict[isr_name] = {}
            for _ in isr.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                if utils.get_definition_ref(_).endswith("OsIsrInterruptPriority"):
                    isr_info_dict[isr_name]["OsIsrInterruptPriority"] = int(utils.get_value(_))

        # Task information
        for task in task_list:
            task_name = utils.get_short_name(task)
            task_info_dict[task_name] = {}
            for _ in task.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE:
                if utils.get_definition_ref(_).endswith("OsTaskSchedule"):
                    task_info_dict[task_name]["OsTaskSchedule"] = utils.get_value(_)
                elif utils.get_definition_ref(_).endswith("OsTaskType"):
                    task_info_dict[task_name]["OsTaskType"] = utils.get_value(_)
            for _ in task.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                if utils.get_definition_ref(_).endswith("OsTaskPriority"):
                    task_info_dict[task_name]["OsTaskPriority"] = int(utils.get_value(_))
                elif utils.get_definition_ref(_).endswith("OsTaskStackSize"):
                    task_info_dict[task_name]["OsTaskStackSize"] = utils.get_value(_)

        return application_info_dict, isr_info_dict, task_info_dict

    @classmethod
    def get_container_path_by_mod_path(
        cls, module_ecuc_obj, root_container_ecuc_path: str, target_container_mod_path: str
    ) -> List[str]:

        def __recursive_get_all_sub_containers(container_path_list, container_obj_list, target_container_mod_path):
            for sub_container in container_obj_list:
                if utils.get_definition_ref(sub_container) == target_container_mod_path:
                    container_path_list.append(sub_container.get_path())
                else:
                    grand_sub_containers = getattr(getattr(sub_container, "SUB_CONTAINERS"), "ECUC_CONTAINER_VALUE", [])
                    __recursive_get_all_sub_containers(
                        container_path_list, grand_sub_containers, target_container_mod_path
                    )

        container_path_list = []
        root_ecuc_obj = module_ecuc_obj.find(root_container_ecuc_path)
        if not root_ecuc_obj:
            return container_path_list
        sub_containers = []
        if hasattr(root_ecuc_obj, "SUB_CONTAINERS"):
            sub_containers = getattr(getattr(root_ecuc_obj, "SUB_CONTAINERS", None), "ECUC_CONTAINER_VALUE", [])
        else:
            sub_containers = getattr(getattr(root_ecuc_obj, "CONTAINERS", None), "ECUC_CONTAINER_VALUE", [])
        for sub_container in sub_containers:
            if utils.get_definition_ref(sub_container) == target_container_mod_path:
                container_path_list.append(sub_container.get_path())
            else:
                grand_sub_containers = getattr(getattr(sub_container, "SUB_CONTAINERS"), "ECUC_CONTAINER_VALUE", [])
                __recursive_get_all_sub_containers(container_path_list, grand_sub_containers, target_container_mod_path)
        return container_path_list

    @staticmethod
    def remove_assembly_sw_connector(flatExtract_autosar, short_name):
        AutosarUtil.remove_connector(flatExtract_autosar, short_name)

    @classmethod
    def save_assembly_sw_connector(cls, flatExtract_autosar, sw_connectors: List):
        connectors = flatExtract_autosar.find("/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE").CONNECTORS
        connector_set = set(
            map(lambda x: x.SHORT_NAME.valueOf_, connectors.ASSEMBLY_SW_CONNECTOR + connectors.DELEGATION_SW_CONNECTOR)
        )
        for conn in sw_connectors:
            for connector_name, connector_value in conn.items():
                if connector_name in connector_set:
                    continue
                cls.create_full_sw_connector(connectors, connector_value)

    @classmethod
    def create_full_sw_connector(cls, parent, value):
        connector_type = value["type"]
        if connector_type == "ASSEMBLY_SW_CONNECTOR":
            short_name = value["short_name"]
            provider_iref_obj = cls.create_provider_iref(parent, value)
            requester_iref_obj = cls.create_requester_iref(parent, value)
            rv_obj = AutosarUtil.create_ar_assembly_sw_connector(short_name, provider_iref_obj, requester_iref_obj)
            if parent and hasattr(parent, "ASSEMBLY_SW_CONNECTOR"):
                if isinstance(parent.ASSEMBLY_SW_CONNECTOR, list):
                    parent.ASSEMBLY_SW_CONNECTOR.append(rv_obj)
        else:
            pass

    @classmethod
    def create_ar_assembly_sw_connector(
        cls, short_name: str, PROVIDER_IREF=None, REQUESTER_IREF=None, parent=None
    ) -> autosar44.ASSEMBLY_SW_CONNECTOR:
        short_name_obj = autosar44.IDENTIFIER(valueOf_=short_name)
        assembly_sw_connector = autosar44.ASSEMBLY_SW_CONNECTOR(
            SHORT_NAME=short_name_obj, PROVIDER_IREF=PROVIDER_IREF, REQUESTER_IREF=REQUESTER_IREF
        )
        assembly_sw_connector.set_parent(parent)
        assembly_sw_connector.set_tag("ASSEMBLY-SW-CONNECTOR")
        return assembly_sw_connector

    @staticmethod
    def create_provider_iref(parent, value):
        context_ref = value["provider_iref"]["context_component_ref"]
        context_component_dest = value["provider_iref"]["context_component_dest"]
        target_pport_ref = value["provider_iref"]["target_pport_ref"]
        target_pport_dest = value["provider_iref"]["target_pport_dest"]
        context_ref_obj = AutosarUtil.create_ar_context_component_reftype(
            DEST=context_component_dest, valueOf_=context_ref
        )
        target_pport_ref_obj = AutosarUtil.create_ar_target_p_port_reftype(
            DEST=target_pport_dest, valueOf_=target_pport_ref
        )
        rv_provider_iref_obj = AutosarUtil.create_ar_p_port_in_composition_instance_ref(
            context_ref_obj, target_pport_ref_obj
        )
        return rv_provider_iref_obj

    @staticmethod
    def create_requester_iref(parent, value):
        rport_context_ref = value["requester_iref"]["context_component_ref"]
        rport_context_dest = value["requester_iref"]["context_component_dest"]
        rport_target_rport_ref = value["requester_iref"]["target_rport_ref"]
        rport_target_rpport_dest = value["requester_iref"]["target_rport_dest"]
        context_r_component_ref = AutosarUtil.create_ar_context_component_reftype(
            DEST=rport_context_dest, valueOf_=rport_context_ref
        )
        target_r_port_ref = AutosarUtil.create_ar_target_r_port_reftype(
            DEST=rport_target_rpport_dest, valueOf_=rport_target_rport_ref
        )
        rv_requester_iref_obj = AutosarUtil.create_ar_r_port_in_composition_instance_ref(
            context_r_component_ref, target_r_port_ref
        )
        return rv_requester_iref_obj

    @classmethod
    def create_ar_context_component_reftype(
        cls, valueOf_: str, DEST: str, parent=None
    ) -> autosar44.CONTEXT_COMPONENT_REFType:
        context_component_reftype = autosar44.CONTEXT_COMPONENT_REFType(valueOf_=valueOf_, DEST=DEST)
        context_component_reftype.set_parent(parent)
        return context_component_reftype

    @classmethod
    def create_ar_target_r_port_reftype(cls, valueOf_: str, DEST: str, parent=None) -> autosar44.TARGET_R_PORT_REFType:
        target_r_port_reftype = autosar44.TARGET_R_PORT_REFType(valueOf_=valueOf_, DEST=DEST)
        target_r_port_reftype.set_parent(parent)
        return target_r_port_reftype

    @classmethod
    def create_ar_target_p_port_reftype(cls, valueOf_: str, DEST: str, parent=None) -> autosar44.TARGET_P_PORT_REFType:
        target_p_port_reftype = autosar44.TARGET_P_PORT_REFType(valueOf_=valueOf_, DEST=DEST)
        target_p_port_reftype.set_parent(parent)
        return target_p_port_reftype

    @classmethod
    def create_ar_p_port_in_composition_instance_ref(
        cls,
        CONTEXT_COMPONENT_REF: autosar44.CONTEXT_COMPONENT_REFType = None,
        TARGET_P_PORT_REF: autosar44.TARGET_P_PORT_REFType = None,
        parent=None,
    ) -> autosar44.P_PORT_IN_COMPOSITION_INSTANCE_REF:
        p_port_in_composition_instance_ref = autosar44.P_PORT_IN_COMPOSITION_INSTANCE_REF(
            CONTEXT_COMPONENT_REF=CONTEXT_COMPONENT_REF, TARGET_P_PORT_REF=TARGET_P_PORT_REF
        )
        p_port_in_composition_instance_ref.set_parent(parent)
        return p_port_in_composition_instance_ref

    @classmethod
    def create_ar_r_port_in_composition_instance_ref(
        cls,
        CONTEXT_COMPONENT_REF: autosar44.CONTEXT_COMPONENT_REFType,
        TARGET_R_PORT_REF: autosar44.TARGET_R_PORT_REFType,
        parent=None,
    ) -> autosar44.P_PORT_IN_COMPOSITION_INSTANCE_REF:
        r_port_in_composition_instance_ref = autosar44.R_PORT_IN_COMPOSITION_INSTANCE_REF(
            CONTEXT_COMPONENT_REF=CONTEXT_COMPONENT_REF, TARGET_R_PORT_REF=TARGET_R_PORT_REF
        )
        r_port_in_composition_instance_ref.set_parent(parent)
        return r_port_in_composition_instance_ref
