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
"""
通信矩阵(DBC)对象定义模块.

定义了生成代码所需要的各类对象.
"""
from basic_func_module.base_logger import logger


class SignalGroupsDBC:
    """
    Signal groups in the communication matrix file

    Attributes:
      signal_group_name:
      repetitions:
      group_signals_name:
    """

    def __init__(self, **kwargs):
        """Init Class."""
        arg_dict = {}
        arg_dict["signal_group_name"] = ""
        arg_dict["repetitions"] = ""
        arg_dict["group_signals_name"] = ""

        for key, value in kwargs.items():
            if key not in arg_dict:
                raise RuntimeError(f'Unknown kwarg "{key}"')
            arg_dict[key] = value

        self.signal_group_name = "SG_" + arg_dict["signal_group_name"]
        self.repetitions = arg_dict["repetitions"]
        self.group_signals_name = arg_dict["group_signals_name"]


class SignalDBC:
    """
    Signals in the communication matrix file

    Attributes:
      signal_name:
      initial: Initial value of the signal
      start: The start bit of the signal
      is_signed: Is a signed type, and the length determines the data type
      maximum:
      minimum:
      is_float: Whether the value is floating point
      offset: Used for data transformation
      scale: Used for data transformation
      is_multiplexer: Multiplexing correlation
      multiplexer_ids: Multiplexing correlation
      multiplexer_signal: Multiplexing correlation
      invalid:
      spn:
      unit:
      byte_order:
      choices:
      receivers: The node that receives the signal
    """

    def __init__(self, **kwargs):
        """Init Class."""
        arg_dict = {}
        arg_dict["signal_name"] = ""
        arg_dict["signal_alias_name"] = ""
        arg_dict["initial"] = ""
        arg_dict["start"] = ""
        arg_dict["is_signed"] = ""
        arg_dict["length"] = ""
        arg_dict["maximum"] = ""
        arg_dict["minimum"] = ""
        arg_dict["is_float"] = ""
        arg_dict["offset"] = ""
        arg_dict["scale"] = ""
        arg_dict["is_multiplexer"] = ""
        arg_dict["multiplexer_ids"] = ""
        arg_dict["multiplexer_signal"] = ""
        arg_dict["invalid"] = ""
        arg_dict["spn"] = ""
        arg_dict["unit"] = ""
        arg_dict["byte_order"] = ""
        arg_dict["choices"] = ""
        arg_dict["signal_attributes"] = ""
        arg_dict["receivers"] = ""

        for key, value in kwargs.items():
            if key not in arg_dict:
                raise RuntimeError(f'Unknown kwarg "{key}"')
            arg_dict[key] = value

        self.signal_name = arg_dict["signal_name"]
        self.signal_alias_name = arg_dict["signal_alias_name"]
        self.initial = arg_dict["initial"]
        self.start = arg_dict["start"]
        self.is_signed = arg_dict["is_signed"]
        self.length = arg_dict["length"]
        self.maximum = arg_dict["maximum"]
        self.minimum = arg_dict["minimum"]
        self.is_float = arg_dict["is_float"]
        self.offset = arg_dict["offset"]
        self.scale = arg_dict["scale"]
        self.is_multiplexer = arg_dict["is_multiplexer"]
        self.multiplexer_ids = arg_dict["multiplexer_ids"]
        self.multiplexer_signal = arg_dict["multiplexer_signal"]
        self.invalid = arg_dict["invalid"]
        self.spn = arg_dict["spn"]
        self.unit = arg_dict["unit"]
        self.byte_order = arg_dict["byte_order"]
        self.choices = arg_dict["choices"]
        self.signal_attributes = arg_dict["signal_attributes"]
        self.receivers = arg_dict["receivers"]


class MessageDBC:
    """

    Message in the communication matrix file, which contains Signal

    Attributes:
      message_name:
      bus_name: The network node to which the message belongs
      frame_id:
      header_byte_order:
      header_id:
      is_container: Whether for the container
      is_extended_frame: Whether it is an extended frame
      is_fd: Whether fd
      length:
      protocol:
      send_type: Send type (event, period)
      senders: Owner of message
    """

    def __init__(self, **kwargs):
        """Init Class."""
        arg_dict = {}
        arg_dict["message_name"] = ""
        arg_dict["bus_name"] = ""
        arg_dict["message_alias_name"] = ""
        arg_dict["frame_id"] = ""
        arg_dict["header_byte_order"] = ""
        arg_dict["header_id"] = ""
        arg_dict["is_container"] = ""
        arg_dict["is_extended_frame"] = ""
        arg_dict["is_fd"] = ""
        arg_dict["length"] = ""
        arg_dict["protocol"] = ""
        arg_dict["send_type"] = ""
        arg_dict["senders"] = ""
        arg_dict["has_signal_groups"] = ""
        arg_dict["signal_groups"] = ""
        arg_dict["message_attributes"] = ""
        arg_dict["signals"] = ""

        for key, value in kwargs.items():
            if key not in arg_dict:
                logger.error(f'Unknown kwarg "{key}"')
                raise RuntimeError(f'Unknown kwarg "{key}"')
            arg_dict[key] = value

        self.message_name = arg_dict["message_name"]
        self.bus_name = arg_dict["bus_name"]
        self.message_alias_name = arg_dict["message_alias_name"]
        self.frame_id = arg_dict["frame_id"]
        self.header_byte_order = arg_dict["header_byte_order"]
        self.header_id = arg_dict["header_id"]
        self.is_container = arg_dict["is_container"]
        self.is_extended_frame = arg_dict["is_extended_frame"]
        self.is_fd = arg_dict["is_fd"]
        self.length = arg_dict["length"]
        self.protocol = arg_dict["protocol"]
        self.send_type = arg_dict["send_type"]
        self.senders = arg_dict["senders"]
        self.has_signal_groups = arg_dict["has_signal_groups"]
        self.signal_groups = arg_dict["signal_groups"]
        self.message_attributes = arg_dict["message_attributes"]
        self.signals = arg_dict["signals"]
