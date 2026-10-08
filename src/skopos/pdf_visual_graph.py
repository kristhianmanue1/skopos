"""Lectura conservadora de cajas y conexiones en renders PNG de diagramas."""

import struct
import zlib
from pathlib import Path


class VisualGraphError(ValueError):
    pass


def _gray_png(path, max_pixels):
    raw = Path(path).read_bytes()
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise VisualGraphError('invalid_render')
    offset, chunks = 8, []
    width = height = channels = None
    while offset + 12 <= len(raw):
        length = struct.unpack_from('>I', raw, offset)[0]
        kind = raw[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(raw):
            raise VisualGraphError('invalid_render')
        payload = raw[offset + 8:offset + 8 + length]
        checksum = struct.unpack_from('>I', raw, offset + 8 + length)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != checksum:
            raise VisualGraphError('invalid_render')
        if kind == b'IHDR':
            if length != 13:
                raise VisualGraphError('invalid_render')
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            channels = {0: 1, 2: 3, 6: 4}.get(color)
            if (depth != 8 or channels is None or compression or filtering or interlace
                    or width < 1 or height < 1 or width * height > max_pixels):
                raise VisualGraphError('unsupported_render')
        elif kind == b'IDAT':
            chunks.append(payload)
        elif kind == b'IEND':
            break
        offset = end
    if width is None or not chunks:
        raise VisualGraphError('invalid_render')
    stride = width * channels
    expected = height * (stride + 1)
    decoder = zlib.decompressobj()
    data = decoder.decompress(b''.join(chunks), expected + 1)
    if len(data) != expected or decoder.unconsumed_tail or not decoder.eof:
        raise VisualGraphError('invalid_render')
    pixels = bytearray(width * height)
    previous = bytearray(stride)
    position = 0
    for y in range(height):
        filter_type = data[position]
        position += 1
        row = bytearray(data[position:position + stride])
        position += stride
        if filter_type > 4:
            raise VisualGraphError('invalid_render')
        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            above = previous[x]
            corner = previous[x - channels] if x >= channels else 0
            if filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                base = left + above - corner
                distances = (abs(base - left), abs(base - above), abs(base - corner))
                predictor = (left, above, corner)[distances.index(min(distances))]
            else:
                predictor = 0
            row[x] = (row[x] + predictor) & 255
        if channels == 1:
            pixels[y * width:(y + 1) * width] = row
        else:
            for x in range(width):
                start = x * channels
                pixels[y * width + x] = (row[start] * 77 + row[start + 1] * 150
                                         + row[start + 2] * 29) >> 8
        previous = row
    return width, height, pixels


def _runs(pixels, width, height, horizontal, threshold=140):
    result = []
    outer, inner = (height, width) if horizontal else (width, height)
    minimum = 60 if horizontal else 30
    for fixed in range(outer):
        varying = 0
        while varying < inner:
            index = fixed * width + varying if horizontal else varying * width + fixed
            if pixels[index] >= threshold:
                varying += 1
                continue
            start = varying
            while varying < inner:
                index = fixed * width + varying if horizontal else varying * width + fixed
                if pixels[index] >= threshold:
                    break
                varying += 1
            if varying - start >= minimum:
                result.append((start, fixed, varying - 1, fixed) if horizontal else
                              (fixed, start, fixed, varying - 1))
    return result


def _cluster(segments, horizontal):
    groups = []
    for segment in segments:
        for group in groups:
            first = group[0]
            close = (abs(segment[1] - first[1]) <= 3 and
                     abs(segment[0] - first[0]) <= 5 and
                     abs(segment[2] - first[2]) <= 5) if horizontal else (
                     abs(segment[0] - first[0]) <= 3 and
                     abs(segment[1] - first[1]) <= 5 and
                     abs(segment[3] - first[3]) <= 5)
            if close:
                group.append(segment)
                break
        else:
            groups.append([segment])
    return [max(group, key=lambda item: item[2] - item[0] + item[3] - item[1])
            for group in groups]


def _touch(first, second):
    first_h = first[1] == first[3]
    second_h = second[1] == second[3]
    if first_h and not second_h:
        return (first[0] - 4 <= second[0] <= first[2] + 4
                and second[1] - 4 <= first[1] <= second[3] + 4)
    if second_h and not first_h:
        return _touch(second, first)
    if first_h:
        return (abs(first[1] - second[1]) <= 4
                and max(first[0], second[0]) <= min(first[2], second[2]) + 4)
    return (abs(first[0] - second[0]) <= 4
            and max(first[1], second[1]) <= min(first[3], second[3]) + 4)


def _bbox(box, width, height):
    return [round(box[0] / width, 6), round(box[1] / height, 6),
            round(box[2] / width, 6), round(box[3] / height, 6)]


def _arrow_at(pixels, width, height, x, y, arm_sign):
    """Dos brazos diagonales junto al extremo de un conector vertical."""
    for tip_y in range(y - 3, y + 4):
        matched = 0
        for distance in (5, 8, 11):
            arm_y = tip_y + arm_sign * distance
            if not 1 <= arm_y < height - 1:
                continue
            sides = []
            for arm_x in (x - distance, x + distance):
                sides.append(any(0 <= arm_x + dx < width and
                                 pixels[(arm_y + dy) * width + arm_x + dx] < 140
                                 for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
            if all(sides):
                matched += 1
        if matched >= 2:
            return True
    return False


def read_visual_graph(png_path, ocr_lines, *, max_pixels, diagram_type='organigram'):
    """Relaciones topológicas; la dirección requiere una punta visible."""
    if diagram_type not in ('organigram', 'flowchart'):
        raise VisualGraphError('invalid_diagram_type')
    width, height, pixels = _gray_png(png_path, max_pixels)
    horizontal = _cluster(_runs(pixels, width, height, True), True)
    vertical = _cluster(_runs(pixels, width, height, False), False)
    boxes = []
    for index, top in enumerate(horizontal):
        x1, y1, x2, _ = top
        box_width = x2 - x1
        if not 80 <= box_width <= min(400, width * 0.4):
            continue
        for bottom in horizontal[index + 1:]:
            bx1, y2, bx2, _ = bottom
            if (not 40 <= y2 - y1 <= min(250, height * 0.2)
                    or abs(bx1 - x1) > 5 or abs(bx2 - x2) > 5):
                continue
            if (any(abs(line[0] - x1) <= 4 and line[1] <= y1 + 3
                    and line[3] >= y2 - 3 for line in vertical)
                    and any(abs(line[0] - x2) <= 4 and line[1] <= y1 + 3
                            and line[3] >= y2 - 3 for line in vertical)
                    and box_width / (y2 - y1) >= 1.4):
                box = (x1, y1, x2, y2)
                if not any(sum(abs(a - b) for a, b in zip(box, old)) < 15
                           for old in boxes):
                    boxes.append(box)
    boxes.sort(key=lambda box: (box[1], box[0]))

    def border(line):
        for x1, y1, x2, y2 in boxes:
            if line[1] == line[3]:
                if (abs(line[0] - x1) < 5 and abs(line[2] - x2) < 5
                        and (abs(line[1] - y1) < 5 or abs(line[1] - y2) < 5)):
                    return True
            elif ((abs(line[0] - x1) < 5 or abs(line[0] - x2) < 5)
                  and abs(line[1] - y1) < 5 and abs(line[3] - y2) < 5):
                return True
        return False

    if boxes:
        y_min = min(box[1] for box in boxes) - 100
        y_max = max(box[3] for box in boxes) + 100
        segments = [line for line in horizontal + vertical
                    if y_min <= line[1] and line[3] <= y_max and not border(line)]
    else:
        segments = []
    parents = list(range(len(segments)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for index, line in enumerate(segments):
        for previous in range(index):
            if _touch(line, segments[previous]):
                parents[find(index)] = find(previous)
    components = {}
    for index, line in enumerate(segments):
        components.setdefault(find(index), []).append(line)
    nodes = []
    for index, box in enumerate(boxes):
        x1, y1, x2, y2 = box
        labels = [(line_index, line) for line_index, line in enumerate(ocr_lines)
                  if isinstance(line.get('bbox'), list)
                  and len(line['bbox']) == 4
                  and x1 / width <= (line['bbox'][0] + line['bbox'][2]) / 2 <= x2 / width
                  and y1 / height <= (line['bbox'][1] + line['bbox'][3]) / 2 <= y2 / height]
        nodes.append({'node_id': 'n' + str(index + 1), 'bbox': _bbox(box, width, height),
                      'label': ' '.join(line['text'] for _, line in labels),
                      'label_status': 'ocr_unreviewed' if labels else 'unknown',
                      'ocr_line_indices': [line_index for line_index, _ in labels]})
    connectors, edges, unknown = [], [], []
    for component in components.values():
        ports = set()
        for index, (x1, y1, x2, y2) in enumerate(boxes):
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            for side, point_y in (('top', y1), ('bottom', y2)):
                if any(line[0] == line[2] and abs(line[0] - center_x) <= 6
                       and (abs(line[1] - point_y) <= 5 or abs(line[3] - point_y) <= 5)
                       for line in component):
                    ports.add((index, side))
            for line in component:
                if line[0] != line[2] or not line[1] - 5 <= center_y <= line[3] + 5:
                    continue
                for side, point_x in (('left', x1), ('right', x2)):
                    distance = point_x - line[0] if side == 'left' else line[0] - point_x
                    if not 5 <= distance <= 40:
                        continue
                    start, stop = sorted((point_x, line[0]))
                    for row in range(max(0, center_y - 5), min(height, center_y + 6)):
                        dark = sum(pixels[row * width + x] < 140 for x in range(start, stop + 1))
                        if dark / (stop - start + 1) > 0.8:
                            ports.add((index, side))
                            break
        if len({index for index, _ in ports}) < 2:
            continue
        connector_id = 'c' + str(len(connectors) + 1)
        connectors.append({'connector_id': connector_id,
                           'segments': [_bbox(line, width, height) for line in component],
                           'ports': [{'node_id': 'n' + str(index + 1), 'side': side}
                                     for index, side in sorted(ports)]})
        parents_here = [index for index, side in ports if side == 'bottom']
        children = [index for index, side in ports if side in ('top', 'left', 'right')]
        if len(set(parents_here)) == 1 and children:
            parent = parents_here[0]
            for child in sorted(set(children) - {parent}):
                origin, target = parent, child
                direction, status = 'unknown', 'topology_hypothesis'
                if diagram_type == 'flowchart' and len(set(children)) == 1:
                    upper, lower = boxes[parent], boxes[child]
                    upper_x = (upper[0] + upper[2]) // 2
                    lower_x = (lower[0] + lower[2]) // 2
                    arrow_up = _arrow_at(pixels, width, height, upper_x,
                                         upper[3], 1)
                    arrow_down = _arrow_at(pixels, width, height, lower_x,
                                           lower[1], -1)
                    if arrow_up != arrow_down:
                        direction, status = 'observed', 'arrowhead_observed'
                        if arrow_up:
                            origin, target = child, parent
                edges.append({'from_node': 'n' + str(origin + 1),
                              'to_node': 'n' + str(target + 1),
                              'connector_id': connector_id, 'direction': direction,
                              'status': status})
        else:
            unknown.append({'connector_id': connector_id,
                            'reason': 'ambiguous_ports_or_direction'})
    return {'status': 'partial' if nodes else 'no_graph_detected',
            'diagram_type': diagram_type, 'nodes': nodes,
            'connectors': connectors, 'edges': edges, 'unknown': unknown,
            'direction_rule': 'unknown_without_visible_arrowhead'}
