# This Python file uses the following encoding: utf-8
import os

import pytest

from conftest import FIXTURE_CONFIG_DIR, parse_arxml, parse_arxml_text

RTE_HEADER = """<?xml version="1.0" ?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>ActiveEcuC</SHORT-NAME>
      <ELEMENTS>
        <ECUC-MODULE-CONFIGURATION-VALUES>
          <SHORT-NAME>Rte</SHORT-NAME>
          <DEFINITION-REF DEST="ECUC-MODULE-DEF">/AUTOSAR/EcucDefs/Rte</DEFINITION-REF>
          <CONTAINERS>
"""
RTE_FOOTER = """          </CONTAINERS>
        </ECUC-MODULE-CONFIGURATION-VALUES>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>
"""
D = "/AUTOSAR/EcucDefs/Rte"
CANSM_EVENT = "/AUTOSAR/CanSM_ib_bswmd/BswModuleDescriptions/CanSM/CanSMBehavior/CanSM_MainFunctionTimingEvent0"
SWC_EVENT = "/ComponentTypes/MinimalSystem/MinimalSystem_IB/MinimalSystem_10ms_Ev"
BM = f"{D}/RteBswModuleInstance/RteBswEventToTaskMapping"
SM = f"{D}/RteSwComponentInstance/RteEventToTaskMapping"

# Schema-valid per Rte_bswmd: RteBswModuleConfigurationRef/RteBswImplementationRef [0..1] and
# RteBswUsedOsEventRef/RteBswUsedOsAlarmRef [0..1] are simply not written.
SPARSE_BSW_INSTANCE = f"""
            <ECUC-CONTAINER-VALUE>
              <SHORT-NAME>CanSM</SHORT-NAME>
              <DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">{D}/RteBswModuleInstance</DEFINITION-REF>
              <SUB-CONTAINERS>
                <ECUC-CONTAINER-VALUE>
                  <SHORT-NAME>CanSM_MainFunctionTimingEvent0</SHORT-NAME>
                  <DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">{BM}</DEFINITION-REF>
                  <PARAMETER-VALUES>
                    <ECUC-NUMERICAL-PARAM-VALUE>
                      <DEFINITION-REF DEST="ECUC-INTEGER-PARAM-DEF">{BM}/RteBswPositionInTask</DEFINITION-REF>
                      <VALUE>3</VALUE>
                    </ECUC-NUMERICAL-PARAM-VALUE>
                  </PARAMETER-VALUES>
                  <REFERENCE-VALUES>
                    <ECUC-REFERENCE-VALUE>
                      <DEFINITION-REF DEST="ECUC-FOREIGN-REFERENCE-DEF">{BM}/RteBswEventRef</DEFINITION-REF>
                      <VALUE-REF DEST="BSW-EVENT">{CANSM_EVENT}</VALUE-REF>
                    </ECUC-REFERENCE-VALUE>
                    <ECUC-REFERENCE-VALUE>
                      <DEFINITION-REF DEST="ECUC-REFERENCE-DEF">{BM}/RteBswMappedToTaskRef</DEFINITION-REF>
                      <VALUE-REF DEST="ECUC-CONTAINER-VALUE">/ActiveEcuC/Os/OsTask_5ms</VALUE-REF>
                    </ECUC-REFERENCE-VALUE>
                  </REFERENCE-VALUES>
                </ECUC-CONTAINER-VALUE>
              </SUB-CONTAINERS>
            </ECUC-CONTAINER-VALUE>
"""
SPARSE_SWC_INSTANCE = f"""
            <ECUC-CONTAINER-VALUE>
              <SHORT-NAME>MinimalSystem_EcuSwComposition</SHORT-NAME>
              <DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">{D}/RteSwComponentInstance</DEFINITION-REF>
              <SUB-CONTAINERS>
                <ECUC-CONTAINER-VALUE>
                  <SHORT-NAME>MinimalSystem_10ms_Ev</SHORT-NAME>
                  <DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">{SM}</DEFINITION-REF>
                  <REFERENCE-VALUES>
                    <ECUC-REFERENCE-VALUE>
                      <DEFINITION-REF DEST="ECUC-FOREIGN-REFERENCE-DEF">{SM}/RteEventRef</DEFINITION-REF>
                      <VALUE-REF DEST="RTE-EVENT">{SWC_EVENT}</VALUE-REF>
                    </ECUC-REFERENCE-VALUE>
                  </REFERENCE-VALUES>
                </ECUC-CONTAINER-VALUE>
              </SUB-CONTAINERS>
            </ECUC-CONTAINER-VALUE>
"""


def refs_of(container):
    from basic_func_module.autosar_utils.utils import get_definition_ref, get_value_ref

    return {
        get_definition_ref(r).split("/")[-1]: get_value_ref(r)
        for r in getattr(container.REFERENCE_VALUES, "ECUC_REFERENCE_VALUE", [])
    }


def slot_names(container):
    from func_module.mapping.task_mapping_helper import RteManager
    from basic_func_module.autosar_utils.utils import get_definition_ref

    return sorted(get_definition_ref(v).split("/")[-1] for v in RteManager.get_container_values(container))


def task_info(task_type):
    return {"OsTaskName": "OsTask_5ms", "OsTaskType": task_type}


def bsw_event_info():
    return {
        "Component": "CanSM",
        "Name": "CanSM_MainFunctionTimingEvent0",
        "EventRef": CANSM_EVENT,
        "TriggerEvent": "TimingEvent",
        "Period": 0.005,
        "IsMainFunction": True,
        "IsServiceComponent": False,
    }


@pytest.fixture
def sparse_rte(tmp_path):
    return parse_arxml_text(tmp_path, RTE_HEADER + SPARSE_BSW_INSTANCE + SPARSE_SWC_INSTANCE + RTE_FOOTER)


def test_task_mapping_dict_reads_absent_optional_refs_as_empty(fixture_rte):
    from func_module.mapping.task_mapping_helper import RteManager

    swc_instances, bsw_instances = RteManager.get_rte_task_mapping_info(fixture_rte)

    cansm = bsw_instances["CanSM"]["CanSM_MainFunctionTimingEvent0"]
    assert cansm["RteBswEventRef"] == CANSM_EVENT
    assert cansm["RteBswMappedToTaskRef"] == "/ActiveEcuC/Os/OsTask_5ms"
    assert cansm["RteBswUsedOsEventRef"] is None
    assert cansm["RteBswUsedOsAlarmRef"] is None
    swc = swc_instances["MinimalSystem_EcuSwComposition"]["MinimalSystem_10ms_Ev"]
    assert swc["RteMappedToTaskRef"] == "/ActiveEcuC/Os/OsTask_10ms"
    assert swc["RteUsedOsEventRef"] is None


def test_bsw_instance_without_reference_values_gets_studio_refs(sparse_rte, rte_mod):
    from func_module.mapping.task_mapping_helper import RteManager

    instance = sparse_rte.find("/ActiveEcuC/Rte/CanSM")
    assert instance.REFERENCE_VALUES is None

    RteManager.add_rte_bsw_instance(sparse_rte, rte_mod, instance, 3, task_info("EXTENDED"), bsw_event_info())

    assert refs_of(instance) == {
        "RteBswImplementationRef": None,
        "RteBswModuleConfigurationRef": "/ActiveEcuC/CanSM",
    }
    mapping = refs_of(sparse_rte.find("/ActiveEcuC/Rte/CanSM/CanSM_MainFunctionTimingEvent0"))
    assert mapping["RteBswEventRef"] == CANSM_EVENT
    assert mapping["RteBswMappedToTaskRef"] == "/ActiveEcuC/Os/OsTask_5ms"
    # The OsEvent that TaskMapping adds to the Os task must also be recorded on the Rte side.
    assert mapping["RteBswUsedOsEventRef"] == "/ActiveEcuC/Os/Rte_Ev_Cyclic2_OsTask_5ms_0_5ms"
    assert mapping["RteBswUsedOsAlarmRef"] is None


def test_basic_task_keeps_optional_os_refs_unset(sparse_rte, rte_mod):
    from func_module.mapping.task_mapping_helper import RteManager

    instance = sparse_rte.find("/ActiveEcuC/Rte/CanSM")
    RteManager.add_rte_bsw_instance(sparse_rte, rte_mod, instance, 3, task_info("BASIC"), bsw_event_info())

    mapping = refs_of(sparse_rte.find("/ActiveEcuC/Rte/CanSM/CanSM_MainFunctionTimingEvent0"))
    assert mapping["RteBswUsedOsEventRef"] is None
    assert mapping["RteBswUsedOsAlarmRef"] is None
    assert mapping["RteBswEventRef"] == CANSM_EVENT


def test_swc_mapping_without_optional_slots_records_os_event(sparse_rte, rte_mod):
    from func_module.mapping.task_mapping_helper import RteManager

    swc_instance = sparse_rte.find("/ActiveEcuC/Rte/MinimalSystem_EcuSwComposition")
    event_info = {
        "Component": "MinimalSystem",
        "Name": "MinimalSystem_10ms_Ev",
        "EventRef": SWC_EVENT,
        "TriggerEvent": "TimingEvent",
        "Period": 0.01,
        "IsMainFunction": False,
        "IsServiceComponent": False,
    }
    RteManager.add_rte_swc_instance(sparse_rte, rte_mod, swc_instance, 0, task_info("EXTENDED"), event_info)

    mapping = sparse_rte.find("/ActiveEcuC/Rte/MinimalSystem_EcuSwComposition/MinimalSystem_10ms_Ev")
    refs = refs_of(mapping)
    assert refs["RteEventRef"] == SWC_EVENT
    assert refs["RteMappedToTaskRef"] == "/ActiveEcuC/Os/OsTask_5ms"
    assert refs["RteUsedOsEventRef"] == "/ActiveEcuC/Os/Rte_Ev_Cyclic_OsTask_5ms_0_10ms"
    assert RteManager.get_rte_param_value(sparse_rte, event_info, "PositionInTask") == "0"


def test_completed_slots_match_studio_created_mapping_and_are_idempotent(sparse_rte, rte_mod):
    from basic_func_module.autosar_utils.autosar_util import AutosarUtil
    from func_module.mapping.task_mapping_helper import RteManager

    mapping_def_path = f"{D}/RteBswModuleInstance/RteBswEventToTaskMapping"
    instance = sparse_rte.find("/ActiveEcuC/Rte/CanSM")
    studio_created = AutosarUtil.create_container_value("Reference", rte_mod.find(mapping_def_path), instance)
    sparse = sparse_rte.find("/ActiveEcuC/Rte/CanSM/CanSM_MainFunctionTimingEvent0")

    RteManager.ensure_value_slots(rte_mod, sparse, mapping_def_path)
    RteManager.ensure_value_slots(rte_mod, sparse, mapping_def_path)

    assert slot_names(sparse) == slot_names(studio_created)
    assert refs_of(sparse)["RteBswEventRef"] == CANSM_EVENT


def ib_bswmds():
    ib_dir = os.path.join(FIXTURE_CONFIG_DIR, "internal_behavior")
    return {m: parse_arxml(os.path.join(ib_dir, f"{m}_ib_bswmd.arxml")) for m in ("CanSM", "Com", "ComM", "Rte")}


def test_schedule_table_timing_infos_without_used_os_event_ref(fixture_rte):
    from func_module.mapping.schedule_table_mapping import ScheduleTableManager

    asw = parse_arxml(os.path.join(FIXTURE_CONFIG_DIR, "system", "Asw.arxml"))
    infos = ScheduleTableManager.get_timing_ecuc_infos(None, fixture_rte, asw, ib_bswmds())

    on_5ms = {i["runnable_name"]: i for i in infos["OsTask_5ms"]}
    assert on_5ms["CanSM_MainFunction"]["event_name"] == ""
    assert on_5ms["CanSM_MainFunction"]["position"] == 3
    assert {"Com_MainFunction_Rx", "Com_MainFunction_Tx", "Com_MainFunction_Gw"} <= set(on_5ms)


def test_trigger_event_runnables_without_used_os_refs(fixture_rte):
    from func_module.mapping.task_mapping_info import TaskMappingInfo

    asw = parse_arxml(os.path.join(FIXTURE_CONFIG_DIR, "system", "Asw.arxml"))
    cfgs = TaskMappingInfo.get_runnable_by_trigger_event(fixture_rte, asw, ib_bswmds())

    cansm = [i for i in cfgs["timing"]["OsTask_5ms"] if i["runnable_name"] == "CanSM_MainFunction"]
    assert cansm and cansm[0]["event_name"] == "" and cansm[0]["alarm_ref"] == ""


@pytest.mark.parametrize(
    "target, expected",
    [
        ("/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE/SysCycle", True),
        ("/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE/ActCycle", True),
        ("/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE/NoSuchProto", False),
        ("/ComponentTypes/MinimalSystem", False),
    ],
)
def test_swc_prototype_refs_resolve_in_flat_extract(rte_mod, target, expected):
    from func_module.validation.basic_validation.basic_validation import ValidationRef

    asw = parse_arxml(os.path.join(FIXTURE_CONFIG_DIR, "system", "Asw.arxml"))
    flat_extract = parse_arxml(os.path.join(FIXTURE_CONFIG_DIR, "system", "FlatExtract.arxml"))
    ref_def = rte_mod.find(f"{D}/RteSwComponentInstance/RteSoftwareComponentInstanceRef")

    assert asw.find(target) is None or asw.find(target).get_tag() != "SW-COMPONENT-PROTOTYPE"
    assert ValidationRef.check_external_ref(target, ref_def, {}, asw, {"FlatExtract": flat_extract}, {}) is expected
