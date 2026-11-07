# This Python file uses the following encoding: utf-8
"""Studio verify/save on the AutoC-configured PC minimal_system_re project.

Needs the companion components, so it only runs when VCOS_STUDIO_IT_ROOT points at a vcos tree containing
components/autoc_mcal (configurator_plug_in), components/runtime, components/rt_framework and
components/communication. The Studio under test is always this checkout.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest
from lxml import etree

from conftest import CONFIGURATOR_DIR, FIXTURE_PROJECT_DIR

VCOS_ROOT = os.environ.get("VCOS_STUDIO_IT_ROOT", "")
PLUGIN_DIR = os.path.join(VCOS_ROOT, "components", "autoc_mcal", "configurator_plug_in")
pytestmark = pytest.mark.skipif(
    not (VCOS_ROOT and os.path.isdir(PLUGIN_DIR)),
    reason="set VCOS_STUDIO_IT_ROOT to a vcos tree with components/autoc_mcal/configurator_plug_in",
)

RUNNER = os.path.join(os.path.dirname(__file__), "studio_runner.py")
PROJECT_FILE = "minimal_system_re.vcosproject"
MODULES = "EcuC,Os,Rte"
NS = {"a": "http://autosar.org/schema/r4.0"}
COMPOSITION = "/COM/VCOS2/CFG/WORKFLOW/SYSDESC/SYNC/COMPOSITIONTYPE"
RTE_ECUC = os.path.join("config", "bsw", "Rte", "Rte_ecuc.arxml")
OS_ECUC = os.path.join("config", "bsw", "Os", "Os_ecuc.arxml")


def make_project(tmp_path, name="pc", rte_edit=None, os_edit=None):
    project_dir = tmp_path / name
    shutil.copytree(FIXTURE_PROJECT_DIR, str(project_dir))
    project_file = project_dir / PROJECT_FILE
    cfg = json.loads(project_file.read_text(encoding="utf-8"))
    paths = cfg["path"]
    paths["studio_path"] = CONFIGURATOR_DIR
    paths["mcal_path"] = os.path.join(VCOS_ROOT, "components", "autoc_mcal")
    paths["system_path"] = PLUGIN_DIR
    for key in ("swc_template_path", "bswcallout_path", "application_path"):
        paths[key] = str(tmp_path / "apps" / key)
    project_file.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    for rel, edit in ((RTE_ECUC, rte_edit), (OS_ECUC, os_edit)):
        if edit:
            path = project_dir / rel
            text = path.read_text(encoding="utf-8")
            edited = edit(text)
            assert edited != text
            path.write_text(edited, encoding="utf-8")
    return project_dir


def run_studio(project_dir, mode, save=False):
    args = [sys.executable, RUNNER, str(project_dir / PROJECT_FILE), mode, MODULES] + (["save"] if save else [])
    proc = subprocess.run(args, cwd=CONFIGURATOR_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    out = proc.stdout.decode("utf-8", "replace")
    summary = json.loads(out.strip().splitlines()[-1])
    assert summary["load"] is True, out[-3000:]
    assert summary["crash"] is None, summary["crash"]
    return summary


def errors(summary, code=None):
    found = summary["verify"][0]["errors"]
    return [e for e in found if code is None or e["code"] == code]


def ecuc_values(path):
    """Order-insensitive view of an ECUC file: {container path: sorted [(definition, value), ...]}."""
    tree = etree.parse(str(path))
    result = {}
    for container in tree.iter("{%s}ECUC-CONTAINER-VALUE" % NS["a"]):
        names = [c.findtext("a:SHORT-NAME", namespaces=NS) for c in container.iterancestors()]
        names = [n for n in reversed(names) if n and n != "ActiveEcuC"]
        names.append(container.findtext("a:SHORT-NAME", namespaces=NS))
        values = []
        for value in container.xpath("a:PARAMETER-VALUES/*|a:REFERENCE-VALUES/*", namespaces=NS):
            definition = value.findtext("a:DEFINITION-REF", namespaces=NS).split("/")[-1]
            text = value.findtext("a:VALUE", namespaces=NS) or value.findtext("a:VALUE-REF", namespaces=NS)
            iref = value.findtext("a:VALUE-IREF/a:TARGET-REF", namespaces=NS)
            values.append((definition, text or iref or ""))
        result["/".join(names)] = sorted(values)
    return result


def mapping(values, container):
    return dict(values[container])


def remove_block(text, anchor, start_tag, end_tag):
    i = text.index(anchor)
    j = text.index(start_tag, i)
    k = text.index(end_tag, j) + len(end_tag)
    return text[:j] + text[k:]


@pytest.mark.parametrize("mode", ["plain", "refresh"])
def test_sparse_autoc_project_verifies_without_crash(tmp_path, mode):
    summary = run_studio(make_project(tmp_path), mode)
    for round_ in summary["verify"]:
        assert round_["result"] == {"EcuC": True, "Os": True, "Rte": True}, round_["errors"]


def test_reparsed_model_matches_loaded_model(tmp_path):
    plain = make_project(tmp_path, "plain")
    refresh = make_project(tmp_path, "refresh")
    run_studio(plain, "plain", save=True)
    run_studio(refresh, "refresh", save=True)
    # Canonicalise both outputs the way any later load does, then compare contents.
    for project_dir in (plain, refresh):
        run_studio(project_dir, "plain", save=True)
    for rel in (RTE_ECUC, OS_ECUC):
        assert ecuc_values(plain / rel) == ecuc_values(refresh / rel), rel


def test_existing_mappings_unchanged_and_roundtrip_stable(tmp_path):
    project_dir = make_project(tmp_path)
    before = ecuc_values(project_dir / RTE_ECUC)
    run_studio(project_dir, "refresh", save=True)
    first = ecuc_values(project_dir / RTE_ECUC)
    run_studio(project_dir, "plain", save=True)
    second_text = (project_dir / RTE_ECUC).read_bytes()
    run_studio(project_dir, "plain", save=True)

    assert (project_dir / RTE_ECUC).read_bytes() == second_text
    for container in (
        "Rte/CanSM/CanSM_MainFunctionTimingEvent0",
        "Rte/Com/Com_MainFunction_RxTimingEvent0",
        "Rte/MinimalSystem_EcuSwComposition/MinimalSystem_Init_Ev",
        "Rte/MinimalSystem_EcuSwComposition/MinimalSystem_10ms_Ev",
        "Rte/IoHwAb_EcuSwComposition/IoHwAb_10ms_Ev",
    ):
        old, new = mapping(before, container), mapping(first, container)
        for key in [k for k in old if k != "RteBswEventRef"]:
            assert new[key] == old[key], (container, key)
        # BASIC tasks: the optional OsEvent ref stays unset (empty slot once re-mapped, absent otherwise).
        assert new.get("RteUsedOsEventRef", new.get("RteBswUsedOsEventRef")) in ("", None)
    assert mapping(first, "Rte/MinimalSystem_EcuSwComposition")["RteSoftwareComponentInstanceRef"] == (
        f"{COMPOSITION}/SysCycle"
    )


def test_bsw_instance_without_reference_values(tmp_path):
    project_dir = make_project(
        tmp_path,
        rte_edit=lambda t: remove_block(
            t, "<SHORT-NAME>CanSM</SHORT-NAME>", "<REFERENCE-VALUES>", "</REFERENCE-VALUES>"
        ),
    )
    summary = run_studio(project_dir, "refresh", save=True)
    assert summary["verify"][0]["result"]["Rte"] is True, errors(summary)
    assert mapping(ecuc_values(project_dir / RTE_ECUC), "Rte/CanSM")["RteBswModuleConfigurationRef"] == (
        "/ActiveEcuC/CanSM"
    )


def test_extended_task_mapping_records_used_os_event(tmp_path):
    def to_extended(text):
        anchor = text.index("<SHORT-NAME>OsTask_5ms</SHORT-NAME>")
        i = text.index("<VALUE>BASIC</VALUE>", anchor)
        return text[:i] + "<VALUE>EXTENDED</VALUE>" + text[i + len("<VALUE>BASIC</VALUE>") :]

    project_dir = make_project(tmp_path, os_edit=to_extended)
    run_studio(project_dir, "refresh", save=True)

    cansm = mapping(ecuc_values(project_dir / RTE_ECUC), "Rte/CanSM/CanSM_MainFunctionTimingEvent0")
    assert cansm["RteBswUsedOsEventRef"] == "/ActiveEcuC/Os/Rte_Ev_Cyclic2_OsTask_5ms_0_5ms"
    assert "Os/Rte_Ev_Cyclic2_OsTask_5ms_0_5ms" in ecuc_values(project_dir / OS_ECUC)


@pytest.mark.parametrize("mode", ["plain", "refresh"])
def test_dangling_swc_instance_ref_is_reported(tmp_path, mode):
    project_dir = make_project(
        tmp_path, rte_edit=lambda t: t.replace(f"{COMPOSITION}/ActCycle<", f"{COMPOSITION}/NoSuchProto<")
    )
    summary = run_studio(project_dir, mode)
    failures = errors(summary, "RTE000000")
    assert summary["verify"][0]["result"]["Rte"] is False
    expected_path = "/ActiveEcuC/Rte/IoHwAb_EcuSwComposition/RteSoftwareComponentInstanceRef"
    assert [e["paths"] for e in failures] == [[expected_path]]
    assert "NoSuchProto" in failures[0]["message"]


@pytest.mark.parametrize("mode", ["plain", "refresh"])
def test_wrong_swc_instance_is_reported(tmp_path, mode):
    rule = os.path.join(VCOS_ROOT, "components", "runtime", "Rte", "config_plug_in", "validation", "rules")
    if not os.path.isfile(os.path.join(rule, "RTE016004.py")):
        pytest.skip("needs vcos_components_runtime RTE016004 (RteSoftwareComponentInstanceRef type check)")
    project_dir = make_project(
        tmp_path, rte_edit=lambda t: re.sub(f"{COMPOSITION}/SysCycle<", f"{COMPOSITION}/ActCycle<", t, count=1)
    )
    summary = run_studio(project_dir, mode)
    failures = errors(summary, "RTE016004")
    assert summary["verify"][0]["result"]["Rte"] is False
    assert len(failures) == 1
    assert failures[0]["paths"] == ["/ActiveEcuC/Rte/MinimalSystem_EcuSwComposition/RteSoftwareComponentInstanceRef"]
    assert "SWC type 'IoHwAb'" in failures[0]["message"]
    assert f"{COMPOSITION}/SysCycle" in failures[0]["message"]
