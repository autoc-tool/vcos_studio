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
import re
from typing import Optional, Dict
from basic_func_module.autosar_utils.autosar_util import AutosarUtil
from basic_func_module.autosar_utils.utils import set_category, set_lower_limit, set_upper_limit, set_vt
from func_module.health_monitor.logger import logger

EMPTY_ARXML = (
    '<?xml version="1.0" ?>'
    '<AUTOSAR xmlns="http://autosar.org/schema/r4.0" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="http://autosar.org/schema/r4.0 AUTOSAR_00046.xsd">'
    "</AUTOSAR>"
)


def get_signed_min(bit: int):
    return -(2 ** (bit - 1))


def get_signed_max(bit: int):
    return 2 ** (bit - 1) - 1


class SystemExtractGenerator:
    @classmethod
    def add_sub_package(cls, parent_pkg, sub_pkg_name):
        if not parent_pkg.AR_PACKAGES:
            ar_pkgs_node = AutosarUtil.create_ar_packages(parent=parent_pkg)
            parent_pkg.AR_PACKAGES = ar_pkgs_node
        sub_pkg = AutosarUtil.create_ar_package(sub_pkg_name, parent=parent_pkg.AR_PACKAGES)
        parent_pkg.AR_PACKAGES.AR_PACKAGE.append(sub_pkg)

        return sub_pkg

    @classmethod
    def append_compu_method(cls, parent_pkg, compu_method_obj):
        if not parent_pkg.ELEMENTS:
            e_obj = AutosarUtil.create_ar_elements()
            parent_pkg.ELEMENTS = e_obj
            e_obj.set_parent(parent_pkg)

        e_obj = parent_pkg.ELEMENTS
        e_obj.COMPU_METHOD.append(compu_method_obj)

    @classmethod
    def create_compu_method(cls, name, scale, offset, low_lim, up_lim, val_tbl=Optional[Dict]):
        cm_obj = AutosarUtil.create_ar_compu_method(name)
        category = cls.infer_cm_category(scale, offset, val_tbl)
        set_category(cm_obj, category)

        # Generate table items for TEXTTABLE and SCALE_LINEAR_AND_TEXTTABLE
        if category in ("TEXTTABLE", "SCALE_LINEAR_AND_TEXTTABLE"):
            for val, text in val_tbl.items():
                vt_item_obj = cls.create_val_tbl_item(val, text)
                cls.append_compu_scale(cm_obj, vt_item_obj)

        # Generate linear info for LINEAR and SCALE_LINEAR_AND_TEXTTABLE
        if category in ("LINEAR", "SCALE_LINEAR_AND_TEXTTABLE"):
            lc_obj = cls.create_linear_compu(low_lim, up_lim, scale, offset)
            cls.append_compu_scale(cm_obj, lc_obj)

        return cm_obj

    @classmethod
    def infer_cm_category(cls, scale, offset, val_tbl):
        linear = scale != 1 or offset != 0
        text_tbl = val_tbl is not None

        if not linear and text_tbl:
            return "TEXTTABLE"
        if linear and not text_tbl:
            return "LINEAR"
        if linear and text_tbl:
            return "SCALE_LINEAR_AND_TEXTTABLE"
        if not linear and not text_tbl:
            return "IDENTICAL"

    @classmethod
    def append_compu_scale(cls, compu_method_obj, compu_scale_obj):
        if not compu_method_obj.COMPU_INTERNAL_TO_PHYS:
            c_obj = AutosarUtil.crate_compu_internal_to_phys()
            compu_method_obj.COMPU_INTERNAL_TO_PHYS = c_obj
            c_obj.set_parent(compu_method_obj)

        citp_obj = compu_method_obj.COMPU_INTERNAL_TO_PHYS
        if not citp_obj.COMPU_SCALES:
            cs_s_obj = AutosarUtil.create_compu_scales()
            citp_obj.COMPU_SCALES = cs_s_obj
            cs_s_obj.set_parent(citp_obj)

        cs_s_obj = citp_obj.COMPU_SCALES
        cs_s_obj.COMPU_SCALE.append(compu_scale_obj)

    @classmethod
    def format_text(cls, text: str):
        if bool(re.match("^[a-zA-Z0-9_]+$", text)):
            return text

        char_list = []
        for c in text:
            if not bool(re.match("^[a-zA-Z0-9_]+$", c)):
                char_list.append(" ")
            else:
                char_list.append(c)
        text = "".join(char_list)
        text = text.strip()
        text = re.sub(r"\s+", "_", text)

        return text

    @classmethod
    def create_val_tbl_item(cls, val, text):
        # LOWER-LIMIT and UPPER-LIMIT
        cs_obj = AutosarUtil.create_compu_scale()
        set_lower_limit(cs_obj, str(val))
        set_upper_limit(cs_obj, str(val))

        # DESC
        text = str(text).strip()
        desc_obj = AutosarUtil.create_desc([text])
        cs_obj.DESC = desc_obj
        desc_obj.set_parent(cs_obj)

        # COMPU-CONST
        cc_obj = AutosarUtil.create_compu_const()
        hex_fmt = hex(val)[2:].upper()
        text = cls.format_text(text)
        set_vt(cc_obj, f"Cx{hex_fmt}_{text}")
        cs_obj.COMPU_CONST = cc_obj
        cc_obj.set_parent(cs_obj)

        return cs_obj

    @classmethod
    def create_linear_compu(cls, low_lim, up_lim, scale, offset):
        # LOWER-LIMIT and UPPER-LIMIT
        cs_obj = AutosarUtil.create_compu_scale()
        set_lower_limit(cs_obj, str(low_lim))
        set_upper_limit(cs_obj, str(up_lim))

        # COMPU-RATIONAL-COEFFS
        crc_obj = AutosarUtil.create_compu_rational_coeffs(parent=cs_obj)
        cs_obj.COMPU_RATIONAL_COEFFS = crc_obj
        cn_obj = AutosarUtil.create_compu_numerator(scale, offset, parent=crc_obj)
        crc_obj.COMPU_NUMERATOR = cn_obj
        cd_obj = AutosarUtil.create_compu_denominator(parent=crc_obj)
        crc_obj.COMPU_DENOMINATOR = cd_obj

        return cs_obj

    @classmethod
    def infer_low_upper_lim(self, val_tbl, scale, offset, maximum, minimum, sig_type, sig_size):
        if sig_type.lower().startswith("uint"):
            l_bound = 0
            u_bound = 2**sig_size - 1
        elif sig_type.lower().startswith("sint"):
            l_bound = get_signed_min(sig_size)
            u_bound = get_signed_max(sig_size)
        else:
            l_bound = float("-inf")
            u_bound = float("inf")
            minimum = l_bound if minimum < get_signed_min(64) else minimum
            maximum = u_bound if maximum > get_signed_max(64) else maximum

        low_lim = max(int((minimum - offset) / scale), l_bound) if minimum != float("-inf") else minimum
        up_lim = min(int((maximum - offset) / scale), u_bound) if maximum != float("inf") else maximum
        if val_tbl:
            min_key = min(val_tbl.keys())
            max_key = max(val_tbl.keys())
            low_lim = min(low_lim, min_key)
            up_lim = max(up_lim, max_key)
        return low_lim, up_lim

    @classmethod
    def append_data_const_rule(cls, data_constr_obj, data_constr_rule_obj):
        if not data_constr_obj.DATA_CONSTR_RULES:
            dcr_s_obj = AutosarUtil.create_data_constr_rules(data_constr_obj)
            data_constr_obj.DATA_CONSTR_RULES = dcr_s_obj

        dcr_s_obj = data_constr_obj.DATA_CONSTR_RULES
        data_constr_rule_obj.set_parent(dcr_s_obj)
        dcr_s_obj.DATA_CONSTR_RULE.append(data_constr_rule_obj)

    @classmethod
    def create_data_constr(cls, name, low_lim, up_lim):
        dc_obj = AutosarUtil.create_data_constr(name)

        low_lim = "-INF" if low_lim == float("-inf") else str(low_lim)
        up_lim = "INF" if up_lim == float("inf") else str(up_lim)
        dcr_obj = AutosarUtil.create_data_constr_rule(low_lim, up_lim)

        cls.append_data_const_rule(dc_obj, dcr_obj)

        return dc_obj

    @classmethod
    def append_data_constr(cls, parent_pkg, data_constr_obj):
        if not parent_pkg.ELEMENTS:
            e_obj = AutosarUtil.create_ar_elements()
            parent_pkg.ELEMENTS = e_obj
            e_obj.set_parent(parent_pkg)

        e_obj = parent_pkg.ELEMENTS
        e_obj.DATA_CONSTR.append(data_constr_obj)

    @classmethod
    def append_sw_base_type(cls, parent_pkg, sw_base_type_obj):
        if not parent_pkg.ELEMENTS:
            e_obj = AutosarUtil.create_ar_elements()
            parent_pkg.ELEMENTS = e_obj
            e_obj.set_parent(parent_pkg)

        e_obj = parent_pkg.ELEMENTS
        e_obj.SW_BASE_TYPE.append(sw_base_type_obj)

    def __init__(self, system_extract_obj=None) -> None:
        self.system_extract_obj = system_extract_obj
        if not self.system_extract_obj:
            self.system_extract_obj = AutosarUtil.parse_arxml_string(EMPTY_ARXML)

    def generate(self, dbc_info):
        self.gen_data_type(dbc_info)
        return AutosarUtil.update_autosar(self.system_extract_obj)

    def gen_data_type(self, dbc_info):
        dt_pkg = self.add_sub_package(self.system_extract_obj, "DataType")

        semantics_pkg = self.add_sub_package(dt_pkg, "Semantics")
        constr_pkg = self.add_sub_package(dt_pkg, "Constraint")
        base_type_set = set()
        cm_set = set()
        dc_set = set()
        fail_info_list = []
        sig_gen = (s for dbc_cfg in dbc_info["config"].values() for m in dbc_cfg["details"] for s in m["signals"])
        for sig in sig_gen:
            val_tbl = sig["choices"]
            scale = float(sig["scale"])
            offset = float(sig["offset"])
            maximum = float(0 if not sig["maximum"] else sig["maximum"])
            minimum = float(0 if not sig["minimum"] else sig["minimum"])
            sig_type = sig["signal_type"]
            sig_size = sig["signal_size"]

            # Gen COMPU-METHOD
            cm_name = f"CM_{sig['signal_alias_name']}"
            if cm_name not in cm_set:
                try:
                    low_lim, up_lim = self.infer_low_upper_lim(
                        None, scale, offset, maximum, minimum, sig_type, sig_size
                    )
                    low_lim = get_signed_min(64) if low_lim < get_signed_min(64) else low_lim
                    up_lim = get_signed_max(64) if low_lim > get_signed_max(64) else up_lim
                    cm_obj = self.create_compu_method(
                        cm_name,
                        scale=scale if int(scale) != scale else int(scale),
                        offset=offset if int(offset) != offset else int(offset),
                        low_lim=low_lim,
                        up_lim=up_lim,
                        val_tbl=val_tbl,
                    )
                    self.append_compu_method(semantics_pkg, cm_obj)
                    cm_set.add(cm_name)
                except Exception:
                    logger.exception(f"Gen compu method {cm_name} failed.")
                    fail_info_list.append(f"Gen compu method {cm_name} failed.")
            else:
                logger.debug(f"Compu method {cm_name} already existed.")

            # Gen DATA-CONSTR
            dc_name = f"DC_{sig['signal_alias_name']}"
            if dc_name not in dc_set:
                try:
                    low_lim, up_lim = self.infer_low_upper_lim(
                        val_tbl, scale, offset, maximum, minimum, sig_type, sig_size
                    )
                    dc_obj = self.create_data_constr(dc_name, low_lim, up_lim)
                    self.append_data_constr(constr_pkg, dc_obj)
                    dc_set.add(dc_name)
                except Exception:
                    logger.exception(f"Gen constr {dc_name} failed.")
                    fail_info_list.append(f"Gen constr {dc_name} failed.")
            else:
                logger.debug(f"Constr {dc_name} already existed.")

            base_type_set.add(sig["signal_type"].lower())

        for info in fail_info_list:
            logger.ui_error(info)
        for bt in base_type_set:
            try:
                dt_obj = self.gen_data_type_eles(bt)
                self.append_sw_base_type(dt_pkg, dt_obj)
            except Exception:
                logger.exception(f"Gen data type element {bt} failed.")
                logger.ui_error(f"Gen data type element {bt} failed.")

    def gen_data_type_eles(self, base_type):
        size_tbl = {
            "uint8": 8,
            "uint16": 16,
            "uint32": 32,
            "uint64": 64,
            "uint8_n": 8,
            "sint8": 8,
            "sint16": 16,
            "sint32": 32,
            "sint64": 64,
            "float32": 32,
            "float64": 64,
        }
        encoding_tbl = {
            "uint8": "NONE",
            "uint16": "NONE",
            "uint32": "NONE",
            "uint64": "NONE",
            "uint8_n": "NONE",
            "sint8": "2C",
            "sint16": "2C",
            "sint32": "2C",
            "sint64": "2C",
            "float32": "IEEE754",
            "float64": "IEEE754",
        }
        type_size = size_tbl[base_type]
        type_encoding = encoding_tbl[base_type]
        sbt_obj = AutosarUtil.create_sw_base_type(base_type, "FIXED_LENGTH", type_size, type_encoding)
        return sbt_obj
