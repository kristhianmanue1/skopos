"""Perfil acotado de derivados PDF para originales con distinta paginación."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat

from skopos.pdf_custody import _digest, _identifier, _policy_digest, _root_fd, load_policy
from skopos.pdf_document_store import (DocumentError, GRAPH_SCRIPT, EXTRACT_SCRIPT,
                                       MAX_POLICY_BYTES, SCRIPT, STORE_SCRIPT,
                                       _file_sha256)


POLICY_SCHEMA = 'skopos/pdf-document-policy/v0.2'
POLICY_SCRIPT = Path(__file__).resolve()


def load_document_policy_v02(path):
    """La política viene del host; una solicitud no puede elegir roots ni motores."""
    path = Path(path)
    if not path.is_absolute():
        raise DocumentError('policy_unavailable')
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise DocumentError('policy_unavailable')
            raw = stream.read(MAX_POLICY_BYTES + 1)
        if len(raw) > MAX_POLICY_BYTES:
            raise DocumentError('policy_unavailable')
        policy = json.loads(raw)
    except (OSError, UnicodeError, ValueError):
        raise DocumentError('policy_unavailable') from None
    required = {
        'schema', 'policy_id', 'policy_version', 'project_id', 'owner',
        'custody_policy_path', 'custody_policy_sha256', 'custody_receipt_id',
        'material_id', 'source_revision', 'source_sha256', 'provenance_sha256',
        'requests_root', 'derived_root', 'delivery_root', 'cache_root',
        'retention_until', 'retention_basis', 'retention_action',
        'max_page', 'ocr_pages', 'graph_pages', 'allowed_modalities',
        'max_pages', 'max_ocr_pages', 'max_render_pixels', 'max_seconds',
        'max_output_bytes', 'render_scale_to', 'allow_network',
        'swift_path', 'renderer_path', 'engine_script_sha256',
        'graph_engine_sha256', 'extract_engine_sha256',
        'store_engine_sha256', 'policy_engine_sha256',
    }
    if (not isinstance(policy, dict) or set(policy) != required
            or policy['schema'] != POLICY_SCHEMA
            or policy['project_id'] != 'expertogobernanza'
            or policy['owner'] != 'expertogobernanza'
            or policy['allow_network'] is not False
            or policy['retention_action'] != 'block_then_explicit_retirement'):
        raise DocumentError('policy_unavailable')
    for field in ('requests_root', 'derived_root', 'delivery_root', 'cache_root'):
        descriptor = _root_fd(policy[field])
        os.close(descriptor)
    for field in ('policy_id', 'policy_version', 'retention_basis'):
        if not isinstance(policy[field], str) or not policy[field]:
            raise DocumentError('policy_unavailable')
    for field in ('material_id', 'project_id'):
        _identifier(policy[field])
    for field in ('source_sha256', 'provenance_sha256',
                  'custody_policy_sha256', 'engine_script_sha256',
                  'graph_engine_sha256', 'extract_engine_sha256',
                  'store_engine_sha256', 'policy_engine_sha256'):
        _digest(policy[field])
    if type(policy['source_revision']) is not int or policy['source_revision'] != 1:
        raise DocumentError('policy_unavailable')
    if (type(policy['max_page']) is not int or not 1 <= policy['max_page'] <= 500
            or type(policy['max_pages']) is not int
            or not 1 <= policy['max_pages'] <= policy['max_page']
            or type(policy['max_ocr_pages']) is not int
            or not 0 <= policy['max_ocr_pages'] <= 8
            or not isinstance(policy['ocr_pages'], list)
            or policy['ocr_pages'] != sorted(set(policy['ocr_pages']))
            or not isinstance(policy['graph_pages'], list)
            or policy['graph_pages'] != sorted(set(policy['graph_pages']))
            or any(type(page) is not int or not 1 <= page <= policy['max_page']
                   for page in policy['ocr_pages'] + policy['graph_pages'])
            or len(policy['ocr_pages']) > policy['max_ocr_pages']
            or policy['allowed_modalities'] !=
               ['native_text', 'selective_ocr', 'visual_graph']
            or type(policy['max_render_pixels']) is not int
            or not 1 <= policy['max_render_pixels'] <= 4_452_000
            or type(policy['max_seconds']) is not int
            or not 1 <= policy['max_seconds'] <= 120
            or type(policy['max_output_bytes']) is not int
            or not 1 <= policy['max_output_bytes'] <= 10_000_000
            or type(policy['render_scale_to']) is not int
            or not 500 <= policy['render_scale_to'] <= 2400):
        raise DocumentError('policy_unavailable')
    if not all(isinstance(policy[field], str) and os.path.isabs(policy[field])
               for field in ('custody_policy_path', 'swift_path', 'renderer_path')):
        raise DocumentError('policy_unavailable')
    engines = ((SCRIPT, 'engine_script_sha256'),
               (GRAPH_SCRIPT, 'graph_engine_sha256'),
               (EXTRACT_SCRIPT, 'extract_engine_sha256'),
               (STORE_SCRIPT, 'store_engine_sha256'),
               (POLICY_SCRIPT, 'policy_engine_sha256'))
    if any(_file_sha256(script) != policy[field] for script, field in engines):
        raise DocumentError('engine_mismatch')
    try:
        expires = datetime.fromisoformat(policy['retention_until'].replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        raise DocumentError('retention_policy_missing') from None
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
        raise DocumentError('retention_policy_missing')
    custody = load_policy(policy['custody_policy_path'])
    try:
        custody_expires = datetime.fromisoformat(
            custody['retention_until'].replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        raise DocumentError('custody_policy_mismatch') from None
    if (_policy_digest(custody) != policy['custody_policy_sha256']
            or expires > custody_expires
            or custody['project_id'] != policy['project_id']
            or len(custody.get('allowed_materials', [])) != 1):
        raise DocumentError('custody_policy_mismatch')
    allowed = custody['allowed_materials'][0]
    if (allowed['material_id'] != policy['material_id']
            or allowed['source_revision'] != policy['source_revision']
            or allowed['source_sha256'] != policy['source_sha256']
            or allowed['provenance_sha256'] != policy['provenance_sha256']):
        raise DocumentError('custody_policy_mismatch')
    return policy
