"""P3 input contracts only: never starts or generates a web product."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from factory.constants import ROOT
from factory.product_contracts import (validate_bundle, validate_manifest, validate_spec, verify_source,
    require_material_ready, digest, tree_digest, SOURCE_MANIFEST_SCHEMA, CORPORATE_SITE_SCHEMA, PRODUCT_WORK_ORDER_SCHEMA)
from factory.schemas import SchemaError


def bundle():
    path=ROOT/"config/pilots/nexonova"
    return [json.loads((path/name).read_text()) for name in ("work-order.json","corporate-site.json","source-manifest.json")]


def rebind(order,spec,manifest):
    order["spec_hash"]=digest(spec)
    order["manifest_hash"]=digest(manifest)


def test_real_approved_preparation_bundle_and_asset_gate():
    order,spec,manifest=bundle()
    validate_bundle(order,spec,manifest)
    with pytest.raises(SchemaError): require_material_ready(spec,manifest)


@pytest.mark.parametrize("index",range(3))
def test_version_and_unknown_fields_rejected(index):
    values=bundle()
    values[index]["format"]="unknown"
    with pytest.raises(SchemaError):validate_bundle(*values)
    values=bundle();values[index]["unexpected"]=True
    with pytest.raises(SchemaError):validate_bundle(*values)


@pytest.mark.parametrize("path",["../escape","/etc/file","a//b","./file","C:/file", "a\\b"])
def test_source_path_escape_rejected(path):
    order,spec,manifest=bundle()
    manifest["entries"][0]["path"]=path
    manifest["tree_hash"]=tree_digest(manifest["entries"])
    rebind(order,spec,manifest)
    with pytest.raises(SchemaError):validate_bundle(order,spec,manifest)


@pytest.mark.parametrize("case",["remote","price","duplicate","empty","scope","budget","approval","generation"])
def test_invalid_or_out_of_scope_contracts_rejected(case):
    order,spec,manifest=bundle()
    if case=="remote":spec["behaviors"]["external_requests"]="enabled"
    if case=="price":spec["plans"][0]["price_clp"]=-1
    if case=="duplicate":spec["sections"].append(deepcopy(spec["sections"][0]))
    if case=="empty":spec["sections"]=[]
    if case=="scope":order["source_id"]="another-source"
    if case=="budget":order["constraints"]["max_files"]=1
    if case=="approval":spec["assets"][0]["approval"]="approved"
    if case=="generation":order["constraints"]["generation"]="authorized"
    rebind(order,spec,manifest)
    with pytest.raises(SchemaError):validate_bundle(order,spec,manifest)


def test_changed_spec_requires_new_scope_binding():
    order,spec,manifest=bundle()
    spec["brand"]["name"]="Different identity"
    with pytest.raises(SchemaError):validate_bundle(order,spec,manifest)


def test_snapshot_content_hash_is_checked():
    order,spec,manifest=bundle()
    manifest["entries"][0]["sha256"]="sha256:"+"0"*64
    rebind(order,spec,manifest)
    with pytest.raises(SchemaError):validate_bundle(order,spec,manifest)


def test_real_files_drift_extra_files_and_links(tmp_path):
    _,_,template=bundle()
    source=tmp_path/"source";source.mkdir()
    path=source/"brief.txt";path.write_text("synthetic")
    import hashlib
    manifest=deepcopy(template)
    manifest["entries"]=[{"path":"brief.txt","sha256":"sha256:"+hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":9,"action":"KEEP","reason":"fixture","approval":"approved","target":""}]
    manifest["tree_hash"]=tree_digest(manifest["entries"])
    verify_source(source,manifest)
    path.write_text("modified")
    with pytest.raises(SchemaError):verify_source(source,manifest)
    path.write_text("synthetic")
    (source/"extra").write_text("unexpected")
    with pytest.raises(SchemaError):verify_source(source,manifest)
    (source/"extra").unlink()
    (source/"link").symlink_to(path)
    with pytest.raises(SchemaError):verify_source(source,manifest)


def test_exported_schemas_match_runtime_contracts():
    for name,schema in [("product-work-order.v1",PRODUCT_WORK_ORDER_SCHEMA),("corporate-site.v0.1.0",CORPORATE_SITE_SCHEMA),("source-manifest.v1",SOURCE_MANIFEST_SCHEMA)]:
        loaded=json.loads((ROOT/"schemas"/(name+".json")).read_text())
        loaded.pop("$schema")
        assert loaded==schema


def test_synthetic_configuration_is_separate():
    original=bundle()[1]
    synthetic=json.loads((ROOT/"config/pilots/synthetic/corporate-site.json").read_text())
    validate_spec(synthetic)
    assert "nexonova" not in json.dumps({k:synthetic[k] for k in ("brand","sections","plans","services")}).lower()
    assert original["brand"]["name"]=="NexoNova"
    assert synthetic["project_id"]!=original["project_id"]


def test_p2_work_orders_remain_separate():
    from factory.execution_scope import execution_order
    p2={"work_order_id":"p2-test","objective":"synthetic","work_type":"test","scope":{"include":["."],"exclude":[]},"inputs":[],"constraints":{"no_web":True,"dry_run":True,"sandbox_required":True,"max_retries":0,"risk":"low","max_cost_usd":0,"max_latency_ms":1000},"expected_outputs":["tool-result.json"],"approval_required_for":[]}
    assert execution_order(p2)==p2
    with pytest.raises(ValueError):execution_order(bundle()[0])


def test_ready_gate_rejects_pending_source_even_if_spec_is_marked_approved():
    _,spec,manifest=bundle()
    spec["pending_decisions"]=[]
    spec["brand"]["font_approval"]="approved"
    for asset in spec["assets"]:asset["approval"]="approved"
    with pytest.raises(SchemaError):require_material_ready(spec,manifest)
