"""Collect existing Bench figure inputs without changing training outputs."""
import argparse
import json
import tarfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--repo', type=Path, default=Path.cwd())
p.add_argument('--out', type=Path, default=Path('/media/cx/data/cxdata/ipr_bench_figure_assets.tar.gz'))
a = p.parse_args()
root = a.repo.resolve()
scene = root / 'dataset/3dovs/bench'
files = []
missing = []
for folder in ('object_mask', 'object_mask_refined', 'object_confidence_refined', 'object_confidence_ipr', 'object_mask_ipr_report'):
    d = scene / folder
    if d.is_dir():
        files.extend(f for f in d.rglob('*') if f.is_file())
    else:
        missing.append(str(d))
for name in ('ilgs_3dovs_layout.json', 'queries.txt'):
    f = scene / name
    if f.is_file():
        files.append(f)
for variant in ('official', 'ipr'):
    base = root / f'output/3dovs/bench_ipr_{variant}_s0/test/ours_30000_text'
    for folder in ('renders', 'objects_feature16', 'test_mask'):
        d = base / folder
        if d.is_dir():
            files.extend(f for f in d.rglob('*') if f.is_file())
a.out.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(a.out, 'w:gz') as archive:
    for f in sorted(set(files)):
        archive.add(f, arcname=str(f.relative_to(root)), recursive=False)
print(json.dumps({'archive':str(a.out), 'files':len(set(files)), 'bytes':a.out.stat().st_size, 'missing':missing}, indent=2))
print('Actual seed / expansion states require decoder instrumentation if not already saved.')
