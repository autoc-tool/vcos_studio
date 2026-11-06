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
from PySide6.QtCore import Qt
from typing import Callable


class MappingModelConfig:

    def __init__(self) -> None:
        self.callback_handler: Callable = lambda *args, **kwargs: None
        self.mime_types = {"default": "application/x-qabstractitemmodeldatalist"}
        self.supported_drag_actions = Qt.DropActions(Qt.DropAction.IgnoreAction)
        self.supported_drop_actions = Qt.DropActions(Qt.DropAction.IgnoreAction)
        self.alignment_flag = Qt.AlignmentFlag.AlignCenter
        self.supported_check_state = False
        self.supported_multiple_selection = True
