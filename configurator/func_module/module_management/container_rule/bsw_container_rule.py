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
from basic_func_module.autosar_utils import utils


class BaseContainerRule:

    @classmethod
    def container_create_trigger(cls, item, other_args={}, from_ui=True):
        pass

    @classmethod
    def container_delete_trigger(cls, item_list):
        pass

    @classmethod
    def container_move_trigger(cls, item_list):
        pass

    @classmethod
    def container_check_by_name(cls, container, target_container_def_name: str):
        container_def_name = utils.get_definition_ref(container)
        if container_def_name is not None:
            return container_def_name.endswith(target_container_def_name)
        else:
            return False

    @classmethod
    def children_container_check_by_path(cls, children, target_container_def_name: str):
        if len(children) == 0:
            return False

        container = children[0].get_data()
        return cls.container_check_by_name(container, target_container_def_name)


base_rule_instance = BaseContainerRule()


class NvMContainerRule(BaseContainerRule):

    @classmethod
    def container_create_trigger(cls, item, other_args={}, from_ui=True):
        container = item.get_data()
        row = item.get_row()
        cls.block_identifier_rule_001(container, row)

    @classmethod
    def container_delete_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        row = item_list[-1].get_row()
        cls.block_identifier_rule_002(children, row)

    @classmethod
    def container_move_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        cls.block_identifier_rule_003(children)

    @classmethod
    def block_identifier_rule_001(cls, container, row):
        block_identifier = row
        if hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("NvMNvramBlockIdentifier"):
                utils.set_value(param_value, str(block_identifier + 1))

    @classmethod
    def block_identifier_rule_002(cls, children, row):
        block_identifier = row + 1
        for child in children[row:]:
            container = child.get_data()
            if hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("NvMNvramBlockIdentifier"):
                    utils.set_value(param_value, str(block_identifier))
                    block_identifier += 1

    @classmethod
    def block_identifier_rule_003(cls, children):
        block_identifier = 1
        for child in children:
            container = child.get_data()
            if hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("NvMNvramBlockIdentifier"):
                    utils.set_value(param_value, str(block_identifier))
                    block_identifier += 1


class EcuMContainerRule(BaseContainerRule):

    @classmethod
    def container_create_trigger(cls, item, other_args=None, from_ui=True):
        if other_args is None:
            other_args = {}

        insertion_index = -1
        container = item.get_data()
        row = item.get_row()

        # 所有需要检查的路径
        base_path = "/AUTOSAR/EcucDefs/EcuM/EcuMConfiguration"
        paths_to_check = [
            f"{base_path}/EcuMCommonConfiguration/EcuMDriverInitListZero/EcuMDriverInitItem",
            f"{base_path}/EcuMCommonConfiguration/EcuMDriverRestartList/EcuMDriverInitItem",
            f"{base_path}/EcuMCommonConfiguration/EcuMDriverInitListOne/EcuMDriverInitItem",
            f"{base_path}/EcuMFlexConfiguration/EcuMDriverInitListBswM/EcuMDriverInitItem",
        ]

        for path in paths_to_check:
            if cls.container_check_by_name(container, path):
                insertion_index = cls.module_initial_sorting(container, row, other_args)
                break

        return insertion_index

    @classmethod
    def get_init_phase(cls, item):
        init_phase = None
        parent_ecuc_path = item.get_path()

        if "EcuMDriverInitListZero" in parent_ecuc_path:
            init_phase = "INIT_ZERO"
        elif "EcuMDriverInitListOne" in parent_ecuc_path:
            init_phase = "INIT_ONE"
        elif "EcuMDriverRestartList" in parent_ecuc_path:
            pass
        elif "EcuMDriverInitListTwo" in parent_ecuc_path:
            init_phase = "INIT_TWO"
        elif "EcuMDriverInitListThree" in parent_ecuc_path:
            init_phase = "INIT_THREE"

        return init_phase

    @classmethod
    def module_initial_sorting(cls, container, row, other_args):
        container_list = container.parent_object_.ECUC_CONTAINER_VALUE
        init_function_settings = other_args.get("init_function_settings", {})
        init_phase = cls.get_init_phase(container_list[0])
        if init_function_settings:

            # 剔除最后的 container，它将被重新排序
            if container_list and container_list[-1] == container:
                container_list.pop()

            # 获取 container 的名字，名字就是 init_function_settings 中的 key
            container_name = container.get_path().split("/")[-1]

            # 创建一个包含 container_list 中有 container 名字的集合
            container_names_set = set(container.get_path().split("/")[-1] for container in container_list)

            # 确定 container_list 中 container 应当插入的位置
            # 索引从 init_function_settings 的顺序开始，检查每个 key 是否在 container_names_set 中
            insertion_index = 0
            for key in init_function_settings.keys():
                if key == container_name:
                    # 发现 init_function_settings 中的 key 与 container 名字相同时，停止
                    if init_function_settings[key]["Init Phase"] != init_phase:
                        insertion_index = len(container_list)
                    break
                if key in container_names_set:
                    # 仅当 key 也存在于 container_list 中时，索引才增加
                    insertion_index += 1
            else:
                # 如果 loop 正常完成没有 break 发生，说明没找到匹配的 key
                # 将 container 添加到列表最后
                insertion_index = len(container_list)

            container_list.insert(insertion_index, container)

            return insertion_index


class DemContainerRule(BaseContainerRule):

    @classmethod
    def container_create_trigger(cls, item, other_args={}, from_ui=True):
        container = item.get_data()
        row = item.get_row()
        if cls.container_check_by_name(container, "/Dem/DemConfigSet/DemEventParameter"):
            cls.event_id_rule_001(container, row)
        else:
            pass

    @classmethod
    def container_delete_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        row = item_list[-1].get_row()
        if cls.children_container_check_by_path(children, "/Dem/DemConfigSet/DemEventParameter"):
            cls.event_id_rule_002(children, row)
        else:
            pass

    @classmethod
    def container_move_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        if cls.children_container_check_by_path(children, "/Dem/DemConfigSet/DemEventParameter"):
            cls.event_id_rule_003(children)
        else:
            pass

    @classmethod
    def event_id_rule_001(cls, container, row):
        event_id = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/DemEventId"):
                utils.set_value(param_value, str(event_id + 1))

    @classmethod
    def event_id_rule_002(cls, children, row):
        event_id = row + 1
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/DemEventId"):
                    utils.set_value(param_value, str(event_id))
                    event_id += 1

    @classmethod
    def event_id_rule_003(cls, children):
        event_id = 1
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/DemEventId"):
                    utils.set_value(param_value, str(event_id))
                    event_id += 1


class PduRContainerRule(BaseContainerRule):

    @classmethod
    def container_create_trigger(cls, item, other_args={}, from_ui=True):
        container = item.get_data()
        row = item.get_row()
        if cls.container_check_by_name(container, "/PduR/PduRRoutingPaths/PduRDestPdu"):
            cls.destpduid_rule_001(container, row)
        if cls.container_check_by_name(container, "/PduR/PduRRoutingPaths/PduRSrcPdu"):
            cls.srcpduid_rule_001(container, row)
        if cls.container_check_by_name(container, "/PduR/PduRRoutingPaths/PduRRoutingPathGroup"):
            cls.routingpathgroup_rule_001(container, row)
        else:
            pass

    @classmethod
    def container_delete_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        row = item_list[-1].get_row()
        if cls.children_container_check_by_path(children, "/PduR/PduRRoutingPaths/PduRDestPdu"):
            cls.destpduid_rule_002(children, row)
        if cls.children_container_check_by_path(children, "/PduR/PduRRoutingPaths/PduRSrcPdu"):
            cls.srcpduid_rule_002(children, row)
        if cls.children_container_check_by_path(children, "/PduR/PduRRoutingPaths/PduRRoutingPathGroup"):
            cls.routingpathgroup_rule_002(children, row)
        else:
            pass

    @classmethod
    def container_move_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        if cls.children_container_check_by_path(children, "/PduR/PduRRoutingPaths/PduRDestPdu"):
            cls.destpduid_rule_003(children)
        if cls.children_container_check_by_path(children, "/PduR/PduRRoutingPaths/PduRSrcPdu"):
            cls.srcpduid_rule_003(children)
        if cls.children_container_check_by_path(children, "/PduR/PduRRoutingPaths/PduRRoutingPathGroup"):
            cls.routingpathgroup_rule_003(children)
        else:
            pass

    @classmethod
    def destpduid_rule_001(cls, container, row):
        destpduid = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/PduRDestPduHandleId"):
                utils.set_value(param_value, str(destpduid))

    @classmethod
    def srcpduid_rule_001(cls, container, row):
        srcpduid = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/PduRSourcePduHandleId"):
                utils.set_value(param_value, str(srcpduid))

    @classmethod
    def routingpathgroup_rule_001(cls, container, row):
        routingpathgroupid = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/PduRRoutingPathGroupId"):
                utils.set_value(param_value, str(routingpathgroupid))

    @classmethod
    def destpduid_rule_002(cls, children, row):
        destpduid = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/PduRDestPduHandleId"):
                    utils.set_value(param_value, str(destpduid))
                    destpduid += 1

    @classmethod
    def srcpduid_rule_002(cls, children, row):
        srcpduid = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/PduRSourcePduHandleId"):
                    utils.set_value(param_value, str(srcpduid))
                    srcpduid += 1

    @classmethod
    def routingpathgroup_rule_002(cls, children, row):
        routingpathgroupid = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/PduRRoutingPathGroupId"):
                    utils.set_value(param_value, str(routingpathgroupid))
                    routingpathgroupid += 1

    @classmethod
    def destpduid_rule_003(cls, children):
        destpduid = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/PduRDestPduHandleId"):
                    utils.set_value(param_value, str(destpduid))
                    destpduid += 1

    @classmethod
    def srcpduid_rule_003(cls, children):
        srcpduid = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/PduRSourcePduHandleId"):
                    utils.set_value(param_value, str(srcpduid))
                    srcpduid += 1

    @classmethod
    def routingpathgroup_rule_003(cls, children):
        routingpathgroupid = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/PduRRoutingPathGroupId"):
                    utils.set_value(param_value, str(routingpathgroupid))
                    routingpathgroupid += 1


class FiMContainerRule(BaseContainerRule):
    @classmethod
    def container_create_trigger(cls, item, other_args={}, from_ui=True):
        container = item.get_data()
        row = item.get_row()
        if cls.container_check_by_name(container, "/FiM/FiMConfigSet/FiMFID"):
            cls.function_id_rule_001(container, row)
        else:
            pass

    @classmethod
    def container_delete_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        row = item_list[-1].get_row()
        if cls.children_container_check_by_path(children, "/FiM/FiMConfigSet/FiMFID"):
            cls.function_id_rule_002(children, row)
        else:
            pass

    @classmethod
    def container_move_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        if cls.children_container_check_by_path(children, "/FiM/FiMConfigSet/FiMFID"):
            cls.function_id_rule_003(children)
        else:
            pass

    @classmethod
    def function_id_rule_001(cls, container, row):
        function_id = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/FiMFunctionId"):
                utils.set_value(param_value, str(function_id))

    @classmethod
    def function_id_rule_002(cls, children, row):
        function_id = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/FiMFunctionId"):
                    utils.set_value(param_value, str(function_id))
                    function_id += 1

    @classmethod
    def function_id_rule_003(cls, children):
        function_id = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/FiMFunctionId"):
                    utils.set_value(param_value, str(function_id))
                    function_id += 1


class CanTSynContainerRule(BaseContainerRule):

    @classmethod
    def container_create_trigger(cls, item, other_args={}, from_ui=True):
        container = item.get_data()
        row = item.get_row()
        if cls.container_check_by_name(
            container,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeSyncDataIDList/CanTSynGlobalTimeSyncDataIDListElement",
        ):
            cls.CanTSynGlobalTimeSyncDataIDListIndex_rule_001(container, row)
        if cls.container_check_by_name(
            container,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeFupDataIDList/CanTSynGlobalTimeFupDataIDListElement",
        ):
            cls.CanTSynGlobalTimeFupDataIDListIndex_rule_001(container, row)
        if cls.container_check_by_name(
            container,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeOfnsDataIDList/CanTSynGlobalTimeOfnsDataIDListElement",
        ):
            cls.CanTSynGlobalTimeOfnsDataIDListIndex_rule_001(container, row)
        if cls.container_check_by_name(
            container,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeOfsDataIDList/CanTSynGlobalTimeOfsDataIDListElement",
        ):
            cls.CanTSynGlobalTimeOfsDataIDListIndex_rule_001(container, row)
        else:
            pass

    @classmethod
    def container_delete_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        row = item_list[-1].get_row()
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeSyncDataIDList/CanTSynGlobalTimeSyncDataIDListElement",
        ):
            cls.CanTSynGlobalTimeSyncDataIDListIndex_rule_002(children, row)
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeFupDataIDList/CanTSynGlobalTimeFupDataIDListElement",
        ):
            cls.CanTSynGlobalTimeFupDataIDListIndex_rule_002(children, row)
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeOfnsDataIDList/CanTSynGlobalTimeOfnsDataIDListElement",
        ):
            cls.CanTSynGlobalTimeOfnsDataIDListIndex_rule_002(children, row)
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeOfsDataIDList/CanTSynGlobalTimeOfsDataIDListElement",
        ):
            cls.CanTSynGlobalTimeOfsDataIDListIndex_rule_002(children, row)
        else:
            pass

    @classmethod
    def container_move_trigger(cls, item_list):
        if len(item_list) == 0:
            return
        parent_item = item_list[0].get_parent()
        children = parent_item.get_children()
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeSyncDataIDList/CanTSynGlobalTimeSyncDataIDListElement",
        ):
            cls.CanTSynGlobalTimeSyncDataIDListIndex_rule_003(children)
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeFupDataIDList/CanTSynGlobalTimeFupDataIDListElement",
        ):
            cls.CanTSynGlobalTimeFupDataIDListIndex_rule_003(children)
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeOfnsDataIDList/CanTSynGlobalTimeOfnsDataIDListElement",
        ):
            cls.CanTSynGlobalTimeOfnsDataIDListIndex_rule_003(children)
        if cls.children_container_check_by_path(
            children,
            "/CanTSyn/CanTSynGlobalTimeDomain/CanTSynGlobalTimeOfsDataIDList/CanTSynGlobalTimeOfsDataIDListElement",
        ):
            cls.CanTSynGlobalTimeOfsDataIDListIndex_rule_003(children)
        else:
            pass

    @classmethod
    def CanTSynGlobalTimeSyncDataIDListIndex_rule_001(cls, container, row):
        CanTSynGlobalTimeSyncDataIDListIndex = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/CanTSynGlobalTimeSyncDataIDListIndex"):
                utils.set_value(param_value, str(CanTSynGlobalTimeSyncDataIDListIndex))

    @classmethod
    def CanTSynGlobalTimeFupDataIDListIndex_rule_001(cls, container, row):
        CanTSynGlobalTimeFupDataIDListIndex = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/CanTSynGlobalTimeFupDataIDListIndex"):
                utils.set_value(param_value, str(CanTSynGlobalTimeFupDataIDListIndex))

    @classmethod
    def CanTSynGlobalTimeOfnsDataIDListIndex_rule_001(cls, container, row):
        CanTSynGlobalTimeOfnsDataIDListIndex = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/CanTSynGlobalTimeOfnsDataIDListIndex"):
                utils.set_value(param_value, str(CanTSynGlobalTimeOfnsDataIDListIndex))

    @classmethod
    def CanTSynGlobalTimeOfsDataIDListIndex_rule_001(cls, container, row):
        CanTSynGlobalTimeOfsDataIDListIndex = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/CanTSynGlobalTimeOfsDataIDListIndex"):
                utils.set_value(param_value, str(CanTSynGlobalTimeOfsDataIDListIndex))

    @classmethod
    def CanTSynGlobalTimeSyncDataIDListIndex_rule_002(cls, children, row):
        CanTSynGlobalTimeSyncDataIDListIndex = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeSyncDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeSyncDataIDListIndex))
                    CanTSynGlobalTimeSyncDataIDListIndex += 1

    @classmethod
    def CanTSynGlobalTimeFupDataIDListIndex_rule_002(cls, children, row):
        CanTSynGlobalTimeFupDataIDListIndex = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeFupDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeFupDataIDListIndex))
                    CanTSynGlobalTimeFupDataIDListIndex += 1

    @classmethod
    def CanTSynGlobalTimeOfnsDataIDListIndex_rule_002(cls, children, row):
        CanTSynGlobalTimeOfnsDataIDListIndex = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeOfnsDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeOfnsDataIDListIndex))
                    CanTSynGlobalTimeOfnsDataIDListIndex += 1

    @classmethod
    def CanTSynGlobalTimeOfsDataIDListIndex_rule_002(cls, children, row):
        CanTSynGlobalTimeOfsDataIDListIndex = row
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeOfsDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeOfsDataIDListIndex))
                    CanTSynGlobalTimeOfsDataIDListIndex += 1

    @classmethod
    def CanTSynGlobalTimeSyncDataIDListIndex_rule_003(cls, children):
        CanTSynGlobalTimeSyncDataIDListIndex = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeSyncDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeSyncDataIDListIndex))
                    CanTSynGlobalTimeSyncDataIDListIndex += 1

    @classmethod
    def CanTSynGlobalTimeFupDataIDListIndex_rule_003(cls, children):
        CanTSynGlobalTimeFupDataIDListIndex = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeFupDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeFupDataIDListIndex))
                    CanTSynGlobalTimeFupDataIDListIndex += 1

    @classmethod
    def CanTSynGlobalTimeOfnsDataIDListIndex_rule_003(cls, children):
        CanTSynGlobalTimeOfnsDataIDListIndex = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeOfnsDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeOfnsDataIDListIndex))
                    CanTSynGlobalTimeOfnsDataIDListIndex += 1

    @classmethod
    def CanTSynGlobalTimeOfsDataIDListIndex_rule_003(cls, children):
        CanTSynGlobalTimeOfsDataIDListIndex = 0
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/CanTSynGlobalTimeOfsDataIDListIndex"):
                    utils.set_value(param_value, str(CanTSynGlobalTimeOfsDataIDListIndex))
                    CanTSynGlobalTimeOfsDataIDListIndex += 1


class BswMContainerRule(BaseContainerRule):
    @classmethod
    def container_create_trigger(cls, container, other_args={}, from_ui=True):
        if from_ui is False:
            row = len(container.parent_object_.ECUC_CONTAINER_VALUE)
            if cls.container_check_by_name(
                container, "/BswM/BswMConfig/BswMModeControl/BswMActionList/BswMActionListItem"
            ):
                cls.event_id_rule_001(container, row)
            else:
                pass
        else:
            pass

    @classmethod
    def container_delete_trigger(cls, container):
        return

    @classmethod
    def event_id_rule_001(cls, container, row):
        event_id = row
        if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
            return
        for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
            def_ref: str = utils.get_definition_ref(param_value)
            if def_ref.endswith("/BswMActionListItemIndex"):
                utils.set_value(param_value, str(event_id + 1))

    @classmethod
    def event_id_rule_002(cls, children, row):
        event_id = row + 1
        for child in children[row:]:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/BswMActionListItemIndex"):
                    utils.set_value(param_value, str(event_id))
                    event_id += 1

    @classmethod
    def event_id_rule_003(cls, children):
        event_id = 1
        for child in children:
            container = child.get_data()
            if not hasattr(container, "PARAMETER_VALUES") and container.PARAMETER_VALUES is None:
                return
            for param_value in container.PARAMETER_VALUES.ECUC_NUMERICAL_PARAM_VALUE:
                def_ref: str = utils.get_definition_ref(param_value)
                if def_ref.endswith("/DemEventId"):
                    utils.set_value(param_value, str(event_id))
                    event_id += 1


RULE_DICT = {
    "NvM": NvMContainerRule,
    "EcuM": EcuMContainerRule,
    "Dem": DemContainerRule,
    "PduR": PduRContainerRule,
    "FiM": FiMContainerRule,
    "CanTSyn": CanTSynContainerRule,
    "BswM": BswMContainerRule,
}
