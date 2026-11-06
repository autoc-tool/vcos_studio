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
from enum import Enum, IntEnum
from typing import Any, Dict, List, Callable


class MappingAssistantUIType(IntEnum):
    PORT_MAPPING_ASSISTANT = 1  # Port mapping 助手
    DATA_MAPPING_ASSISTANT = 2  # Data mapping 助手
    ASSISTANT_SELECT_COMPONENT_PROTOTYPE = 4  # Port mapping 助手二级Select Component Prototype弹窗
    ASSISTANT_SELECT_PORT_PROTOTYPE = 8  # Port mapping 助手二级Select Port Prototype弹窗
    ASSISTANT_SELECT_REFERENCE_TARGET = 16  # Data mapping 助手二级Select Reference Target弹窗
    SELECT_PORT_PROTOTYPE = 32  # Port Mapping 右键弹窗
    SELECT_SYSTEM_SIGNAL = 64  # Data Mapping 右键弹窗
    SELECT_REFERENCE_TARGET = 128  # Data Mapping 右键二级Select Reference Target弹窗


class MappingAssistantPushButtonType(Enum):
    BACK = "< Back"
    NEXT = "Next >"
    FINISH = "Finish"
    CANCEL = "Cancel"

    def name(self) -> str:
        return self.value


PORT_MAPPING_ASSISTANT_CONFIG = [
    {
        "title": "Select Component Prototypes",
        "header_labels": ["", "Component Prototype", "Component Type"],
        "supported_check_state": True,
        "supported_multiple_selection": True,
        "push_button_dict": {
            MappingAssistantPushButtonType.BACK: False,
            MappingAssistantPushButtonType.NEXT: True,
            MappingAssistantPushButtonType.FINISH: False,
            MappingAssistantPushButtonType.CANCEL: True,
        },
    },
    {
        "title": "Select Port Prototypes",
        "header_labels": ["", "Component Prototype", "Port Prototype", "Already connected"],
        "supported_check_state": True,
        "supported_multiple_selection": True,
        "push_button_dict": {
            MappingAssistantPushButtonType.BACK: False,
            MappingAssistantPushButtonType.NEXT: True,
            MappingAssistantPushButtonType.FINISH: False,
            MappingAssistantPushButtonType.CANCEL: True,
        },
    },
    {
        "title": "Component Connection Confirm",
        "header_labels": [
            "Component Prototype",
            "Port Prototype",
            "Port Interface",
            "Connected Component Prototype",
            "Connected Port Prototype",
            "Connected Port Interface",
            "Port Interface Mapping",
        ],
        "supported_check_state": False,
        "supported_multiple_selection": False,
        "push_button_dict": {
            MappingAssistantPushButtonType.BACK: False,
            MappingAssistantPushButtonType.NEXT: True,
            MappingAssistantPushButtonType.FINISH: False,
            MappingAssistantPushButtonType.CANCEL: True,
        },
        "header_labels_dialog_dict": {
            "Connected Component Prototype": MappingAssistantUIType.ASSISTANT_SELECT_COMPONENT_PROTOTYPE,
            "Connected Port Prototype": MappingAssistantUIType.ASSISTANT_SELECT_PORT_PROTOTYPE,
        },
    },
]
DATA_MAPPING_ASSISTANT_CONFIG = [
    {
        "title": "Select Port Prototypes",
        "header_labels": [
            "",
            "Component",
            "Port Prototype",
            "Communication Element",
            "Direction",
            "Mapped System Signals",
            "Channel",
            "Cluster",
            "PDU",
            "Frame",
            "Com/LdCom",
        ],
        "supported_check_state": True,
        "supported_multiple_selection": True,
        "push_button_dict": {
            MappingAssistantPushButtonType.BACK: False,
            MappingAssistantPushButtonType.NEXT: True,
            MappingAssistantPushButtonType.FINISH: False,
            MappingAssistantPushButtonType.CANCEL: True,
        },
    },
    {
        "title": "Data Mapping Confirm",
        "header_labels": [
            "Communication Element",
            "Component",
            "Port Prototype",
            "Direction",
            "Compatibility",
            "System Signal to be Mapped",
            "Channel",
            "Cluster",
            "PDU",
            "Frame",
            "Com/LdCom",
        ],
        "supported_check_state": False,
        "supported_multiple_selection": False,
        "push_button_dict": {
            MappingAssistantPushButtonType.BACK: False,
            MappingAssistantPushButtonType.NEXT: True,
            MappingAssistantPushButtonType.FINISH: False,
            MappingAssistantPushButtonType.CANCEL: True,
        },
        "header_labels_dialog_dict": {
            "System Signal to be Mapped": MappingAssistantUIType.ASSISTANT_SELECT_REFERENCE_TARGET
        },
    },
]
SELECT_DIALOG_DICT = {
    "Select Component Prototype": {
        "title": "Select Component Prototype",
        "header_labels": ["", "Component Prototype"],
        "supported_check_state": True,
        "supported_multiple_selection": True,
        "push_button_dict": {MappingAssistantPushButtonType.FINISH: True, MappingAssistantPushButtonType.CANCEL: True},
        "header_labels_dialog_dict": {},
    },
    "Select Port Prototype": {
        "title": "Select Port Prototype",
        "header_labels": [
            "",
            "Compatibility",
            "Component Prototype",
            "Port Prototype",
            "Port Interface",
            "Port Interface Mapping",
            "Port Interface Mapping Set",
        ],
        "supported_check_state": True,
        "supported_multiple_selection": True,
        "push_button_dict": {MappingAssistantPushButtonType.FINISH: True, MappingAssistantPushButtonType.CANCEL: True},
        "header_labels_dialog_dict": {},
    },
    "Select System Signal": {
        "title": "Select System Signal",
        "header_labels": [
            "Communication Element",
            "Component",
            "Port Prototype",
            "Direction",
            "Compatibility",
            "System Signal to be Mapped",
            "Channel",
            "Cluster",
            "PDU",
            "Frame",
            "Com/LdCom",
        ],
        "supported_check_state": False,
        "supported_multiple_selection": False,
        "push_button_dict": {MappingAssistantPushButtonType.FINISH: True, MappingAssistantPushButtonType.CANCEL: True},
        "header_labels_dialog_dict": {"System Signal to be Mapped": MappingAssistantUIType.SELECT_REFERENCE_TARGET},
    },
    "Select Reference Target": {
        "title": "Select Reference Target",
        "header_labels": ["", "Name", "Serialized", "Channel", "Cluster", "PDU", "Frame"],
        "supported_check_state": True,
        "supported_multiple_selection": False,
        "push_button_dict": {MappingAssistantPushButtonType.FINISH: True, MappingAssistantPushButtonType.CANCEL: True},
        "header_labels_dialog_dict": {},
        "resize_column_to_contents": [],
    },
}


class MappingAssistantUIConfig:

    def __init__(self, mapping_ui_type: MappingAssistantUIType):
        self.mapping_ui_type = mapping_ui_type
        self.has_filter_control = False
        self.input_data: Any = None
        self.table_data: Any = None
        self.callback_handler: Callable = lambda *args, **kwargs: None
        self._page_cfg_dict = {}
        self._page_cfg_dict["current_page"] = {}
        self._page_cfg_dict["current_page_index"] = -1
        self._page_cfg_dict["page_cache_stack"] = []

    @property
    def assistant_cfg(self):
        if self.mapping_ui_type == MappingAssistantUIType.PORT_MAPPING_ASSISTANT:
            assistant_cfg = PORT_MAPPING_ASSISTANT_CONFIG
        elif self.mapping_ui_type == MappingAssistantUIType.DATA_MAPPING_ASSISTANT:
            assistant_cfg = DATA_MAPPING_ASSISTANT_CONFIG
        elif self.mapping_ui_type == MappingAssistantUIType.ASSISTANT_SELECT_COMPONENT_PROTOTYPE:
            assistant_cfg = [SELECT_DIALOG_DICT["Select Component Prototype"]]
        elif self.mapping_ui_type & (
            MappingAssistantUIType.SELECT_PORT_PROTOTYPE | MappingAssistantUIType.ASSISTANT_SELECT_PORT_PROTOTYPE
        ):
            assistant_cfg = [SELECT_DIALOG_DICT["Select Port Prototype"]]
        elif self.mapping_ui_type == MappingAssistantUIType.SELECT_SYSTEM_SIGNAL:
            assistant_cfg = [SELECT_DIALOG_DICT["Select System Signal"]]
        elif self.mapping_ui_type & (
            MappingAssistantUIType.SELECT_REFERENCE_TARGET | MappingAssistantUIType.ASSISTANT_SELECT_REFERENCE_TARGET
        ):
            assistant_cfg = [SELECT_DIALOG_DICT["Select Reference Target"]]
        return assistant_cfg

    @property
    def current_page_title(self) -> str:
        if self._page_cfg_dict["current_page_index"] == -1:
            self.next_page()
        return self._page_cfg_dict["current_page"]["title"]

    @property
    def current_page_header_labels(self) -> List[str]:
        if self._page_cfg_dict["current_page_index"] == -1:
            self.next_page()
        return self._page_cfg_dict["current_page"]["header_labels"]

    @property
    def supported_check_state(self) -> bool:
        if self._page_cfg_dict["current_page_index"] == -1:
            self.next_page()
        return self._page_cfg_dict["current_page"]["supported_check_state"]

    @property
    def supported_multiple_selection(self) -> bool:
        if self._page_cfg_dict["current_page_index"] == -1:
            self.next_page()
        return self._page_cfg_dict["current_page"]["supported_multiple_selection"]

    @property
    def current_page_push_buttons(self) -> Dict[MappingAssistantPushButtonType, bool]:
        if self._page_cfg_dict["current_page_index"] == -1:
            self.next_page()
        return self._page_cfg_dict["current_page"]["push_button_dict"]

    @property
    def current_page_header_label_dialogs(self):
        if self._page_cfg_dict["current_page_index"] == -1:
            self.next_page()
        return self._page_cfg_dict["current_page"].get("header_labels_dialog_dict", {})

    def next_page(self):
        if self.mapping_ui_type & (
            MappingAssistantUIType.PORT_MAPPING_ASSISTANT | MappingAssistantUIType.DATA_MAPPING_ASSISTANT
        ):
            current_page_index = self._page_cfg_dict["current_page_index"]
            if current_page_index + 1 < len(self.assistant_cfg):
                current_page_index += 1
            else:
                return False
        else:
            current_page_index = 0
        self._page_cfg_dict["current_page"] = self.assistant_cfg[current_page_index]
        self._page_cfg_dict["current_page_index"] = current_page_index
        return True

    def previous_page(self):
        if (
            self.mapping_ui_type
            & (MappingAssistantUIType.PORT_MAPPING_ASSISTANT | MappingAssistantUIType.DATA_MAPPING_ASSISTANT)
            == 0
        ):
            return self.next_page()
        current_page_index = self._page_cfg_dict["current_page_index"]
        if current_page_index - 1 >= 0:
            current_page_index -= 1
        else:
            return False
        self._page_cfg_dict["current_page"] = self.assistant_cfg[current_page_index]
        self._page_cfg_dict["current_page_index"] = current_page_index
        return True

    def push_page_cache(self, page_data: Any):
        self._page_cfg_dict["page_cache_stack"].append(page_data)

    def pop_page_cache(self):
        return self._page_cfg_dict["page_cache_stack"].pop()

    def previous_page_cache(self):
        return self._page_cfg_dict["page_cache_stack"][-1]
