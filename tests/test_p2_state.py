"""P2 restrictions, portable references and recoverable checkpoints."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from factory.config import FactoryConfig
from factory.executor import ToolExecutor
from factory.storage import StorageError, tree_hash
from factory.state_transfer import import_reference, resolve_reference, recover_run
from factory.utils import read_json
from test_p2_validation import store, host_adapter


def order():
    return {'work_order_id': 'WO-test', 'objective': 'local validation', 'work_type': 'test',
            'scope': {'include': ['.'], 'exclude': []}, 'inputs': [],
            'constraints': {'no_web': True, 'dry_run': False, 'sandbox_required': True,
                            'max_retries': 0, 'risk': 'low', 'max_cost_usd': 0, 'max_latency_ms': 1000},
            'expected_outputs': ['tool-result.json'], 'approval_required_for': []}


@pytest.mark.parametrize('variant', ['scope', 'excluded', 'input', 'latency', 'dry_run'])
def test_work_order_restricts_before_process(store, monkeypatch, variant):
    value = order()
    if variant == 'scope': value['scope']['include'] = ['tests']
    if variant == 'excluded': value['scope']['exclude'] = ['input.txt']
    if variant == 'input': value['inputs'] = [{'source_id':'synthetic','type':'brief','authorized':False,'trust':'untrusted'}]
    if variant == 'latency': value['constraints']['max_latency_ms'] = 0
    if variant == 'dry_run': value['constraints']['dry_run'] = True
    executor = ToolExecutor(store, FactoryConfig(python_image='python@sha256:'+'a'*64), work_order=value)
    approval = store.approve_tool('python.unittest', actor='test', policy_hash=executor.policy_hash)
    monkeypatch.setattr('factory.executor.shutil.which', lambda _: '/usr/bin/true')
    def forbidden(*args, **kwargs): pytest.fail('WorkOrder restriction allowed a process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = executor.run('python.unittest', approval_id=approval)
    assert result['executed'] is False
    assert result['status'] == ('needs_user_input' if variant == 'dry_run' else 'error')
    assert read_json(store.path/'approvals'/(approval+'.json'))['used'] is False


def test_work_order_change_invalidates_approval_and_cannot_enable_network(store, monkeypatch):
    value = order()
    config = FactoryConfig(python_image='python@sha256:'+'a'*64)
    original = ToolExecutor(store, config, work_order=value)
    approval = store.approve_tool('python.unittest', actor='test', policy_hash=original.policy_hash)
    value['constraints']['no_web'] = False
    value['constraints']['sandbox_required'] = False
    changed = ToolExecutor(store, config, work_order=value)
    monkeypatch.setattr('factory.executor.shutil.which', lambda _: '/usr/bin/true')
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Stale approval executed'))
    assert changed.run('python.unittest', approval_id=approval)['status'] == 'error'
    snapshot = store.path/'temporary'/'snapshot'
    snapshot.mkdir()
    command = changed.command('/usr/bin/docker', 'python.unittest', 'test', snapshot)
    assert '--network=none' in command and '--read-only' in command
    assert original.work_order['constraints']['no_web'] is True


def test_reference_portable_preserves_bytes_and_does_not_import_claims(store, tmp_path):
    legacy = tmp_path/'legacy'
    legacy.mkdir()
    (legacy/'state.json').write_text('{"status":"complete","old_path":"/old/machine/run"}')
    before = tree_hash(legacy)
    reference = import_reference(store, legacy)
    manifest = read_json(store.path/reference)
    assert manifest['format'] == 'nexonova.legacy-reference.v1'
    assert manifest['interpretation'] == 'unverified_legacy_claims'
    assert '/old/machine' not in json.dumps(manifest) and str(legacy) not in json.dumps(manifest)
    relocated = tmp_path/'relocated'
    shutil.copytree(legacy, relocated)
    assert resolve_reference(store, reference, relocated) == [relocated/'state.json']
    assert tree_hash(legacy) == before
    (relocated/'state.json').write_text('changed')
    with pytest.raises(StorageError): resolve_reference(store, reference, relocated)


def test_reference_rejects_links_credentials_and_unknown_version(store, tmp_path):
    source = tmp_path/'legacy'
    source.mkdir()
    (source/'.env').write_text('synthetic only')
    with pytest.raises(StorageError): import_reference(store, source)
    (source/'.env').unlink()
    (source/'file').symlink_to(tmp_path/'outside')
    with pytest.raises(StorageError): import_reference(store, source)
    (source/'file').unlink()
    reference = import_reference(store, source)
    path = store.path/reference
    value = read_json(path)
    value['format'] = 'unknown'
    path.write_text(json.dumps(value))
    with pytest.raises(StorageError): resolve_reference(store, reference, source)


def test_recovery_after_actual_abrupt_exit_is_idempotent(store):
    driver = '''from pathlib import Path
import os,sys
from factory.storage import ProjectStore
s=ProjectStore(Path(sys.argv[1]),'client-a','site')
with s.locked():
 r=s.new_run()
 s.write(r,'checkpoint.json',{'format':'nexonova.checkpoint.v1','phase':'approved','result':{'output':'public partial evidence'}})
 os._exit(17)
'''
    assert subprocess.run([sys.executable, '-B', '-c', driver, str(store.root)], timeout=10).returncode == 17
    run = next((store.path/'runs').iterdir())
    recover_run(store, run.name)
    result = read_json(run/'tool-result.json')
    assert result['termination'] == 'interrupted' and result['executed'] is None
    assert result['cleanup'] == 'operator_inspection_required'
    assert result['output'] == 'public partial evidence'
    before = tree_hash(run)
    recover_run(store, run.name)
    assert tree_hash(run) == before
    assert read_json(run/'state.json')['lifecycle'] == 'finished'


def test_recovery_completes_interrupted_state_commit_without_replaying(store, monkeypatch):
    executor, approval = host_adapter(store, monkeypatch, "print('public marker')")
    write = store.write
    def fail_terminal_state(directory, name, value):
        if name == 'state.json' and value.get('lifecycle') == 'finished':
            raise OSError('synthetic interrupted commit')
        return write(directory, name, value)
    monkeypatch.setattr(store, 'write', fail_terminal_state)
    with pytest.raises(OSError): executor.run('python.unittest', approval_id=approval)
    run = next((store.path/'runs').iterdir())
    checkpoint = read_json(run/'checkpoint.json')
    assert checkpoint['phase'] == 'executing' and 'public marker' in checkpoint['result']['output']
    terminal = (run/'tool-result.json').read_bytes()
    monkeypatch.setattr(store, 'write', write)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Recovery replayed a process'))
    recover_run(store, run.name)
    assert (run/'tool-result.json').read_bytes() == terminal
    assert read_json(run/'state.json')['lifecycle'] == 'finished'


def test_recovery_obeys_writer_lock_and_run_boundary(store):
    with store.locked():
        run = store.new_run()
        with pytest.raises(StorageError): recover_run(store, run.name)
    with pytest.raises(StorageError): recover_run(store, '../other')
