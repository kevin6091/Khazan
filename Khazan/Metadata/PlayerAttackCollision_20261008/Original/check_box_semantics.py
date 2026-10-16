"""Recover box geometry convention from original saved baking bounds."""
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent


def vec(v):
    return [float((v or {}).get(a, 0)) for a in 'XYZ']


def quat(r):
    p, y, roll = [math.radians(float((r or {}).get(a, 0))) / 2 for a in ('Pitch', 'Yaw', 'Roll')]
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(roll), math.cos(roll)
    return [cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy,
            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy]


def mul(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]


def matrix(q):
    x, y, z, w = q
    return [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]


def rotate(q, v):
    m = matrix(q)
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def geometry(w, key, scale=1, rotation_order='raw_then_relative', offset_uses_relative=False):
    raw_q, relative_q = quat(key['local_rotator_degrees_raw']), quat(w['relative_rotation_raw'])
    q = mul(raw_q, relative_q) if rotation_order == 'raw_then_relative' else mul(relative_q, raw_q)
    off = rotate(q if offset_uses_relative else raw_q, vec(w['relative_offset_raw']))
    c = [x+y+z for x,y,z in zip(vec(key['local_center_pos_raw']), off, vec(w['absolute_offset_raw']))]
    m = matrix(q)
    extent = vec(w['size_raw'])
    ex = [sum(abs(m[i][j]) * extent[j] * scale for j in range(3)) for i in range(3)]
    return c, q, ex


def bounds_error(w, scale=1, rotation_order='raw_then_relative', offset_uses_relative=False):
    minimum, maximum = [math.inf]*3, [-math.inf]*3
    for k in w['baked_keys']:
        c, q, ex = geometry(w, k, scale, rotation_order, offset_uses_relative)
        minimum = [min(a, b-e) for a,b,e in zip(minimum,c,ex)]
        maximum = [max(a, b+e) for a,b,e in zip(maximum,c,ex)]
    b = w['baked_bounds_raw']
    return max(abs(a-b) for a,b in zip(minimum+maximum, vec(b['Min'])+vec(b['Max']))), minimum, maximum


def main():
    data = json.loads((HERE/'SourceAttackWindows.json').read_text(encoding='utf-8'))
    rows = []
    for c in data['composites']:
        for w in c['attack_windows']:
            if w['shape_raw'] != 'EAttackShape::AttackBoxComponent' or not w['baked_keys'] or not w['baked_bounds_raw']:
                continue
            if not w['baked_bounds_raw'].get('IsValid'):
                continue
            models = []
            for rotation_order in ('raw_then_relative', 'relative_then_raw'):
                for offset_uses_relative in (False, True):
                    err, mn, mx = bounds_error(w, 1, rotation_order, offset_uses_relative)
                    models.append({'size_is_half_extent': True, 'rotation_order': rotation_order,
                                   'offset_rotated_by_combined_relative_rotation': offset_uses_relative,
                                   'max_bounds_error_cm': err, 'calculated_min': mn, 'calculated_max': mx})
            models.sort(key=lambda x: x['max_bounds_error_cm'])
            full_err, mn, mx = bounds_error(w, .5)
            rows.append({'package': c['package'], 'source_file': c['metadata_file'],
                         'source_sha256': c['metadata_sha256'], 'attack_export_index': w['attack_export_index'],
                         'attack_export_name': w['attack_export_name'],
                         'source_fields': ['Properties.Size', 'Properties.RelativeOffset', 'Properties.AbsoluteOffset',
                                           'Properties.RelativeRotatoion', 'Properties.PostCleaningAttackInfo.AttackBoxList',
                                           'Properties.PostCleaningAttackInfo.Bounds'],
                         'raw_size': w['size_raw'], 'source_bounds': w['baked_bounds_raw'],
                         'baked_keys': w['baked_key_count'], 'default_order_half_extent_error_cm': models[0]['max_bounds_error_cm'] if not w['relative_rotation_raw'] else bounds_error(w)[0],
                         'size_divided_by_two_error_cm': full_err, 'best_model': models[0],
                         'matches_original_bounds_at_0_001_cm': models[0]['max_bounds_error_cm'] < .001,
                         'geometry_keys_derived_using_best_model': [
                             {'original_time_seconds': k['time_seconds_raw'],
                              'source_local_center_cm': geometry(w,k,rotation_order=models[0]['rotation_order'],offset_uses_relative=models[0]['offset_rotated_by_combined_relative_rotation'])[0],
                              'source_local_quaternion_xyzw': geometry(w,k,rotation_order=models[0]['rotation_order'],offset_uses_relative=models[0]['offset_rotated_by_combined_relative_rotation'])[1]}
                             for k in w['baked_keys']]})
    report = {'schema': 1, 'method': 'UE FRotator quaternion formula; transformed box-corner union against original PostCleaningAttackInfo.Bounds. .001cm is numerical comparison tolerance, not gameplay tuning.',
              'conclusions': {
                  'size': 'Box Size is half-extents, supported by reconstructed source bounds (see per-window matches).',
                  'baked_center': 'LocalCenterPos is attachment-origin transform. It must be composed with RelativeOffset and AbsoluteOffset to obtain collision center.',
                  'rotation': 'RelativeRotatoion composition is derived per-window by original bounds comparison; use best_model only when it matches.',
                  'local_reference_frame': 'Original native local-frame origin still unverified. Derived keys remain source-local, not confirmed current capsule-center actor-local.',
                  'cylinder': 'Box evidence does not prove Cylinder fields/height conventions.'},
              'summary': {'windows_checked': len(rows), 'matching_best_model': sum(r['matches_original_bounds_at_0_001_cm'] for r in rows),
                          'nonmatching_windows': [(r['attack_export_name'], r['best_model']['max_bounds_error_cm']) for r in rows if not r['matches_original_bounds_at_0_001_cm']]},
              'windows': rows}
    (HERE/'BoxSemantics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary']))


if __name__ == '__main__':
    main()
