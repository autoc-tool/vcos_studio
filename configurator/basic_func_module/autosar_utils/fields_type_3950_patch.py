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
from autosar44 import autosar44


class FIELDSType3950Patch(autosar44.FIELDSType3950):

    @classmethod
    def init(cls):
        autosar44.FIELDSType3950 = FIELDSType3950Patch

    def _exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:AR="http://autosar.org/schema/r4.0"',
        name_="FIELDSType3950",
        fromsubclass_=False,
        pretty_print=True,
    ):
        all_value_specification = []
        all_value_specification.extend(self.APPLICATION_ASSOC_MAP_VALUE_SPECIFICATION)
        all_value_specification.extend(self.APPLICATION_RULE_BASED_VALUE_SPECIFICATION)
        all_value_specification.extend(self.APPLICATION_VALUE_SPECIFICATION)
        all_value_specification.extend(self.ARRAY_VALUE_SPECIFICATION)
        all_value_specification.extend(self.COMPOSITE_RULE_BASED_VALUE_SPECIFICATION)
        all_value_specification.extend(self.CONSTANT_REFERENCE)
        all_value_specification.extend(self.NOT_AVAILABLE_VALUE_SPECIFICATION)
        all_value_specification.extend(self.NUMERICAL_RULE_BASED_VALUE_SPECIFICATION)
        all_value_specification.extend(self.NUMERICAL_VALUE_SPECIFICATION)
        all_value_specification.extend(self.RECORD_VALUE_SPECIFICATION)
        all_value_specification.extend(self.REFERENCE_VALUE_SPECIFICATION)
        all_value_specification.extend(self.TEXT_VALUE_SPECIFICATION)
        all_value_specification.sort(key=lambda x: x.index)
        for value_specification in all_value_specification:
            value_specification.export(
                outfile,
                level,
                namespaceprefix_="",
                namespacedef_="",
                name_=value_specification.original_tagname_,
                pretty_print=pretty_print,
            )

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if autosar44.SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self._buildAttributes(node, node.attrib, already_processed)
        for i, child in enumerate(node):
            nodeName_ = autosar44.Tag_pattern_.match(child.tag).groups()[-1]
            self._buildChildren(child, node, nodeName_, gds_collector_=gds_collector_, index=i)
        return self

    def _buildChildren(self, child_, node, nodeName_: str, fromsubclass_=False, gds_collector_=None, index=0):
        super()._buildChildren(child_, node, nodeName_, fromsubclass_=fromsubclass_, gds_collector_=gds_collector_)
        obj = getattr(self, nodeName_.replace("-", "_"), [])[-1]
        if obj:
            setattr(obj, "index", index)
