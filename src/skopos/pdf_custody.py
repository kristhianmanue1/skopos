"""Custodia binaria de PDF por referencia externa, separada de source-envelope."""

from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from pymongo import ReadPreference
from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern


SCHEMA = 'skopos/pdf-custody-lab/v0.1'
CONTRACT = 'expertogobernanza/skopos-source'
VERSION = 'v0.1'
PROFILE = 'skopos/pdf-custody/v0.1'
HEX = re.compile(r'[0-9a-f]{64}\Z')
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z')
MAX_REQUEST_BYTES = 64 * 1024
MAX_POLICY_BYTES = 16 * 1024
MAX_PROVENANCE_BYTES = 256 * 1024


class CustodyError(ValueError):
    def __init__(self, code, stage='validation'):
        self.code = code
        self.stage = stage
        super().__init__(code)


def _digest(value):
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise CustodyError('invalid_digest')
    return value


def _identifier(value):
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        raise CustodyError('invalid_identity')
    return value


def _parts(reference):
    if not isinstance(reference, str) or len(reference) > 1024 or '\\' in reference:
        raise CustodyError('path_outside_root')
    parts = reference.split('/')
    if (reference.startswith('/') or any(part in ('', '.', '..') for part in parts)
            or any('\x00' in part for part in parts)):
        raise CustodyError('path_outside_root')
    return parts


def _root_fd(root):
    if not isinstance(root, str) or not os.path.isabs(root):
        raise CustodyError('policy_unavailable')
    try:
        return os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        raise CustodyError('policy_unavailable') from None


def _parent_fd(root, reference):
    parts = _parts(reference)
    fd = _root_fd(root)
    try:
        for part in parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=fd)
            os.close(fd)
            fd = following
        return fd, parts[-1]
    except OSError:
        os.close(fd)
        raise CustodyError('path_outside_root') from None


def _read_under(root, reference, maximum, *, stage='validation'):
    parent, name = _parent_fd(root, reference)
    try:
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                                 dir_fd=parent)
        except PermissionError:
            raise CustodyError('permission_denied', stage) from None
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise CustodyError('path_outside_root', stage) from None
            raise CustodyError('bytes_unavailable', stage) from None
        with os.fdopen(descriptor, 'rb') as source:
            details = os.fstat(source.fileno())
            if not stat.S_ISREG(details.st_mode):
                raise CustodyError('invalid_file', stage)
            if details.st_size < 1 or details.st_size > maximum:
                raise CustodyError('limit_exceeded', stage)
            raw = source.read(details.st_size + 1)
            if len(raw) != details.st_size:
                raise CustodyError('bytes_unavailable', stage)
            return raw
    finally:
        os.close(parent)


def _load_json(raw, maximum):
    if len(raw) > maximum:
        raise CustodyError('limit_exceeded')
    try:
        data = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError):
        raise CustodyError('invalid_json') from None
    if not isinstance(data, dict):
        raise CustodyError('invalid_json')
    return data


def _policy_digest(policy):
    raw = json.dumps(policy, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def load_policy(path):
    """El host entrega la política; la solicitud nunca puede crearla."""
    path = Path(path)
    if not path.is_absolute():
        raise CustodyError('policy_unavailable')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise CustodyError('policy_unavailable')
            raw = source.read(MAX_POLICY_BYTES + 1)
    except OSError:
        raise CustodyError('policy_unavailable') from None
    policy = _load_json(raw, MAX_POLICY_BYTES)
    required = ('schema', 'project_id', 'policy_id', 'policy_version', 'owner',
                'classification', 'requests_root', 'input_root', 'source_root', 'delivery_root',
                'retention_until', 'retention_basis', 'max_bytes', 'seal_policy',
                'seal_profile_id', 'recovery_requirement')
    if any(key not in policy for key in required) or policy['schema'] != 'skopos/pdf-custody-policy/v0.1':
        raise CustodyError('policy_unavailable')
    for field in ('requests_root', 'input_root', 'source_root', 'delivery_root'):
        fd = _root_fd(policy[field])
        os.close(fd)
    for field in ('project_id', 'owner'):
        _identifier(policy[field])
    for field in ('policy_id', 'policy_version', 'classification', 'retention_basis',
                  'seal_profile_id'):
        if not isinstance(policy[field], str) or not policy[field] or len(policy[field]) > 256:
            raise CustodyError('policy_unavailable')
    if policy['seal_policy'] != 'not_required':
        raise CustodyError('policy_unavailable')
    if policy['recovery_requirement'] != 'while_reference_available':
        raise CustodyError('policy_unavailable')
    if type(policy['max_bytes']) is not int or not 0 < policy['max_bytes'] <= 32 * 1024 * 1024:
        raise CustodyError('policy_unavailable')
    try:
        expiry = datetime.fromisoformat(policy['retention_until'].replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        raise CustodyError('retention_policy_missing') from None
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise CustodyError('retention_policy_missing')
    return policy


def read_request(policy, envelope):
    """Ata sobre externo, bytes exactos de solicitud y su identidad."""
    for key in ('request_file_ref', 'request_sha256', 'request_id', 'contract_id', 'contract_version'):
        if key not in envelope:
            raise CustodyError('invalid_request')
    raw = _read_under(policy['requests_root'], envelope['request_file_ref'], MAX_REQUEST_BYTES)
    if hashlib.sha256(raw).hexdigest() != _digest(envelope['request_sha256']):
        raise CustodyError('hash_mismatch')
    request = _load_json(raw, MAX_REQUEST_BYTES)
    for key in ('request_id', 'contract_id', 'contract_version'):
        if request.get(key) != envelope[key]:
            raise CustodyError('request_mismatch')
    if request.get('contract_id') != CONTRACT or request.get('contract_version') != VERSION:
        raise CustodyError('unsupported_contract')
    _identifier(request['request_id'])
    return request


def _identity(request, policy):
    if request.get('project_id') != policy['project_id']:
        raise CustodyError('policy_mismatch')
    project = _identifier(request['project_id'])
    material = _identifier(request.get('material_id'))
    revision = request.get('source_revision')
    if type(revision) is not int or not 1 <= revision < 2**63:
        raise CustodyError('invalid_revision')
    return project, material, revision


def _policy_current(policy):
    try:
        expiry = datetime.fromisoformat(policy['retention_until'].replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        raise CustodyError('retention_policy_missing') from None
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise CustodyError('retention_policy_missing')


def _admission_data(request, policy):
    project, material, revision = _identity(request, policy)
    _policy_current(policy)
    if request.get('operation') != 'admit_original' or request.get('scope') != 'single_object':
        raise CustodyError('unsupported_operation')
    if (request.get('custody_mode') != 'verified_external_reference'
            or request.get('custody_policy_id') != policy['policy_id']
            or request.get('custody_policy_version') != policy['policy_version']
            or request.get('classification') != policy['classification']
            or request.get('seal_profile_id') != policy['seal_profile_id']
            or request.get('recovery_requirement') != policy['recovery_requirement']):
        raise CustodyError('policy_mismatch')
    if request.get('media_type_declared') != 'application/pdf':
        raise CustodyError('unsupported_format')
    limits = request.get('limits')
    if (not isinstance(limits, dict) or limits.get('allow_network') is not False
            or limits.get('allow_ocr') is not False
            or type(limits.get('max_bytes')) is not int
            or limits['max_bytes'] < 1):
        raise CustodyError('invalid_limits')
    if 'max_pages' in limits:
        raise CustodyError('unsupported_limit')
    maximum = min(policy['max_bytes'], limits['max_bytes'])
    delivery = request.get('source_delivery')
    if not isinstance(delivery, dict):
        raise CustodyError('invalid_request')
    mode = delivery.get('mode')
    if mode == 'authorized_reference':
        reference = delivery.get('file_ref')
    elif mode == 'provided_file':
        reference = delivery.get('persistent_ref')
        if not reference:
            raise CustodyError('persistent_reference_missing')
        lateral = _read_under(policy['input_root'], delivery.get('file_ref'), maximum,
                              stage='admission')
    else:
        raise CustodyError('unsupported_delivery')
    raw = _read_under(policy['source_root'], reference, maximum, stage='admission')
    observed = hashlib.sha256(raw).hexdigest()
    if observed != _digest(request.get('expected_source_sha256')):
        raise CustodyError('hash_mismatch', 'admission')
    if mode == 'provided_file' and lateral != raw:
        raise CustodyError('hash_mismatch', 'admission')
    if not raw.startswith(b'%PDF-'):
        raise CustodyError('unsupported_format')
    provenance = request.get('provenance')
    if provenance is not None:
        if (not isinstance(provenance, dict)
                or provenance.get('asserted_by') != policy['owner']
                or provenance.get('claim_status') != 'consumer_declared'):
            raise CustodyError('provenance_incomplete')
        record = _read_under(policy['source_root'], provenance.get('record_ref'),
                             MAX_PROVENANCE_BYTES, stage='admission')
        if hashlib.sha256(record).hexdigest() != _digest(provenance.get('record_sha256')):
            raise CustodyError('hash_mismatch', 'admission')
    return {
        '_id': ':'.join((project, material, str(revision))),
        'schema': SCHEMA, 'project_id': project, 'material_id': material,
        'source_revision': revision, 'source_sha256': observed,
        'byte_length': len(raw), 'source_ref': reference,
        'policy_id': policy['policy_id'], 'policy_version': policy['policy_version'],
        'policy_sha256': _policy_digest(policy),
        'retention_basis': policy['retention_basis'],
        'retention_until': policy['retention_until'],
        'seal_policy': policy['seal_policy'],
        'seal_profile_id': policy['seal_profile_id'],
        'classification': policy['classification'], 'owner': policy['owner'],
        'provenance': provenance, 'request_id': request['request_id'],
        'request_sha256': request['_request_sha256'],
        'previous_source_sha256': request.get('expected_previous_sha256'),
        'admitted_at': datetime.now(timezone.utc).isoformat()}


def _receipt(document, status):
    return {'receipt_id': document['_id'] + ':' + document['request_sha256'][:16],
            'admission_status': status, 'project_id': document['project_id'],
            'material_id': document['material_id'],
            'source_revision': document['source_revision'],
            'source_sha256': document['source_sha256'],
            'request_id': document['request_id'],
            'request_sha256': document['request_sha256'],
            'admitted_at': document['admitted_at']}


def _record_digest(document):
    raw = json.dumps({key: value for key, value in document.items()
                      if key != 'record_sha256'}, sort_keys=True,
                     ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def _verified_document(document, key):
    try:
        if (document['_id'] != key or document['schema'] != SCHEMA
                or _record_digest(document) != document['record_sha256']):
            raise CustodyError('store_integrity_failed', 'retrieval')
        _digest(document['source_sha256'])
        _digest(document['request_sha256'])
        _parts(document['source_ref'])
    except (KeyError, TypeError, ValueError):
        raise CustodyError('store_integrity_failed', 'retrieval') from None
    return document


def _deliver(root, reference, raw):
    """Publica el nombre final sólo después de escribir y verificar el temporal."""
    parent, name = _parent_fd(root, reference)
    temporary = '.skopos-' + secrets.token_hex(16)
    created = False
    published = False
    try:
        try:
            descriptor = os.open(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
            created = True
            with os.fdopen(descriptor, 'w+b') as target:
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
                target.seek(0)
                if target.read(len(raw) + 1) != raw:
                    raise CustodyError('output_unavailable', 'delivery')
            os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent,
                    follow_symlinks=False)
            published = True
            os.fsync(parent)
        except (OSError, CustodyError):
            if published:
                try:
                    os.unlink(name, dir_fd=parent)
                except OSError:
                    pass
            raise CustodyError('output_unavailable', 'delivery') from None
    finally:
        if created:
            try:
                os.unlink(temporary, dir_fd=parent)
            except OSError:
                pass
        os.close(parent)


class PdfCustodyStore:
    """Solo cliente local confiable; project_id no es un control de acceso."""

    def __init__(self, database, policy):
        self.database = database
        self.policy = policy
        self.revisions = database.get_collection(
            'pdf_custody_revisions_v1', read_concern=ReadConcern('majority'),
            read_preference=ReadPreference.PRIMARY)
        self.heads = database.get_collection(
            'pdf_custody_heads_v1', read_concern=ReadConcern('majority'),
            read_preference=ReadPreference.PRIMARY)

    def _prepare(self):
        hello = self.database.client.admin.command('hello')
        if not hello.get('setName') or not hello.get('logicalSessionTimeoutMinutes'):
            raise CustodyError('transactions_required', 'admission')

    def admit(self, request):
        document = _admission_data(request, self.policy)
        document['record_sha256'] = _record_digest(document)
        self._prepare()
        for attempt in range(3):
            try:
                with self.database.client.start_session() as session:
                    return session.with_transaction(
                        lambda current: self._publish(document, current),
                        read_concern=ReadConcern('snapshot'),
                        write_concern=WriteConcern('majority'),
                        read_preference=ReadPreference.PRIMARY)
            except DuplicateKeyError:
                if attempt == 2:
                    raise CustodyError('revision_conflict', 'admission') from None

    def _publish(self, document, session):
        existing = self.revisions.find_one({'_id': document['_id']}, session=session)
        if existing is not None:
            _verified_document(existing, document['_id'])
            if (existing['source_sha256'] != document['source_sha256']
                    or existing['request_sha256'] != document['request_sha256']
                    or existing['policy_sha256'] != document['policy_sha256']):
                raise CustodyError('revision_conflict', 'admission')
            return _receipt(existing, 'duplicate')
        head_id = document['project_id'] + ':' + document['material_id']
        head = self.heads.find_one({'_id': head_id}, session=session)
        revision = document['source_revision']
        if ((head is None and revision != 1)
                or (head is not None and (revision != head['source_revision'] + 1
                                         or document['previous_source_sha256'] != head['source_sha256']))):
            raise CustodyError('predecessor_conflict', 'admission')
        next_head = {'_id': head_id, 'source_revision': revision,
                     'source_sha256': document['source_sha256']}
        self.revisions.insert_one(document, session=session)
        if head is None:
            self.heads.insert_one(next_head, session=session)
        else:
            outcome = self.heads.replace_one(
                {'_id': head_id, 'source_revision': head['source_revision'],
                 'source_sha256': head['source_sha256']}, next_head, session=session)
            if outcome.matched_count != 1:
                raise CustodyError('predecessor_conflict', 'admission')
        return _receipt(document, 'admitted')

    def receipt(self, request):
        project, material, revision = _identity(request, self.policy)
        document = self.revisions.find_one({'_id': ':'.join((project, material, str(revision)))})
        if document is None:
            return {'admission_status': 'not_found'}
        _verified_document(document, ':'.join((project, material, str(revision))))
        if (document['source_sha256'] != _digest(request.get('expected_source_sha256'))
                or document['request_sha256'] != _digest(request.get('admission_request_sha256'))):
            raise CustodyError('revision_conflict')
        return _receipt(document, 'duplicate')

    def fetch(self, request):
        project, material, revision = _identity(request, self.policy)
        _policy_current(self.policy)
        if request.get('operation') != 'fetch_original':
            raise CustodyError('unsupported_operation')
        key = ':'.join((project, material, str(revision)))
        document = self.revisions.find_one({'_id': key})
        if document is None:
            raise CustodyError('not_found', 'retrieval')
        _verified_document(document, key)
        expected = _digest(request.get('expected_source_sha256'))
        if document['source_sha256'] != expected:
            raise CustodyError('revision_conflict', 'retrieval')
        if (document['policy_id'] != self.policy['policy_id']
                or document['policy_version'] != self.policy['policy_version']
                or document['policy_sha256'] != _policy_digest(self.policy)):
            raise CustodyError('policy_mismatch', 'retrieval')
        raw = _read_under(self.policy['source_root'], document['source_ref'],
                          self.policy['max_bytes'], stage='retrieval')
        if len(raw) != document['byte_length'] or hashlib.sha256(raw).hexdigest() != expected:
            raise CustodyError('hash_mismatch', 'retrieval')
        output_ref = request.get('output_ref')
        _deliver(self.policy['delivery_root'], output_ref, raw)
        return {'material_id': material, 'source_revision': revision,
                'source_sha256': expected, 'byte_length': len(raw),
                'bytes_ref': output_ref, 'custody_mode': 'verified_external_reference',
                'custody_owner': document['owner'], 'seal_check': 'not_applicable',
                'coverage': {'status': 'complete_for_declared_scope',
                             'scope': 'single_object', 'exclusions': []}}
