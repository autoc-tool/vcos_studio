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
from typing import List, Dict, Tuple
from basic_func_module.file_handler.sidl.parser import parse_sidl_file


class DataTypeConflictError(Exception):

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ServiceConflictError(Exception):

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class DataTypeNotFoundError(Exception):

    def __init__(self, *args: object) -> None:
        self.__message = args[0]
        super().__init__(*args)

    @property
    def message(self):
        return self.__message


class SidlDataPool:

    PRIMITIVE_TYPES = (
        "char",
        "int8",
        "uint8",
        "int16",
        "uint16",
        "int32",
        "uint32",
        "int64",
        "uint64",
        "float",
        "double",
        "boolean",
        "string",
    )

    def __init__(self, sidl_list: List) -> None:
        self.primary_info = {}
        for sidl in sidl_list:
            info = parse_sidl_file(sidl)
            self.primary_info.update({sidl: info})

        self.data_type_pool, self.typedef_pool = self.gather_data_type()
        self.service_pool = self.gather_service()
        self.sidl_dict = self.merge_sidl_dicts()

    def gather_data_type(self):
        def_type_tuple = ("enum", "struct")
        data_type_pool: Dict[str, Dict] = {}
        # Gather all datatype
        for file, sidl in self.primary_info.items():
            for t in def_type_tuple:
                for dt in sidl[t]:  # dt is abbrevation of def_type
                    name = dt["name"]
                    if name not in data_type_pool:
                        data_type_pool[name] = {"def_type": t, "file": file, "primary": dt}
                    else:
                        conf_file = data_type_pool[name]["file"]
                        conf_type = data_type_pool[name]["def_type"]
                        raise DataTypeConflictError(
                            f"Conflicting types:\n{file}:{t} {name} <->\n{conf_file}:{conf_type} {name}"
                        )

        # Should not merge typedef_pool with datatype_pool,
        # as typedef alias may duplicate with datatype, e.g."typedef A A",
        typedef_pool: Dict[str, Dict] = {}
        for file, sidl in self.primary_info.items():
            for td in sidl["typedef"]:  # td is abbrevation of typedef
                origin_type = td["origin_type"]["type"]
                origin_name = td["origin_type"]["data_type"]
                alias = td["alias"]
                # Simple record redundant typedef
                if origin_type == "single" and origin_name == alias:
                    typedef_pool[alias] = {"def_type": "typedef", "file": file, "primary": td}
                    continue

                # Check if typedef conflict
                if alias in data_type_pool or alias in typedef_pool:
                    conf_file = data_type_pool[alias]["file"]
                    conf_type = data_type_pool[alias]["def_type"]
                    raise DataTypeConflictError(
                        f"Conflicting types:\n{file}:typedef {alias} <->\n{conf_file}:{conf_type} {alias}"
                    )
                else:
                    typedef_pool[alias] = {"def_type": "typedef", "file": file, "primary": td}

        return data_type_pool, typedef_pool

    def gather_service(self):
        service_pool: Dict[str, Dict] = {}
        for file, sidl in self.primary_info.items():
            for service in sidl["service"]:
                name = service["name"]
                if name not in service_pool:
                    service_pool[name] = {"file": file, "primary": service}
                else:
                    conf_file = service_pool[name]["file"]
                    raise ServiceConflictError(f"Conflicting services:\n{file}: {name} <->\n{conf_file}: {name}")

        return service_pool

    def get_type_form(self, type_name):
        # For void type, return "void" dict
        if type_name == "void":
            return "void"

        if type_name in self.PRIMITIVE_TYPES:
            return "primitive"

        pool_record = self.data_type_pool.get(type_name, None) or self.typedef_pool.get(type_name, None)
        if not pool_record:
            raise DataTypeNotFoundError(f"Unknown type name '{type_name}'")
        return pool_record["def_type"]

    def merge_data_type(self):
        merged_dict = {"enum": [], "struct": [], "typedef": []}
        # Merge data types from all sidl files
        for typedef in self.data_type_pool.values():
            type = typedef["def_type"]
            primary = typedef["primary"]

            # Enrich "struct items" info
            if type == "struct":
                for item in primary["items"]:
                    data_type = item["data_type"]
                    try:
                        form = self.get_type_form(data_type)
                    except DataTypeNotFoundError as e:
                        raise DataTypeNotFoundError(f"{typedef['file']}: {e.message}")
                    item.update({"form": form})

            merged_dict[type].append(primary)

        for typedef in self.typedef_pool.values():
            type = typedef["def_type"]
            primary = typedef["primary"]

            # Enrich "typedef" info
            origin_info = primary["origin_type"]
            data_type = origin_info["data_type"]
            try:
                form = self.get_type_form(data_type)
            except DataTypeNotFoundError as e:
                raise DataTypeNotFoundError(f"{typedef['file']}: {e.message}")
            origin_info.update({"form": form})

            merged_dict[type].append(primary)
        return merged_dict

    def merge_service(self):
        merged_dict = {"service": []}
        # Merge services from all sidl files
        for service in self.service_pool.values():
            file_name = service["file"]
            primary: Dict[str, Dict] = service["primary"]

            # Enrich service info
            enrich_target: Tuple[str] = ("method", "field", "event")
            for target in enrich_target:
                for comm_def in primary[target]:
                    # Enrich "param_list" info
                    enriched_param = []
                    for param_name in comm_def["param_list"]:
                        try:
                            form = self.get_type_form(param_name)
                        except DataTypeNotFoundError as e:
                            msg = e.message
                            raise DataTypeNotFoundError(f"{file_name}: {msg}")
                        info_dict = {"name": param_name, "form": form}
                        enriched_param.append(info_dict)
                    comm_def["param_list"] = enriched_param

                    # Enrich "returns" info
                    if rt := comm_def.get("returns", None):
                        try:
                            form = self.get_type_form(rt)
                        except DataTypeNotFoundError as e:
                            msg = e.message
                            raise DataTypeNotFoundError(f"{file_name}: {msg}")
                        info_dict = {"name": rt, "form": form}
                        comm_def["returns"] = info_dict

            merged_dict["service"].append(primary)

        return merged_dict

    def merge_sidl_dicts(self):
        merged_dict = {}

        merged_dict.update(self.merge_data_type())
        merged_dict.update(self.merge_service())

        return merged_dict
