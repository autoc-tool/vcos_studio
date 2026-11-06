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
import copy
from lxml import etree
from xml.dom import minidom
from collections import defaultdict
from autosar44 import autosar44
from basic_func_module.base_logger import logger
from basic_func_module.autosar_utils.utils import get_short_name
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from func_module.health_monitor.perf_record import log_function_stats


class ArxmlConflict(Exception):

    def __init__(self, conflicts) -> None:
        super().__init__()
        self.conflicts = conflicts


class NoDefaultFileException(Exception):

    def __init__(self, msg) -> None:
        super().__init__()
        self.msg = msg


class AutosarEcuc:
    VCOS_PATH_LABEL = "VCOS:Path"
    VCOS_FILE_PATH_LABEL = "VCOS:FilePath"
    VCOS_DEFAULT_LABEL = "VCOS:Default"
    VCOS_DEFAULT_FILE_LABEL = "VCOS:DefaultFile"
    NAME_SPACES = {"AR": "http://autosar.org/schema/r4.0"}
    PARAM_TAGS = ("ECUC-NUMERICAL-PARAM-VALUE", "ECUC-ADD-INFO-PARAM-VALUE", "ECUC-TEXTUAL-PARAM-VALUE")
    REF_TAGS = ("ECUC-INSTANCE-REFERENCE-VALUE", "ECUC-REFERENCE-VALUE")

    @staticmethod
    def save_xml_string(xml_string, path):
        dom = minidom.parseString(xml_string)
        pretty_xml_as_string = dom.toprettyxml(indent="  ")
        with open(path, "w+", encoding="utf-8") as f:
            f.write(pretty_xml_as_string)

        return True

    @classmethod
    def prepare_sdg(cls, obj, sdg_label):
        # Check if ADMIN-DATA field exists
        if obj.ADMIN_DATA is None:
            obj.ADMIN_DATA = autosar44.ADMIN_DATA()
        admin_data_obj = obj.ADMIN_DATA

        # Check if SDGS field exists
        sdgs_obj = admin_data_obj.get_SDGS()
        if sdgs_obj is None:
            # If there are no existing SDGS, create one.
            sdgs_obj = autosar44.SDGSType50()
            admin_data_obj.set_SDGS(sdgs_obj)

        # Check if VCOS:PATH SDG field exists
        sdg_obj = next(filter(lambda sdg: sdg.get_GID() == sdg_label, sdgs_obj.SDG), None)
        if not sdg_obj:
            sdg_obj = autosar44.SDG()
            sdg_obj.set_GID(sdg_label)
            sdgs_obj.add_SDG(sdg_obj)

        return sdg_obj

    @classmethod
    def record_default_file(cls, module_obj, file_path):
        if module_obj.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
            logger.exception("The autosar obj must be ECUC-MODULE-CONFIGURATION-VALUES")
            return
        sdg_obj = cls.prepare_sdg(module_obj, cls.VCOS_DEFAULT_LABEL)

        # Override existed SDs
        sdg_obj.set_SD([])
        sd_obj = AutosarUtil.create_sd_obj(cls.VCOS_DEFAULT_FILE_LABEL, file_path)
        sdg_obj.add_SD(sd_obj)

    @classmethod
    def peek_default_file(cls, module_obj):
        """
        Return the default file path
        """
        if module_obj.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
            logger.exception("The autosar obj must be ECUC-MODULE-CONFIGURATION-VALUES")
            return
        path_marks = ""
        if getattr(module_obj, "ADMIN_DATA", None) and getattr(module_obj.ADMIN_DATA, "SDGS", None):
            sdg_list = getattr(module_obj.ADMIN_DATA.SDGS, "SDG", []) or []
            for sdg in reversed(sdg_list):
                if sdg.GID == cls.VCOS_DEFAULT_LABEL:
                    sd_list = getattr(sdg, "SD", []) or []
                    # Iter sd with specific GID, the last will be selected
                    for sd in reversed(sd_list):
                        if sd.GID == cls.VCOS_DEFAULT_FILE_LABEL:
                            path_marks = sd.valueOf_
                            return path_marks

        return path_marks

    @classmethod
    def pop_default_file(cls, module_obj):
        """
        Return the default file path and clear the ADMIN-DATA/SDGS/SDG/SD if necessary
        """
        if module_obj.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
            logger.exception("The autosar obj must be ECUC-MODULE-CONFIGURATION-VALUES")
            return
        path_marks = ""
        if getattr(module_obj, "ADMIN_DATA", None) and getattr(module_obj.ADMIN_DATA, "SDGS", None):
            sdg_list = getattr(module_obj.ADMIN_DATA.SDGS, "SDG", []) or []
            for sdg in reversed(sdg_list):
                if sdg.GID == cls.VCOS_DEFAULT_LABEL:
                    sd_list = getattr(sdg, "SD", []) or []
                    # Iter sd with specific GID, the last will be selected
                    for sd in reversed(sd_list):
                        if sd.GID == cls.VCOS_DEFAULT_FILE_LABEL:
                            path_marks = sd.valueOf_
                            sd_list.remove(sd)

                    if not sd_list:
                        sdg_list.remove(sdg)

            # Clear empty SDGS and ADMIN-DATA
            if not sdg_list:
                module_obj.ADMIN_DATA = None

        return path_marks

    @classmethod
    def set_default_label_sdg(cls, module_obj):
        if module_obj.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
            logger.exception("The autosar obj must be ECUC-MODULE-CONFIGURATION-VALUES")
            return
        cls.prepare_sdg(module_obj, cls.VCOS_DEFAULT_LABEL)

    @classmethod
    def check_default_label_sdg(cls, module_obj):
        if module_obj.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
            logger.exception("The autosar obj must be ECUC-MODULE-CONFIGURATION-VALUES")
            return False
        if admin_data := getattr(module_obj, "ADMIN_DATA", None):
            if sdgs := getattr(admin_data, "SDGS", None):
                sdg_list = getattr(sdgs, "SDG", []) or []
                for sdg in sdg_list:
                    if sdg.GID == cls.VCOS_DEFAULT_LABEL:
                        return True

        return False

    @classmethod
    def add_path_tag(cls, parent, file_path):
        """
        Add path tag to the container, do not override the existed path tag
        """
        # Prepare and get SDG obj with specific label
        sdg_obj = cls.prepare_sdg(parent, cls.VCOS_PATH_LABEL)

        # Check if VCOS:PATH SD field of the file exists
        file_path_obj = next(filter(lambda sd: sd.get_valueOf_() == file_path, sdg_obj.get_SD()), None)
        if not file_path_obj:
            sd_obj = AutosarUtil.create_sd_obj(cls.VCOS_FILE_PATH_LABEL, file_path)
            sdg_obj.add_SD(sd_obj)
        else:
            logger.debug(f'{parent.get_path()} already has path tag "{file_path}"')

    @classmethod
    def set_path_tag(cls, parent, file_path):
        """
        Set path tag to the container, which means overriding the existed path tag
        """
        # Prepare and get SDG obj with specific label
        sdg_obj = cls.prepare_sdg(parent, cls.VCOS_PATH_LABEL)

        # Override existed file path flags
        sdg_obj.set_SD([])
        sd_obj = AutosarUtil.create_sd_obj(cls.VCOS_FILE_PATH_LABEL, file_path)
        sdg_obj.add_SD(sd_obj)

    @classmethod
    def add_path_tag_str(cls, parent, path_list):
        """
        Set path tags for lxml Element
        """
        if (admin_data := parent.find("AR:ADMIN-DATA", cls.NAME_SPACES)) is None:
            tag = f"{{{cls.NAME_SPACES['AR']}}}ADMIN-DATA"
            admin_data = etree.Element(tag)
            parent.insert(1, admin_data)

        if (sdgs := admin_data.find("AR:SDGS", cls.NAME_SPACES)) is None:
            tag = f"{{{cls.NAME_SPACES['AR']}}}SDGS"
            sdgs = etree.SubElement(admin_data, tag)
        if (sdg := sdgs.find(f"AR:SDG[@GID='{cls.VCOS_PATH_LABEL}']", namespaces=cls.NAME_SPACES)) is None:
            tag = f"{{{cls.NAME_SPACES['AR']}}}SDG"
            sdg = etree.SubElement(sdgs, tag, attrib={"GID": cls.VCOS_PATH_LABEL})
        for path in path_list:
            if not sdg.xpath(
                f"AR:SD[@GID='{cls.VCOS_FILE_PATH_LABEL}' and text()='{path}']", namespaces=cls.NAME_SPACES
            ):
                tag = f"{{{cls.NAME_SPACES['AR']}}}SD"
                sd = etree.SubElement(sdg, tag, attrib={"GID": cls.VCOS_FILE_PATH_LABEL})
                sd.text = path

    @classmethod
    def iter_ancestors(cls, container_obj):
        parent = container_obj.get_path_parent()
        while parent and parent.get_tag() == "ECUC-CONTAINER-VALUE":
            yield parent
            parent = parent.get_path_parent()

    @classmethod
    def iter_descendants(cls, container_obj):
        if container_obj.get_tag() == "ECUC-MODULE-CONFIGURATION-VALUES":
            sub_container_obj = container_obj.CONTAINERS
        elif container_obj.get_tag() == "ECUC-CONTAINER-VALUE":
            sub_container_obj = container_obj.SUB_CONTAINERS
        else:
            logger.error(f"{get_short_name(container_obj)} is not a valid layer in container tree")
            return f"{get_short_name(container_obj)}"

        for sub in getattr(sub_container_obj, "ECUC_CONTAINER_VALUE", []):
            yield sub
            yield from cls.iter_descendants(sub)

    @classmethod
    def get_path_marks(cls, container_obj):
        """
        Get all path marks of the container
        """
        path_marks = []
        if getattr(container_obj, "ADMIN_DATA", None) and getattr(container_obj.ADMIN_DATA, "SDGS", None):
            sdg_list = getattr(container_obj.ADMIN_DATA.SDGS, "SDG", []) or []
            for sdg in sdg_list:
                if sdg.GID == cls.VCOS_PATH_LABEL:
                    sd_list = getattr(sdg, "SD", []) or []
                    for sd in sd_list:
                        if sd.GID == cls.VCOS_FILE_PATH_LABEL:
                            path_marks.append(sd.valueOf_)
        return path_marks

    @classmethod
    def mark_path(cls, container_obj, file_path):
        # Mark ancestors
        for anc in cls.iter_ancestors(container_obj):
            cls.add_path_tag(anc, file_path)

        # Mark the container
        cls.set_path_tag(container_obj, file_path)

        # Mark descendants
        for dec in cls.iter_descendants(container_obj):
            cls.set_path_tag(dec, file_path)

    @classmethod
    def supply_path_tag(cls, ele_root, default_file_tag):
        """
        Supply path tags for nodes which have no path tag
        """

        container_iter = ele_root.iterfind(".//AR:ECUC-CONTAINER-VALUE", cls.NAME_SPACES)
        node_list = [node for node in container_iter]
        for node in reversed(node_list):
            if not node.xpath(
                f"./AR:ADMIN-DATA/AR:SDGS/AR:SDG/AR:SD[@GID='{cls.VCOS_FILE_PATH_LABEL}']", namespaces=cls.NAME_SPACES
            ):
                for anc in node.xpath("ancestor::AR:ECUC-CONTAINER-VALUE", namespaces=cls.NAME_SPACES):
                    cls.add_path_tag_str(anc, [default_file_tag])
                cls.add_path_tag_str(node, [default_file_tag])
                for dec in node.xpath(".//AR:ECUC-CONTAINER-VALUE", namespaces=cls.NAME_SPACES):
                    cls.add_path_tag_str(dec, [default_file_tag])

    @classmethod
    def get_pure_tag(cls, element):
        return etree.QName(element.tag).localname

    @classmethod
    def config_ele_to_dict(cls, config_ele):
        """
        config_ele: Elements which are ECUC-NUMERICAL-PARAM-VALUE, ECUC-ADD-INFO-PARAM-VALUE, ECUC-TEXTUAL-PARAM-VALUE,
                    ECUC-INSTANCE-REFERENCE-VALUE, ECUC-REFERENCE-VALUE
        """
        tag = cls.get_pure_tag(config_ele)
        if tag in cls.PARAM_TAGS:
            return {"VALUE": config_ele.findtext("AR:VALUE", namespaces=cls.NAME_SPACES)}
        if tag == "ECUC-REFERENCE-VALUE":
            return {"VALUE-REF": config_ele.findtext("AR:VALUE-REF", namespaces=cls.NAME_SPACES)}
        if tag == "ECUC-INSTANCE-REFERENCE-VALUE":
            return {
                "CONTEXT-ELEMENT-REF": set(
                    config_ele.xpath("./AR:VALUE-IREF/AR:CONTEXT-ELEMENT-REF/text()", namespaces=cls.NAME_SPACES)
                ),
                "TARGET-REF": set(config_ele.xpath("./AR:VALUE-IREF/AR:TARGET-REF/text()", namespaces=cls.NAME_SPACES)),
            }

    @classmethod
    def gather_container_configs(cls, container_ele):
        """
        Gather parameter/reference configs of the container
        """
        config_info_dict = defaultdict(dict)
        param_xpath_rule = [f"./AR:PARAMETER-VALUES/AR:{tag}" for tag in cls.PARAM_TAGS]
        ref_xpath_rule = [f"./AR:REFERENCE-VALUES/AR:{tag}" for tag in cls.REF_TAGS]
        xpath_rule = "|".join(param_xpath_rule + ref_xpath_rule)
        config_list = container_ele.xpath(xpath_rule, namespaces=cls.NAME_SPACES)
        for config in config_list:
            def_name = config.findtext("AR:DEFINITION-REF", namespaces=cls.NAME_SPACES)
            config_info_dict[def_name].update(cls.config_ele_to_dict(config))

        return config_info_dict

    @classmethod
    def container_diff(cls, l_container, r_container):
        """
        Compare configs between two containers

        Return list of diff info
        """
        # Count diff of two containers
        l_file, l_element = l_container
        r_file, r_element = r_container
        l_config = cls.gather_container_configs(l_element)
        r_config = cls.gather_container_configs(r_element)

        diff_info_list = []
        config_name_set = set(l_config.keys()) | set(r_config.keys())
        for config in config_name_set:
            if config not in r_config:
                diff_info_list.append(
                    f"File '{r_file}' missing configuration item '{config}' compared to file '{l_file}'"
                )
            elif config not in l_config:
                diff_info_list.append(
                    f"File '{l_file}' missing configuration item '{config}' compared to file '{r_file}'"
                )
            elif l_config[config] != r_config[config]:
                diff_info_list.append(f"Configuration item '{config}' in {l_file} are different from {r_file}")

        return diff_info_list

    @classmethod
    def has_container_conflict(cls, container_ele_dict):
        """
        Check conflict between several containers.

        Return list of all found diffs
        """
        # Let each container compare with the first container
        items_list = list(container_ele_dict.items())
        bench_item = items_list[0]
        diff_list = []
        for item in items_list[1:]:
            diff_list += cls.container_diff(bench_item, item)

        return diff_list

    @classmethod
    def split_ecuc_arxml(cls, data, default_file_tag):
        arxml_str = AutosarUtil.get_arxml_string(data)
        arxml_root = etree.fromstring(arxml_str.encode())
        if arxml_root is None:
            return {}

        # Find no file path marks, means the arxml is not splitted
        root_container = next(arxml_root.iterfind(".//AR:ECUC-MODULE-CONFIGURATION-VALUES", cls.NAME_SPACES))
        tags = set(
            root_container.xpath(
                f".//AR:ADMIN-DATA/AR:SDGS/AR:SDG/AR:SD[@GID='{cls.VCOS_FILE_PATH_LABEL}']/text()",
                namespaces=cls.NAME_SPACES,
            )
        )
        if not tags or (len(tags) == 1 and default_file_tag in tags):
            return {default_file_tag: arxml_str}

        # Complete path tags for the tree
        cls.supply_path_tag(arxml_root, default_file_tag)
        arxml_str = etree.tostring(arxml_root, encoding="unicode")

        # Count how many files are splited into
        file_set = set(
            arxml_root.xpath(f"//AR:SD[@GID='{cls.VCOS_FILE_PATH_LABEL}']/text()", namespaces=cls.NAME_SPACES)
        )

        file_res_dict = {}
        for file in file_set:
            file_str_root = etree.fromstring(arxml_str.encode())
            elements = []
            elements += [e for e in file_str_root.iterfind(".//AR:ECUC-CONTAINER-VALUE", cls.NAME_SPACES)]

            for e in reversed(elements):
                file_tags = e.xpath(
                    f"./AR:ADMIN-DATA/AR:SDGS/AR:SDG/AR:SD[@GID='{cls.VCOS_FILE_PATH_LABEL}']/text()",
                    namespaces=cls.NAME_SPACES,
                )
                if file not in file_tags:
                    e.getparent().remove(e)

                # Clear file tag in exported arxml
                sdg = next(e.iterfind(f"./AR:ADMIN-DATA/AR:SDGS/AR:SDG[@GID='{cls.VCOS_PATH_LABEL}']", cls.NAME_SPACES))
                for sd in sdg.iterfind(f"./AR:SD[@GID='{cls.VCOS_FILE_PATH_LABEL}']", cls.NAME_SPACES):
                    sdg.remove(sd)
                if not sdg.xpath("./AR:SD", namespaces=cls.NAME_SPACES):
                    sdgs = sdg.getparent()
                    sdgs.remove(sdg)
                    if not sdgs.xpath("./AR:SDG", namespaces=cls.NAME_SPACES):
                        admin_data = sdgs.getparent()
                        admin_data.remove(sdgs)
                        if not len(admin_data):
                            admin_data.getparent().remove(admin_data)

            file_res_dict[file] = etree.tostring(file_str_root, encoding="unicode")

        return file_res_dict

    @classmethod
    def clear_file_path_marks(cls, ele):
        """
        清理Element下的文件路径标记
        """
        if (admin_data := ele.find("AR:ADMIN-DATA", cls.NAME_SPACES)) is not None:
            if (sdgs := admin_data.find("AR:SDGS", cls.NAME_SPACES)) is not None:
                empt_sdg = []
                for sdg in sdgs.xpath(f"./AR:SDG[@GID='{cls.VCOS_PATH_LABEL}']", namespaces=cls.NAME_SPACES):
                    sd_list = sdg.xpath(f"./AR:SD[@GID='{cls.VCOS_FILE_PATH_LABEL}']", namespaces=cls.NAME_SPACES)
                    for sd in sd_list:
                        sdg.remove(sd)
                    if len(sdg) == 0:
                        empt_sdg.append(sdg)
                for sdg in empt_sdg:
                    sdgs.remove(sdg)
            if len(sdgs):
                ele.remove(admin_data)

    @classmethod
    def pick_container_node(cls, ele):
        """
        Pick out the container from the arxml,
        without parent container and sub-containers

        Return the copy of the picked container node
        """
        # Prepare the new tree
        new_element = copy.deepcopy(ele)
        cls.clear_file_path_marks(new_element)
        containers = new_element.find("AR:SUB-CONTAINERS", namespaces=cls.NAME_SPACES)
        if containers is not None:
            for container in list(containers):
                containers.remove(container)

        return new_element

    @classmethod
    def merge_subtrees(cls, original, data_dict, parent):
        # Count children nodes of current layer
        value_dict = defaultdict(list)
        for file_name, container in data_dict.items():
            for sub_container in container.iterfind("./*/AR:ECUC-CONTAINER-VALUE", namespaces=cls.NAME_SPACES):
                short_name = sub_container.findtext("AR:SHORT-NAME", namespaces=cls.NAME_SPACES)
                value_dict[short_name].append({"file_name": file_name, "sub_container": sub_container})

        if len(value_dict) > 0:
            xpath_res = parent.xpath("./AR:SUB-CONTAINERS|./AR:CONTAINERS", namespaces=cls.NAME_SPACES)
            if xpath_res:
                parent_node = xpath_res[0]
            else:
                tag_map = {
                    f"{{{cls.NAME_SPACES['AR']}}}ECUC-MODULE-CONFIGURATION-VALUES": (
                        f"{{{cls.NAME_SPACES['AR']}}}SUB-CONTAINERS"
                    ),
                    f"{{{cls.NAME_SPACES['AR']}}}ECUC-CONTAINER-VALUE": f"{{{cls.NAME_SPACES['AR']}}}CONTAINERS",
                }
                parent_node = etree.SubElement(parent, tag_map[parent.tag])

        if original is not None:
            o_value_dict = {
                container.findtext("AR:SHORT-NAME", namespaces=cls.NAME_SPACES): container
                for container in original.iterfind("./*/AR:ECUC-CONTAINER-VALUE", namespaces=cls.NAME_SPACES)
            }
            for value, o_container in o_value_dict.items():
                # Iter each node of this layer
                if value in value_dict:
                    # Compare the content of the container in different files, if diff, through diff exception
                    container_dict = {info["file_name"]: info["sub_container"] for info in value_dict[value]}
                    if diff_list := cls.has_container_conflict(container_dict):
                        raise ArxmlConflict(diff_list)

                    # Create the container for this layer
                    new_container_node = cls.pick_container_node(next(iter(container_dict.values())))
                    cls.add_path_tag_str(new_container_node, container_dict.keys())
                    parent_node.append(new_container_node)

                    # Merge sub tree, if this node exists in many files
                    file_dict = value_dict[value]
                    if len(file_dict) > 0:
                        cls.merge_subtrees(o_container, container_dict, new_container_node)
                    # Pop accessed node
                    value_dict.pop(value)

        # Create nodes, which are new (not recorded in original file)
        for value, file_dict in value_dict.items():
            # Compare the content of the container in different files, if diff, through diff exception
            container_dict = {info["file_name"]: info["sub_container"] for info in file_dict}
            if diff_list := cls.has_container_conflict(container_dict):
                raise ArxmlConflict(diff_list)

            # Create the container for this layer
            new_container_node = cls.pick_container_node(next(iter(container_dict.values())))
            cls.add_path_tag_str(new_container_node, container_dict.keys())
            parent_node.append(new_container_node)

            if len(file_dict) > 0:
                cls.merge_subtrees(None, container_dict, new_container_node)

    @classmethod
    @log_function_stats(["BSW Editor", "配置文件解析和导入", "拆分和合并ecuc arxml", "合并拆分的ecuc arxml"])
    def merge_ecuc_arxml(cls, origin, data_dict):
        """
        Merge ecuc arxml of the same module
        """
        container_tree_dict = {}
        for file, obj in data_dict.items():
            arxml_str = AutosarUtil.get_arxml_string(obj)
            element = etree.fromstring(arxml_str.encode())
            container_root = element.xpath(".//AR:ECUC-MODULE-CONFIGURATION-VALUES", namespaces=cls.NAME_SPACES)[0]
            container_tree_dict[file] = container_root

        o_container_root = None
        if origin:
            o_str = AutosarUtil.get_arxml_string(origin)
            o_element = etree.fromstring(o_str.encode())
            o_container_root = o_element.xpath(".//AR:ECUC-MODULE-CONFIGURATION-VALUES", namespaces=cls.NAME_SPACES)[0]

        # Prepare the new tree
        new_element_tree = copy.deepcopy(element)
        new_container_root = new_element_tree.xpath(
            ".//AR:ECUC-MODULE-CONFIGURATION-VALUES", namespaces=cls.NAME_SPACES
        )[0]
        cls.clear_file_path_marks(new_container_root)
        containers_node = new_container_root.find("AR:CONTAINERS", namespaces=cls.NAME_SPACES)
        for container in list(containers_node):
            containers_node.remove(container)

        cls.merge_subtrees(o_container_root, container_tree_dict, new_container_root)

        tree_str = etree.tostring(new_element_tree, encoding="unicode")
        return tree_str
