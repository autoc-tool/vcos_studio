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
通信矩阵(LDF)对象定义模块.

定义了生成代码所需要的各类对象.
"""

from basic_func_module.base_logger import logger


class ProductIdLDF:
    """
    ProductId in the communication matrix file

    Attributes:
      function_id: function id
      supplier_id: supplier id
      variant: variant
    """

    def __init__(self, **kwargs):
        """Init Class."""
        arg_dict = {}
        arg_dict["function_id"] = ""
        arg_dict["supplier_id"] = ""
        arg_dict["variant"] = ""

        for key, value in kwargs.items():
            if key not in arg_dict:
                raise RuntimeError(f'Unknown kwarg "{key}"')
            arg_dict[key] = value

        self.function_id = arg_dict["function_id"]
        self.supplier_id = arg_dict["supplier_id"]
        self.variant = arg_dict["variant"]


class AttributeLDF:
    """
    Signals in the communication matrix file

    Attributes:
      jitter: The time difference between the time when a frame packet actually
              starts to be transmitted and the start of the frame time slot
      timebase: time base
      configured_nad: configured nad
      initial_nad: initial nad
      lin_protocol:
      n_as_timeout: n_as timer timeout
      n_as_timeout: n_as timer timeout
      p2_min: P2 timer minimum value
      st_min: st timer minimum value
      product_id:
    """

    def __init__(self, **kwargs):
        """Init Class."""
        arg_dict = {}
        arg_dict["jitter"] = ""
        arg_dict["timebase"] = ""
        arg_dict["configured_nad"] = ""
        arg_dict["initial_nad"] = ""
        arg_dict["lin_protocol"] = ""
        arg_dict["n_as_timeout"] = ""
        arg_dict["n_cr_timeout"] = ""
        arg_dict["p2_min"] = ""
        arg_dict["st_min"] = ""
        arg_dict["product_id"] = ""

        for key, value in kwargs.items():
            if key not in arg_dict:
                raise RuntimeError(f'Unknown kwarg "{key}"')
            arg_dict[key] = value

        self.jitter = arg_dict["jitter"]
        self.timebase = arg_dict["timebase"]
        self.configured_nad = arg_dict["configured_nad"]
        self.initial_nad = arg_dict["initial_nad"]
        self.lin_protocol = arg_dict["lin_protocol"]
        self.n_as_timeout = arg_dict["n_as_timeout"]
        self.n_cr_timeout = arg_dict["n_cr_timeout"]
        self.p2_min = arg_dict["p2_min"]
        self.st_min = arg_dict["st_min"]
        self.product_id = arg_dict["product_id"]


class SignalLDF:
    """
    Signals in the communication matrix file

    Attributes:
      signal_name:
      initial: Initial value of the signal
      start: The start bit of the signal
    """

    def __init__(self, **kwargs):
        """Init Class."""
        arg_dict = {}
        arg_dict["signal_name"] = ""
        arg_dict["signal_alias_name"] = ""
        arg_dict["initial"] = ""
        arg_dict["length"] = ""
        arg_dict["start"] = ""

        for key, value in kwargs.items():
            if key not in arg_dict:
                raise RuntimeError(f'Unknown kwarg "{key}"')
            arg_dict[key] = value

        self.signal_name = arg_dict["signal_name"]
        self.signal_alias_name = arg_dict["signal_alias_name"]
        self.initial = arg_dict["initial"]
        self.length = arg_dict["length"]
        self.start = arg_dict["start"]


class MessageLDF:
    """
    Message in the communication matrix file, which contains Signal

    Attributes:
      message_name:
      frame_id:
      length: The length of the message
      node_name: The node where message resides
      attributes: All attributes of message
      signals: Message all the signals
    """

    def __init__(self, **kwargs):
        """Init Class."""
        arg_dict = {}
        arg_dict["message_name"] = ""
        arg_dict["bus_name"] = ""
        arg_dict["message_alias_name"] = ""
        arg_dict["frame_id"] = ""
        arg_dict["length"] = ""
        arg_dict["node_name"] = ""
        arg_dict["direction"] = ""
        arg_dict["delay_time"] = ""
        arg_dict["attributes"] = ""
        arg_dict["sender"] = ""
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
        self.length = arg_dict["length"]
        self.node_name = arg_dict["node_name"]
        self.direction = arg_dict["direction"]
        self.delay_time = arg_dict["delay_time"]
        self.attributes = arg_dict["attributes"]
        self.signals = arg_dict["signals"]
