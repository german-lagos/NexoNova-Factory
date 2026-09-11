"""WorkOrder restrictions for the sole read-only P2 adapter."""
import copy
import math

from .schemas import WORK_ORDER_SCHEMA, validate_strict
from .storage import StorageError, safe_path
from .utils import sha256_file


def execution_order(order):
    if order is None:
        return None  # Direct operator API; global policy and approval still mandatory.
    value = copy.deepcopy(order)
    validate_strict(WORK_ORDER_SCHEMA, value)
    if value['work_type'] != 'test':
        raise StorageError('Only test WorkOrders are supported by this adapter')
    if any(name != 'tool-result.json' for name in value['expected_outputs']):
        raise StorageError('Unsupported WorkOrder output')
    for key in ('max_cost_usd', 'max_latency_ms'):
        if not math.isfinite(value['constraints'][key]):
            raise StorageError('Non-finite WorkOrder budget')
    return value


def check_scope(store, order):
    if order is None:
        return
    scope = order['scope']
    for relative in scope['include'] + scope['exclude']:
        if relative != '.':
            safe_path(store.workspace, relative)
    def matches(relative, entries):
        return any(item == '.' or relative == item or relative.startswith(item + '/') for item in entries)
    # Refuse a partial mount instead of silently broadening the approved scope.
    for path in store.workspace.rglob('*'):
        relative = path.relative_to(store.workspace).as_posix()
        safe_path(store.workspace, relative)
        if path.is_file() and (not matches(relative, scope['include']) or matches(relative, scope['exclude'])):
            raise StorageError('Workspace contains files outside WorkOrder scope')
    for item in order['inputs']:
        if not item['authorized']:
            raise StorageError('Unauthorized WorkOrder input')
        if 'path' in item:
            path = store.workspace if item['path'] == '.' else safe_path(store.workspace, item['path'])
            if not path.exists():
                raise StorageError('Missing WorkOrder input')
            if 'hash' in item and (not path.is_file() or sha256_file(path) != item['hash']):
                raise StorageError('WorkOrder input hash mismatch')
