"""Versioned legacy references and explicit recovery; never replay tool effects."""
import hashlib
import os
import re
import uuid
from pathlib import Path

from .storage import StorageError, safe_path, tree_hash
from .utils import read_json, utc_now


def import_reference(store, source: Path):
    """Store hashes/relative names only. Caller supplies source again to resolve."""
    source = source.absolute()
    if not source.is_dir() or any(p.is_symlink() for p in (source, *source.parents)):
        raise StorageError('Invalid legacy source root')
    if source.is_relative_to(store.root) or store.root.is_relative_to(source):
        raise StorageError('Legacy source and private state must not overlap')
    digest = tree_hash(source)  # budgets, credential filenames, links, special files
    records = []
    for current, directories, files in os.walk(source, followlinks=False):
        directories[:] = [d for d in directories if d not in {'.git', 'node_modules', '.next', '__pycache__', '.pytest_cache'}]
        for name in files:
            if name == '.git':
                continue
            relative = (Path(current) / name).relative_to(source).as_posix()
            path = safe_path(source, relative)
            records.append({'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    if tree_hash(source) != digest:
        raise StorageError('Legacy source changed during reference import')
    manifest = {'format': 'nexonova.legacy-reference.v1', 'source_hash': digest,
                'files': sorted(records, key=lambda item: item['path']),
                'interpretation': 'unverified_legacy_claims', 'created_at': utc_now()}
    with store.locked():
        directory = safe_path(store.path, 'imports')
        directory.mkdir(mode=0o700, exist_ok=True)
        name = 'REF-' + uuid.uuid4().hex + '.json'
        store.write(directory, name, manifest)
    return 'imports/' + name


def resolve_reference(store, reference: str, source: Path):
    if not re.fullmatch(r'imports/REF-[a-f0-9]{32}\.json', reference):
        raise StorageError('Invalid legacy reference')
    manifest = read_json(safe_path(store.path, reference))
    if manifest.get('format') != 'nexonova.legacy-reference.v1' or tree_hash(source) != manifest['source_hash']:
        raise StorageError('Legacy source or reference version mismatch')
    paths = []
    for item in manifest['files']:
        path = safe_path(source, item['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise StorageError('Legacy file hash mismatch')
        paths.append(path)
    return paths


def recover_run(store, run_id):
    """Close an abandoned run under writer lock; preserve evidence, never retry."""
    from .executor import redact
    if not re.fullmatch(r'RUN-[a-f0-9]{32}', run_id):
        raise StorageError('Invalid run identifier')
    with store.locked():
        directory = safe_path(store.path, 'runs/' + run_id)
        state = read_json(safe_path(directory, 'state.json'))
        if state.get('lifecycle') == 'finished':
            return state  # Idempotent; no alteration of already closed evidence.
        if state.get('lifecycle') != 'running':
            raise StorageError('Unsupported run lifecycle')
        terminal = safe_path(directory, 'tool-result.json')
        checkpoint_path = safe_path(directory, 'checkpoint.json')
        checkpoint = read_json(checkpoint_path) if checkpoint_path.exists() else {}
        if checkpoint and checkpoint.get('format') != 'nexonova.checkpoint.v1':
            raise StorageError('Unsupported checkpoint version')
        if terminal.exists():
            result = read_json(terminal)
            if result.get('run_id') != run_id or result.get('status') not in {'complete', 'error', 'not_answerable', 'needs_user_input'} or not result.get('finished_at'):
                raise StorageError('Invalid terminal result; manual review required')
        else:
            result = dict(checkpoint.get('result', {}))
            result.update(format='nexonova.tool-result.v1', run_id=run_id, status='error',
                          termination='interrupted', reason='recovered_abandoned_run', executed=None,
                          exit_code=None, finished_at=utc_now(), human_review='pending',
                          output=redact(result.get('output', '')))
            # A crash cannot certify container cleanup or process termination.
            result['cleanup'] = 'operator_inspection_required'
            for key in ('container', 'staging'):
                if key in checkpoint:
                    result[key] = checkpoint[key]
            store.write(directory, 'tool-result.json', result)
        state = {'format': 'nexonova.tool-run.v1', 'lifecycle': 'finished',
                 'status': result['status'], 'tool_result': 'tool-result.json', 'recovered_at': utc_now()}
        store.write(directory, 'state.json', state)
        return state
