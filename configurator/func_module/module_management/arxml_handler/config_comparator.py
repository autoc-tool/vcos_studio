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
import inspect
from copy import deepcopy
from func_module.health_monitor.logger import logger
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.utils import (
    get_short_name,
    set_short_name,
    get_definition_ref,
    get_value,
    set_value,
    get_value_ref,
    set_value_ref,
    get_value_iref,
    set_value_iref,
)

USER_DEFINE_FLAG = "UserDefined"


def get_param_or_ref_value(value_obj):
    tag = value_obj.get_tag()
    if tag in ("ECUC-NUMERICAL-PARAM-VALUE", "ECUC-TEXTUAL-PARAM-VALUE"):
        return get_value(value_obj)
    elif tag == "ECUC-REFERENCE-VALUE":
        return get_value_ref(value_obj)
    elif tag == "ECUC-INSTANCE-REFERENCE-VALUE":
        return get_value_iref(value_obj)
    else:
        print(f"{__file__}:{inspect.currentframe().f_lineno}    Unsupported value obj tag {tag}")


def set_param_or_ref_value(value_obj, value):
    tag = value_obj.get_tag()
    if tag in ("ECUC-NUMERICAL-PARAM-VALUE", "ECUC-TEXTUAL-PARAM-VALUE"):
        return set_value(value_obj, value)
    elif tag == "ECUC-REFERENCE-VALUE":
        return set_value_ref(value_obj, value)
    elif tag == "ECUC-INSTANCE-REFERENCE-VALUE":
        return set_value_iref(value_obj, value)
    else:
        print(f"{__file__}:{inspect.currentframe().f_lineno}    Unsupported value obj tag {tag}")


class ConfigComparator:

    def __init__(self, old_config, new_config) -> None:
        # Arg check
        if old_config.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
            logger.exception("Invalid old_config!")
            raise TypeError("Arg old_config excepted a ECUC-MODULE-CONFIGURATION-VALUES!")
        self.old_config = old_config
        if new_config.get_tag() != "ECUC-MODULE-CONFIGURATION-VALUES":
            logger.exception("Invalid new_config!")
            raise TypeError("Arg new_config excepted a ECUC-MODULE-CONFIGURATION-VALUES!")
        self.new_config = new_config

        self.deleted_container_list = []
        self.deleted_param_list = []
        self.deleted_ref_list = []
        self.added_container_list = []
        self.added_param_list = []
        self.added_ref_list = []
        self.modified_config_list = []

    def config_comparator(self):
        """
        Compare top level containers and gather diffs
        """
        old_container_dict = {
            get_short_name(old_container): old_container
            for old_container in getattr(getattr(self.old_config, "CONTAINERS", None), "ECUC_CONTAINER_VALUE", [])
        }
        new_container_dict = {
            get_short_name(new_container): new_container
            for new_container in getattr(getattr(self.new_config, "CONTAINERS", None), "ECUC_CONTAINER_VALUE", [])
        }

        # Gather all container names, and keep order according to new config
        key_list = list(dict.fromkeys(list(new_container_dict.keys()) + list(old_container_dict.keys())))
        for key in key_list:
            self.compare_container_trees(old_container_dict.get(key, None), new_container_dict.get(key, None))

    def compare_parameters(self, old_container, new_container):
        old_param_obj_list = getattr(old_container.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE", []) + getattr(
            old_container.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE", []
        )
        old_param_dict = {}
        for param in old_param_obj_list:
            param_name = get_definition_ref(param).split("/")[-1]
            old_param_dict.setdefault(param_name, []).append(param)

        new_param_obj_list = getattr(new_container.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE", []) + getattr(
            new_container.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE", []
        )
        new_param_dict = {}
        for param in new_param_obj_list:
            param_name = get_definition_ref(param).split("/")[-1]
            new_param_dict.setdefault(param_name, []).append(param)

        param_name_set = set(old_param_dict.keys()) | set(new_param_dict.keys())
        for param_name in param_name_set:
            # If new container has different param with old container, throw an exception
            try:
                new_value_list = new_param_dict[param_name]
            except KeyError:
                logger.debug(f"{param_name} not find in {new_container.get_path()} of new DDD")
                new_value_list = []

            try:
                old_value_list = old_param_dict[param_name]
            except KeyError:
                logger.debug(f"{param_name} not find in {old_container.get_path()} of old DDD")
                old_value_list = []

            # Deal with param which has more than one value
            old_value_dict = {get_value(old_value): old_value for old_value in old_value_list}
            new_value_dict = {get_value(new_value): new_value for new_value in new_value_list}
            if len(new_value_list) > 1 or len(old_value_list) > 1:

                self.added_param_list += [
                    {"path": new_value_dict[key].get_path(), "obj": new_value_dict[key]}
                    for key in new_value_dict.keys()
                    if key not in old_value_dict.keys()
                ]
                self.deleted_param_list += [
                    {"path": old_value_dict[key].get_path(), "obj": old_value_dict[key]}
                    for key in old_value_dict.keys()
                    if key not in new_value_dict.keys()
                ]
            # old value list is empty means this is a new ref param
            elif len(old_value_list) == 0:
                self.added_ref_list += [
                    {"path": new_value_dict[key].get_path(), "obj": new_value_dict[key]}
                    for key in new_value_dict.keys()
                    if key not in old_value_dict.keys()
                ]
            # new value list is empty means this is a removed ref param
            elif len(new_value_list) == 0:
                self.deleted_ref_list += [
                    {"path": old_value_dict[key].get_path(), "obj": old_value_dict[key]}
                    for key in old_value_dict.keys()
                    if key not in new_value_dict.keys()
                ]
            # Check if the value of new and old param are same
            elif get_value(new_value_list[0]) != get_value(old_value_list[0]):
                self.modified_config_list.append(
                    {
                        "path": new_value_list[0].get_path(),
                        "old_value_obj": old_value_list[0],
                        "new_value_obj": new_value_list[0],
                    }
                )

    def compare_references(self, old_container, new_container):
        old_ref_obj_list = getattr(old_container.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", [])
        old_ref_dict = {}
        for ref in old_ref_obj_list:
            ref_name = get_definition_ref(ref).split("/")[-1]
            old_ref_dict.setdefault(ref_name, []).append(ref)

        new_ref_obj_list = getattr(new_container.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", [])
        new_ref_dict = {}
        for ref in new_ref_obj_list:
            ref_name = get_definition_ref(ref).split("/")[-1]
            new_ref_dict.setdefault(ref_name, []).append(ref)

        ref_name_set = set(old_ref_dict.keys()) | set(new_ref_dict.keys())
        for ref_name in ref_name_set:
            # If new container has different param with old container, throw an exception
            try:
                new_value_list = new_ref_dict[ref_name]
            except KeyError:
                logger.debug(f"{ref_name} not find in {new_container.get_path()} of new DDD")
                new_value_list = []

            try:
                old_value_list = old_ref_dict[ref_name]
            except KeyError:
                logger.debug(f"{ref_name} not find in {old_container.get_path()} of old DDD")
                old_value_list = []

            # Deal with ref which has more than one value
            old_value_dict = {get_value_ref(old_value): old_value for old_value in old_value_list}
            new_value_dict = {get_value_ref(new_value): new_value for new_value in new_value_list}
            if len(new_value_list) > 1 or len(old_value_list) > 1:
                self.added_ref_list += [
                    {"path": new_value_dict[key].get_path(), "obj": new_value_dict[key]}
                    for key in new_value_dict.keys()
                    if key not in old_value_dict.keys()
                ]
                self.deleted_ref_list += [
                    {"path": old_value_dict[key].get_path(), "obj": old_value_dict[key]}
                    for key in old_value_dict.keys()
                    if key not in new_value_dict.keys()
                ]
            # old value list is empty means this is a new ref param
            elif len(old_value_list) == 0:
                self.added_ref_list += [
                    {"path": new_value_dict[key].get_path(), "obj": new_value_dict[key]}
                    for key in new_value_dict.keys()
                    if key not in old_value_dict.keys()
                ]
            # new value list is empty means this is a removed ref param
            elif len(new_value_list) == 0:
                self.deleted_ref_list += [
                    {"path": old_value_dict[key].get_path(), "obj": old_value_dict[key]}
                    for key in old_value_dict.keys()
                    if key not in new_value_dict.keys()
                ]
            # Check if the value of new and old ref are same
            elif get_value_ref(new_value_list[0]) != get_value_ref(old_value_list[0]):
                self.modified_config_list.append(
                    {
                        "path": new_value_list[0].get_path(),
                        "old_value_obj": old_value_list[0],
                        "new_value_obj": new_value_list[0],
                    }
                )

    def compare_instance_reference(self, old_container, new_container):
        old_iref_obj_list = getattr(old_container.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE", [])
        old_iref_dict = {}
        for iref in old_iref_obj_list:
            iref_name = get_definition_ref(iref).split("/")[-1]
            old_iref_dict.setdefault(iref_name, []).append(iref)

        new_iref_obj_list = getattr(new_container.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE", [])
        new_iref_dict = {}
        for iref in new_iref_obj_list:
            iref_name = get_definition_ref(iref).split("/")[-1]
            new_iref_dict.setdefault(iref_name, []).append(iref)

        iref_name_set = set(old_iref_dict.keys()) | set(new_iref_dict.keys())
        for iref_name in iref_name_set:
            # If new container has different param with old container, throw an exception
            try:
                new_value_list = new_iref_dict[iref_name]
            except KeyError as e:
                print(f"Warning:{iref_name}: not find in new DiagnosticDescriptionData class")
                print(e)
                continue

            try:
                old_value_list = old_iref_dict[iref_name]
            except KeyError as e:
                print(f"Warning:{iref_name}: not find in old DiagnosticDescriptionData class")
                print(e)
                continue

            # Deal with iref which has more than one value
            if len(new_value_list) > 1 or len(old_value_list) > 1:
                old_value_dict = {get_value_iref(old_value): old_value for old_value in old_value_list}
                new_value_dict = {get_value_iref(new_value): new_value for new_value in new_value_list}

                self.added_ref_list += [
                    {"path": new_value_dict[key].get_path(), "obj": new_value_dict[key]}
                    for key in new_value_dict.keys()
                    if key not in old_value_dict.keys()
                ]
                self.deleted_ref_list += [
                    {"path": old_value_dict[key].get_path(), "obj": old_value_dict[key]}
                    for key in old_value_dict.keys()
                    if key not in new_value_dict.keys()
                ]
            # Check if the value of new and old ref are same
            elif (
                get_value_iref(new_value_list[0]) != get_value_iref(old_value_list[0])
                and get_value_iref(new_value_list[0]) is not None
            ):
                self.modified_config_list.append(
                    {
                        "path": new_value_list[0].get_path(),
                        "old_value_obj": old_value_list[0],
                        "new_value_obj": new_value_list[0],
                    }
                )

    def compare_container_trees(self, old_container_tree, new_container_tree):
        # If both trees are empty, treate them as equal
        if not old_container_tree and not new_container_tree:
            return
        # If old tree is empty, it means the new tree has more content, which should be added config
        elif not old_container_tree:
            self.added_container_list.append({"path": new_container_tree.get_path(), "obj": new_container_tree})
        # If new tree is empty, it means the old tree has more content, which should be deleted config
        elif not new_container_tree:
            self.deleted_container_list.append({"path": old_container_tree.get_path(), "obj": old_container_tree})
        else:
            # Compare numerical and textual parameter
            self.compare_parameters(old_container_tree, new_container_tree)

            # Compare reference
            self.compare_references(old_container_tree, new_container_tree)

            # Compare instance reference
            self.compare_instance_reference(old_container_tree, new_container_tree)

            # Iterately compare subcontainers
            old_container_dict = {
                get_short_name(old_container): old_container
                for old_container in getattr(old_container_tree.SUB_CONTAINERS, "ECUC_CONTAINER_VALUE", [])
            }
            new_container_dict = {
                get_short_name(new_container): new_container
                for new_container in getattr(new_container_tree.SUB_CONTAINERS, "ECUC_CONTAINER_VALUE", [])
            }

            key_list = list(dict.fromkeys(list(new_container_dict.keys()) + list(old_container_dict.keys())))
            for key in key_list:
                self.compare_container_trees(old_container_dict.get(key, None), new_container_dict.get(key, None))

    def add_container(self, added_container_dict, ecuc_obj):
        added_container_obj = added_container_dict["obj"]
        # Check if the container already exit
        existed_container = ecuc_obj.find(added_container_obj.get_path().replace("InitialEcuC", "ActiveEcuC"))

        # Get parent container whcih needs the new container
        delimiter = "/"
        path_list = added_container_obj.get_path().split(delimiter)
        path_list[1] = "ActiveEcuC"
        path_list.pop()
        parent_container_path = delimiter.join(path_list)
        parent_container = ecuc_obj.find(parent_container_path)
        if parent_container is None:
            logger.debug(f"{parent_container_path} not exit! Stop add [{get_short_name(added_container_obj)}]")
            return

        # If the container already exit, rename the new container
        if existed_container is not None:
            # Find a unique name
            base_name = get_short_name(added_container_obj)
            unique_name = base_name
            i = 1
            while parent_container.find(f"{parent_container_path}/{unique_name}"):
                unique_name = f"{base_name}_{i:03}"
                i += 1

            # Rename the new container
            previous_name = get_short_name(added_container_obj)
            logger.debug(
                f"New container {previous_name} conflict with {existed_container.get_path()}\nRename to {unique_name}"
            )
            set_short_name(added_container_obj, unique_name)

        # Add the new container into corresponding sub container list
        if parent_container.get_tag() == "ECUC-MODULE-CONFIGURATION-VALUES":
            parent_node = parent_container.CONTAINERS
            container_value_str = AutosarUtil.get_arxml_string(added_container_obj, is_root=False)
            AutosarUtil.append_container_value_with_string(parent_node, container_value_str)
        else:
            parent_node = parent_container.SUB_CONTAINERS
            container_value_str = AutosarUtil.get_arxml_string(added_container_obj, is_root=False)
            AutosarUtil.append_container_value_with_string(parent_node, container_value_str)

    def add_param(self, added_param_dict, ecuc_obj):
        ecuc_container_path = added_param_dict["path"].replace("InitialEcuC", "ActiveEcuC")
        param_name = get_definition_ref(added_param_dict["obj"]).split("/")[-1]
        added_obj = added_param_dict["obj"]
        obj_tag: str = added_obj.get_tag()
        # Find the target container
        ecuc_container = ecuc_obj.find(ecuc_container_path)
        if ecuc_container is None:
            return

        # Iterate param of the container, insert the new param item
        tail_idx = -1
        param_list = getattr(ecuc_container.PARAMETER_VALUES, obj_tag.replace("-", "_"), [])
        for idx, param_item in enumerate(param_list):
            if get_definition_ref(param_item).split("/")[-1] == param_name:
                # If find a none value instance, break to modify its value
                if not get_param_or_ref_value(param_item):
                    tail_idx = idx
                    break
                elif get_param_or_ref_value(param_item) != get_param_or_ref_value(added_obj):
                    tail_idx = idx
                else:
                    logger.debug(
                        f"Duplicate value '{get_param_or_ref_value(param_item)}' "
                        f"of {get_definition_ref(added_obj) in {ecuc_container.get_path()}}"
                    )
                    return

        # Cannot find existed instance means invalid ecuc
        if tail_idx == -1:
            logger.exception(f"Missing instance of {get_definition_ref(added_obj) in {ecuc_container.get_path()}}")
            return

        if not get_param_or_ref_value(param_list[tail_idx]):
            set_param_or_ref_value(param_list[tail_idx], get_param_or_ref_value(added_obj))
        else:
            parent_memo = added_obj.parent_object_
            added_obj.parent_object_ = None
            new_param_item = deepcopy(added_obj)
            added_obj.parent_object_ = parent_memo
            ecuc_container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE.insert(tail_idx + 1, new_param_item)

    def add_ref(self, added_ref_dict, ecuc_obj):
        ecuc_container_path = added_ref_dict["path"].replace("InitialEcuC", "ActiveEcuC")
        param_name = get_definition_ref(added_ref_dict["obj"]).split("/")[-1]
        added_obj = added_ref_dict["obj"]
        obj_tag: str = added_obj.get_tag()
        # Find the target container
        ecuc_container = ecuc_obj.find(ecuc_container_path)
        if ecuc_container is None:
            return

        # Iterate param of the container, insert the new param item
        tail_idx = -1
        # Find the idx of the last item which belongs to the same param name
        ref_list = getattr(ecuc_container.REFERENCE_VALUES, obj_tag.replace("-", "_"), [])
        for idx, ref_item in enumerate(ref_list):
            if get_definition_ref(ref_item).split("/")[-1] == param_name:
                # If find a none value instance, break to modify its value
                if not get_param_or_ref_value(ref_item):
                    tail_idx = idx
                    break
                elif get_param_or_ref_value(ref_item) != get_param_or_ref_value(added_obj):
                    tail_idx = idx
                # If already had the same item, mark idx as -1 to skip this insert
                else:
                    logger.debug(
                        f"Duplicate value '{get_param_or_ref_value(ref_item)}' of "
                        f"{get_definition_ref(added_obj) in {ecuc_container.get_path()}}"
                    )
                    return

        # Cannot find existed instance means invalid ecuc
        if tail_idx == -1:
            logger.exception(f"Missing instance of {get_definition_ref(added_obj) in {ecuc_container.get_path()}}")
            return

        if not get_param_or_ref_value(ref_list[tail_idx]):
            set_param_or_ref_value(ref_list[tail_idx], get_param_or_ref_value(added_obj))
        else:
            parent_memo = added_obj.parent_object_
            added_obj.parent_object_ = None
            new_ref_item = deepcopy(added_obj)
            added_obj.parent_object_ = parent_memo
            ecuc_container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE.insert(tail_idx + 1, new_ref_item)

    def modify_config(self, modified_container_dict, ecuc_obj, keep_user_define=True):
        old_value_obj = modified_container_dict["old_value_obj"]
        new_value_obj = modified_container_dict["new_value_obj"]
        container_path = modified_container_dict["path"]

        param_name = get_definition_ref(old_value_obj).split("/")[-1]
        # Find the corresponding param or ref from ecuc obj
        ecuc_container_obj = ecuc_obj.find(container_path.replace("InitialEcuC", "ActiveEcuC"))
        if ecuc_container_obj is None:
            return
        numerical_param_list = getattr(ecuc_container_obj.PARAMETER_VALUES, "ECUC_NUMERICAL_PARAM_VALUE", [])
        textual_param_list = getattr(ecuc_container_obj.PARAMETER_VALUES, "ECUC_TEXTUAL_PARAM_VALUE", [])
        reference_list = getattr(ecuc_container_obj.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", [])
        instance_ref_list = getattr(ecuc_container_obj.REFERENCE_VALUES, "ECUC_INSTANCE_REFERENCE_VALUE", [])
        target_config_obj = None
        for param in numerical_param_list + textual_param_list + reference_list + instance_ref_list:
            if get_definition_ref(param).split("/")[-1] == param_name:
                target_config_obj = param
                break

        # Check if the ecuc obj exists.
        # If not exists, it means user deleted this config. We give up this modification
        if target_config_obj is None:
            return

        # Check the UserDefine flag.
        if keep_user_define:
            # If flag exits, give up this modification
            for annotation in getattr(target_config_obj.ANNOTATIONS, "ANNOTATION", []):
                if annotation.ANNOTATION_ORIGIN.valueOf_ == USER_DEFINE_FLAG:
                    return

        # Modify the config
        set_param_or_ref_value(target_config_obj, get_param_or_ref_value(new_value_obj))

    def delete_container(self, deleted_container_dict, ecuc_obj, keep_user_define=True):
        container_path = deleted_container_dict["path"]

        # Find the corresponding param or ref from ecuc obj
        ecuc_container_obj = ecuc_obj.find(container_path.replace("InitialEcuC", "ActiveEcuC"))

        # Check if the ecuc obj exists.
        # If not exists, it means user deleted this config. We give up this modification
        if ecuc_container_obj is None:
            return

        # Check the UserDefine flag.
        if keep_user_define:
            # If flag exits, give up this modification
            for annotation in getattr(ecuc_container_obj.ANNOTATIONS, "ANNOTATION", []):
                if annotation.ANNOTATION_ORIGIN.valueOf_ == USER_DEFINE_FLAG:
                    return

        # Remove the config
        AutosarUtil.remove_container_value(ecuc_container_obj.get_parent().ECUC_CONTAINER_VALUE, ecuc_container_obj)

    def delete_param(self, deleted_param_dict, ecuc_obj, keep_user_define=True):
        # Find the corresponding container and param item
        deleted_obj = deleted_param_dict["obj"]
        ecuc_container_path = deleted_param_dict["path"].replace("InitialEcuC", "ActiveEcuC")
        ecuc_container = ecuc_obj.find(ecuc_container_path)
        if ecuc_container is None:
            return
        target_item = None

        param_list_tuple = (
            ecuc_container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE,
            ecuc_container.PARAMETER_VALUES.ECUC_TEXTUAL_PARAM_VALUE,
        )
        for param_list in param_list_tuple:
            for param_item in param_list:
                if get_param_or_ref_value(param_item) == get_param_or_ref_value(deleted_obj):
                    target_item = param_item
                    break

            # Check if the item exist
            if target_item is None:
                continue

            # Check if the param item is "UserDefined"
            if keep_user_define:
                # If "UserDefined", keep the param item, give up this deletion
                for annotation in getattr(target_item.ANNOTATIONS, "ANNOTATION", []):
                    if annotation.ANNOTATION_ORIGIN.valueOf_ == USER_DEFINE_FLAG:
                        return

            # If not "UserDefined", delete the param item
            param_list.remove(target_item)
            return

    def delete_ref(self, deleted_ref_dict, ecuc_obj, keep_user_define=True):
        # Find the corresponding container and param item
        deleted_obj = deleted_ref_dict["obj"]
        ecuc_container_path = deleted_ref_dict["path"].replace("InitialEcuC", "ActiveEcuC")
        ecuc_container = ecuc_obj.find(ecuc_container_path)
        if ecuc_container is None:
            return
        target_item = None

        reference_list_tuple = (
            ecuc_container.REFERENCE_VALUES.ECUC_REFERENCE_VALUE,
            ecuc_container.REFERENCE_VALUES.ECUC_INSTANCE_REFERENCE_VALUE,
        )
        for reference_list in reference_list_tuple:
            for ref_item in reference_list:
                if get_param_or_ref_value(ref_item) == get_param_or_ref_value(deleted_obj):
                    target_item = ref_item
                    break

            # Check if the item exist
            if target_item is None:
                continue

            # Check if the param item is "UserDefined"
            if keep_user_define:
                # If "UserDefined", keep the param item, give up this deletion
                for annotation in getattr(target_item.ANNOTATIONS, "ANNOTATION", []):
                    if annotation.ANNOTATION_ORIGIN.valueOf_ == USER_DEFINE_FLAG:
                        return

            # If not "UserDefined", delete the param item
            reference_list.remove(target_item)
            return

    def update_ecuc_config(self, ecuc_obj):
        for modified_config in self.modified_config_list:
            self.modify_config(modified_config, ecuc_obj)

        for added_container in self.added_container_list:
            self.add_container(added_container, ecuc_obj)

        for added_param in self.added_param_list:
            self.add_param(added_param, ecuc_obj)

        for added_ref in self.added_ref_list:
            self.add_ref(added_ref, ecuc_obj)

        for deleted_container in self.deleted_container_list:
            self.delete_container(deleted_container, ecuc_obj)

        for deleted_param in self.deleted_param_list:
            self.delete_param(deleted_param, ecuc_obj)

        for deleted_ref in self.deleted_ref_list:
            self.delete_ref(deleted_ref, ecuc_obj)

        ecuc_obj = AutosarUtil.update_autosar(ecuc_obj)
        # AutosarUtil.save_arxml(ecuc_obj, "D:/fangyifei/vcos/VCOS_Configurator/Studio/import/result.arxml")

        return ecuc_obj

    def has_diff(self):
        return any(
            (
                self.deleted_container_list,
                self.deleted_param_list,
                self.deleted_ref_list,
                self.added_container_list,
                self.added_param_list,
                self.added_ref_list,
                self.modified_config_list,
            )
        )

    def diff_item_to_str(self, item: dict):
        # Parameter check
        if not isinstance(item, dict):
            logger.exception("Invalid item datatype!")
            return "Invalid item datatype!"
        if "path" not in item:
            logger.exception("Item missing necessary key: path!")
            return "Item missing necessary key: path!"
        if "obj" not in item and not all(key in item for key in ("old_value_obj", "new_value_obj")):
            logger.exception("Item missing necessary key: obj/(old_value_obj, new_value_obj)!")
            return "Item missing necessary key: obj/(old_value_obj, new_value_obj)!"

        path = item["path"]
        # If item has "obj", ite means the item is member of added or deleted list
        if "obj" in item:
            obj = item["obj"]
            item_type = obj.get_tag()
            # For container item, {path} is the unique key
            if item_type == "ECUC-CONTAINER-VALUE":
                return path
            # For param or ref item, {path.param/ref_name: value} is the unique key
            else:
                value = get_param_or_ref_value(obj)
                param_ref_name = get_definition_ref(obj).split("/")[-1]
                return f"{path}.{param_ref_name}: {value}"
        # If item not has "obj", ite means the item is member of modified list
        else:
            old_value = get_param_or_ref_value(item["old_value_obj"])
            new_value = get_param_or_ref_value(item["new_value_obj"])
            param_ref_name = get_definition_ref(item["old_value_obj"]).split("/")[-1]
            return f"{path}.{param_ref_name}: {old_value} -> {new_value}"

    def all_diff_string(self):
        diff_str_dict = {
            "added_container": [],
            "added_param": [],
            "added_ref": [],
            "deleted_container": [],
            "deleted_param": [],
            "deleted_ref": [],
            "modified_config": [],
        }
        diff_str_dict["added_container"] = map(self.diff_item_to_str, self.added_container_list)
        diff_str_dict["added_param"] = map(self.diff_item_to_str, self.added_param_list)
        diff_str_dict["added_ref"] = map(self.diff_item_to_str, self.added_ref_list)
        diff_str_dict["deleted_container"] = map(self.diff_item_to_str, self.deleted_container_list)
        diff_str_dict["deleted_param"] = map(self.diff_item_to_str, self.deleted_param_list)
        diff_str_dict["deleted_ref"] = map(self.diff_item_to_str, self.deleted_ref_list)
        diff_str_dict["modified_config"] = map(self.diff_item_to_str, self.modified_config_list)

        return diff_str_dict

    def module_name(self):
        return get_short_name(self.old_config)

    def merge_ecuc(self, disabled_change):
        """
        Apply enabled modification in new_config to old_config
        """

        for added_container in self.added_container_list:
            if self.diff_item_to_str(added_container) not in disabled_change["added_container"]:
                self.add_container(added_container, self.old_config)

        for added_param in self.added_param_list:
            if self.diff_item_to_str(added_param) not in disabled_change["added_param_ref"]:
                self.add_param(added_param, self.old_config)

        for added_ref in self.added_ref_list:
            if self.diff_item_to_str(added_ref) not in disabled_change["added_param_ref"]:
                self.add_ref(added_ref, self.old_config)

        for deleted_container in self.deleted_container_list:
            if self.diff_item_to_str(deleted_container) not in disabled_change["deleted_container"]:
                self.delete_container(deleted_container, self.old_config, keep_user_define=False)

        for deleted_param in self.deleted_param_list:
            if self.diff_item_to_str(deleted_param) not in disabled_change["deleted_param_ref"]:
                self.delete_param(deleted_param, self.old_config, keep_user_define=False)

        for deleted_ref in self.deleted_ref_list:
            if self.diff_item_to_str(deleted_ref) not in disabled_change["deleted_param_ref"]:
                self.delete_ref(deleted_ref, self.old_config, keep_user_define=False)

        for modified_config in self.modified_config_list:
            if self.diff_item_to_str(modified_config) not in disabled_change["modified_config"]:
                self.modify_config(modified_config, self.old_config, keep_user_define=False)

        AutosarUtil.refresh_containers(self.old_config.CONTAINERS)

        # ecuc_obj = self.old_config
        # while parent := ecuc_obj.get_parent():
        #     ecuc_obj = parent
        # AutosarUtil.save_arxml(ecuc_obj, "D:/fangyifei/Desktop/compare/Dcm_ecuc_merge.arxml")
