"""Opt-in REAL local Docker tests. No transport mocks or image downloads.
Run with NEXONOVA_TEST_DOCKER=1; absence is explicitly NOT_EXECUTED.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import pytest

from factory.config import FactoryConfig
from factory.executor import ToolExecutor
from factory.storage import ProjectStore, tree_hash
from factory.state_transfer import recover_run
from factory.utils import read_json, write_json

pytestmark = pytest.mark.skipif(os.environ.get('NEXONOVA_TEST_DOCKER') != '1', reason='NOT_EXECUTED: opt in to real local Docker using NEXONOVA_TEST_DOCKER=1')
EVIDENCE = []


def docker(*args):
    with tempfile.TemporaryDirectory(prefix='nexonova-inspect-') as home:
        return subprocess.run(['docker','--host','unix:///var/run/docker.sock',*args],
            env={'PATH':'/usr/bin:/bin','HOME':home,'DOCKER_CONFIG':home}, capture_output=True, text=True, timeout=20)


@pytest.fixture
def case(tmp_path):
    store=ProjectStore(tmp_path/'private','client-a','site')
    store.initialize()
    other=ProjectStore(store.root,'client-b','site')
    other.initialize()
    for directory in (other.workspace, other.path/'runs', other.path/'approvals'):
        (directory/'sentinel.txt').write_text('synthetic-client-b')
    client_dirs=set(Path(tempfile.gettempdir()).glob("nexonova-docker-client-*"))
    yield store,other
    # Only names created by this fixture; never prune unrelated resources.
    for run in (store.path/'runs').iterdir():
        checkpoint=run/'checkpoint.json'
        if checkpoint.exists():
            name=read_json(checkpoint)['container']
            existing=docker('ps','-aq','--filter','name=^/'+name+'$')
            assert existing.returncode == 0, existing.stderr
            if existing.stdout.strip():
                cleanup=docker('rm','-f',name)
                assert cleanup.returncode == 0, cleanup.stderr
                pytest.fail('Scenario left a container; fixture removed '+name)
    assert set(Path(tempfile.gettempdir()).glob('nexonova-docker-client-*')) == client_dirs, 'Leaked Docker client directory'


def config(timeout=20):
    value=FactoryConfig.load(Path('config/factory.json'))
    assert value.python_image is not None, 'BLOCKED: pinned image missing'
    assert docker('image','inspect',value.python_image).returncode == 0, 'BLOCKED: local image unavailable'
    return FactoryConfig(python_image=value.python_image,timeout_seconds=timeout)


def source(store, body):
    tests=store.workspace/'tests'
    tests.mkdir()
    (tests/'test_probe.py').write_text(body)


def finish(store, result, scenario):
    run=store.path/'runs'/result['run_id']
    assert read_json(run/'state.json')['lifecycle'] == 'finished'
    assert not list((store.path/'temporary').iterdir())
    checkpoint=read_json(run/'checkpoint.json')
    name=checkpoint['container']
    existing=docker('ps','-aq','--filter','name=^/'+name+'$')
    assert existing.returncode == 0 and not existing.stdout.strip(), existing.stderr
    EVIDENCE.append({'scenario':scenario,'container':name,'status':result['status'],
                     'reason':result['reason'],'exit_code':result['exit_code'],'cleanup':'absent'})


def run(store, timeout=20):
    executor=ToolExecutor(store,config(timeout))
    approval=store.approve_tool('python.unittest',actor='local-p2-test',policy_hash=executor.policy_hash)
    return executor.run('python.unittest',approval_id=approval)


def test_real_isolation_and_success(case, monkeypatch):
    store,other=case
    monkeypatch.setenv('NEXONOVA_PRIVATE_SYNTHETIC','not-for-container')
    before=tree_hash(other.path)
    body='''import unittest,os,socket,resource,subprocess
from pathlib import Path
class Probe(unittest.TestCase):
 def test_controls(self):
  self.assertEqual(os.getcwd(),'/workspace')
  self.assertEqual(os.getuid(),UID)
  self.assertEqual(os.getgid(),GID)
  self.assertNotIn('NEXONOVA_PRIVATE_SYNTHETIC',os.environ)
  self.assertLessEqual(set(os.environ),{'PATH','LANG','GPG_KEY','PYTHON_VERSION','PYTHON_SHA256','HOME','HOSTNAME','PYTHONDONTWRITEBYTECODE'})
  self.assertEqual(os.environ['HOME'],'/tmp')
  self.assertEqual(os.environ['PYTHONDONTWRITEBYTECODE'],'1')
  for path in DENIED:
   with self.assertRaises(OSError): Path(path).write_text('forbidden')
  for path in PRIVATE:
   with self.assertRaises(OSError): Path(path).read_text()
   with self.assertRaises(OSError): Path(path).write_text('forbidden')
  Path('/tmp/authorized').write_text('synthetic')
  self.assertEqual(Path('/tmp/authorized').read_text(),'synthetic')
  Path('/tmp/program').write_text('#!/bin/sh\\nexit 0\\n')
  os.chmod('/tmp/program',0o700)
  with self.assertRaises(PermissionError): subprocess.run(['/tmp/program'],check=True)
  with open('/tmp/limited','wb') as stream:
   with self.assertRaises(OSError):
    for _ in range(11): stream.write(b'x'*1048576)
  self.assertLessEqual(Path('/tmp/limited').stat().st_size,10485760)
  self.assertEqual(set(os.listdir('/sys/class/net')),{'lo'})
  with socket.socket() as sock:
   sock.settimeout(0.2)
   with self.assertRaises(OSError): sock.connect(('192.0.2.1',9))
  self.assertEqual(Path('/sys/fs/cgroup/memory.max').read_text().strip(),'536870912')
  self.assertEqual(Path('/sys/fs/cgroup/pids.max').read_text().strip(),'64')
  quota,period=map(int,Path('/sys/fs/cgroup/cpu.max').read_text().split())
  self.assertEqual(quota,period)
  self.assertEqual(resource.getrlimit(resource.RLIMIT_FSIZE),(10485760,10485760))
  status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
  self.assertEqual(int(status['CapEff'].strip(),16),0)
  self.assertEqual(status['NoNewPrivs'].strip(),'1')
  self.assertEqual(status['Seccomp'].strip(),'2')
  print('docker-controls-verified',flush=True)
'''
    private=[str(d/'sentinel.txt') for d in (other.workspace,other.path/'runs',other.path/'approvals')]
    denied=['/workspace/forbidden','/workspace/tests/forbidden','/workspace/../forbidden','/etc/forbidden','/root/forbidden',str(store.path/'runs'/'forbidden')]
    body=body.replace('UID',str(os.getuid())).replace('GID',str(os.getgid())).replace('DENIED',repr(denied)).replace('for path in PRIVATE:', 'for path in '+repr(private)+':')
    source(store,body)
    result=run(store)
    assert result['status']=='complete',result
    assert result['tests_run']==1 and result['exit_code']==0
    assert 'docker-controls-verified' in result['output']
    assert tree_hash(other.path)==before
    finish(store,result,'isolation-success')


@pytest.mark.parametrize('scenario', ['failure','timeout','output_limit'])
def test_real_outcomes(case,scenario):
    store,_=case
    action={'failure':'self.fail("synthetic failure")','timeout':'time.sleep(30)', 'output_limit':'print("x"*100000,flush=True)'}[scenario]
    source(store,'import unittest,time\nclass Probe(unittest.TestCase):\n def test_case(self):\n  '+action+'\n')
    result=run(store,3 if scenario=='timeout' else 20)
    assert result['status']=='error',result
    if scenario=='failure': assert result['exit_code']==1 and 'synthetic failure' in result['output']
    else: assert scenario in result['reason']
    finish(store,result,scenario)


def launch_waiting(store):
    # Construct the synthetic secret at runtime so source secret rejection stays active.
    source(store,"import unittest,time\nclass Probe(unittest.TestCase):\n def test_wait(self):\n  print('partial-public',flush=True)\n  print('pass'+'word='+chr(34)+'synthetic private tail'+chr(34),flush=True)\n  time.sleep(40)\n")
    conf=config(60)
    path=store.path/'test-config.json'
    write_json(path,conf.__dict__)
    executor=ToolExecutor(store,conf)
    approval=store.approve_tool('python.unittest',actor='local-p2-test',policy_hash=executor.policy_hash)
    command=[sys.executable,'-B','-m','factory.cli','run-tool','--root',str(store.root),'--client','client-a','--project-id','site','--tool','python.unittest','--config',str(path),'--approval',approval]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        for run_dir in (store.path/'runs').iterdir():
            checkpoint=run_dir/'checkpoint.json'
            if checkpoint.exists() and 'partial-public' in read_json(checkpoint)['result']['output']:
                return process,run_dir
        if process.poll() is not None:
            pytest.fail('Container did not reach checkpoint: '+repr(process.communicate()))
        time.sleep(.05)
    process.kill();process.communicate()
    pytest.fail('Waiting for real container timed out')


@pytest.mark.parametrize('scenario',['sigint','crash'])
def test_real_interruption_recovery(case,scenario):
    store,_=case
    process,run_dir=launch_waiting(store)
    name=read_json(run_dir/'checkpoint.json')['container']
    inspected=docker('inspect',name)
    assert inspected.returncode==0
    metadata=json.loads(inspected.stdout)[0]
    assert metadata['State']['Running'] is True
    host=metadata['HostConfig']
    assert host['NetworkMode']=='none' and host['ReadonlyRootfs'] is True
    assert host['Memory']==536870912 and host['PidsLimit']==64 and host['NanoCpus']==1000000000
    assert host['Privileged'] is False and not host['PortBindings']
    assert host['CapDrop']==['ALL']
    assert len([m for m in metadata['Mounts'] if m['Type']=='bind'])==1
    assert all(not m['RW'] for m in metadata['Mounts'] if m['Type']=='bind')
    children=Path(f'/proc/{process.pid}/task/{process.pid}/children').read_text().split()
    assert len(children)==1
    client_pid=int(children[0])
    client_env=Path(f'/proc/{client_pid}/environ').read_bytes().split(b'\0')
    client_home=Path(next(item.split(b'=',1)[1].decode() for item in client_env if item.startswith(b'DOCKER_CONFIG=')))
    assert client_home.parent==Path(tempfile.gettempdir()) and client_home.name.startswith('nexonova-docker-client-')
    process.send_signal(signal.SIGINT if scenario=='sigint' else signal.SIGKILL)
    process.communicate(timeout=20)
    if scenario=='sigint':
        assert process.returncode==130
        result=read_json(run_dir/'tool-result.json')
        assert result['termination']=='interrupted' and result['signal']=='SIGINT'
        assert 'partial-public' in result['output'] and 'private tail' not in result['output']
        assert not client_home.exists()
        finish(store,result,scenario)
    else:
        assert process.returncode==-signal.SIGKILL
        assert docker('inspect',name).returncode==0 # orphan is explicitly expected after crash
        recover_run(store,run_dir.name)
        result=read_json(run_dir/'tool-result.json')
        assert result['cleanup']=='operator_inspection_required' and result['executed'] is None
        assert len(list((store.path/'runs').iterdir()))==1
        current=json.loads(docker('inspect',name).stdout)[0]
        assert current['Id']==metadata['Id'] and current['State']['StartedAt']==metadata['State']['StartedAt']
        assert docker('rm','-f',name).returncode==0
        # Only this test's staging: crash cannot run TemporaryDirectory.__exit__.
        import shutil
        staging=store.path/read_json(run_dir/'checkpoint.json')['staging']
        shutil.rmtree(staging)
        shutil.rmtree(client_home)
        finish(store,result,scenario+'-manual-cleanup')
    deadline=time.monotonic()+5
    while Path(f'/proc/{client_pid}').exists() and time.monotonic()<deadline:
        time.sleep(.05)
    assert not Path(f'/proc/{client_pid}').exists(), 'Docker CLI child still present'
    assert not Path('/proc/'+str(metadata['State']['Pid'])).exists(), 'Container process still present'


@pytest.fixture(scope='module',autouse=True)
def record_evidence():
    yield
    if EVIDENCE:
        path=Path('docs/migration/P2_DOCKER_RESULTS.json')
        previous=json.loads(path.read_text()) if path.exists() else []
        path.write_text(json.dumps(previous+EVIDENCE,indent=2)+'\n')


@pytest.mark.parametrize('kind',['symlink','hardlink','traversal','absolute'])
def test_paths_rejected_before_container(case,kind):
    store,other=case
    source(store,'import unittest\nclass Probe(unittest.TestCase):\n def test_ok(self): pass\n')
    executor=ToolExecutor(store,config())
    approval=store.approve_tool('python.unittest',actor='local-p2-test',policy_hash=executor.policy_hash)
    before=docker('ps','-aq','--filter','name=nexonova-test-').stdout
    if kind=='symlink':
        (store.workspace/'escape').symlink_to(other.workspace/'sentinel.txt')
    elif kind=='hardlink':
        os.link(other.workspace/'sentinel.txt',store.workspace/'escape')
    else:
        from factory.storage import StorageError
        path='../forbidden' if kind=='traversal' else str(other.workspace/'sentinel.txt')
        with pytest.raises(StorageError): store.write(store.path/'runs',path,{'synthetic':'forbidden'})
    if kind in {'symlink','hardlink'}:
        result=executor.run('python.unittest',approval_id=approval)
        assert result['status']=='error' and result['executed'] is False
        assert read_json(store.path/'approvals'/(approval+'.json'))['used'] is False
        assert not (store.path/'runs'/result['run_id']/'checkpoint.json').exists()
    assert (other.workspace/'sentinel.txt').read_text()=='synthetic-client-b'
    assert docker('ps','-aq','--filter','name=nexonova-test-').stdout==before
