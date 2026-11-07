# This Python file uses the following encoding: utf-8
"""Fixtures for Rte task-mapping handling of schema-valid, sparsely written ECUC.

fixtures/minimal_system_re/pc is the PC ``minimal_system_re`` project as configured by AutoC (CAN/PduR/CanIf
modules and diagnostics dropped, enabled modules reduced accordingly). Its Rte_ecuc.arxml writes only the values
it sets: no RteBswUsedOsEventRef/RteBswUsedOsAlarmRef/RteBswImplementationRef etc. slots.
"""
import os
import sys

import pytest

CONFIGURATOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _path in (CONFIGURATOR_DIR, os.path.join(CONFIGURATOR_DIR, "third_party")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

FIXTURE_PROJECT_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "minimal_system_re", "pc")
FIXTURE_CONFIG_DIR = os.path.join(FIXTURE_PROJECT_DIR, "config")
RTE_BSWMD = os.path.join(
    CONFIGURATOR_DIR, "func_module", "module_management", "base_config", "common", "bswmd", "Rte_bswmd.arxml"
)


def parse_arxml(path):
    from basic_func_module.file_handler.file_io_handler import FileIOHandler

    return FileIOHandler.parse_arxml_file(path)


def parse_arxml_text(tmp_path, text, name="input.arxml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return parse_arxml(str(path))


@pytest.fixture(scope="session")
def rte_mod():
    return parse_arxml(RTE_BSWMD)


@pytest.fixture
def fixture_rte(tmp_path):
    with open(os.path.join(FIXTURE_CONFIG_DIR, "bsw", "Rte", "Rte_ecuc.arxml"), encoding="utf-8") as f:
        return parse_arxml_text(tmp_path, f.read(), "Rte_ecuc.arxml")
