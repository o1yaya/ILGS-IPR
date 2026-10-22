"""Export real Bench intermediates without modifying model or evaluation files."""
import argparse
import json
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import segmentation_mask_stream as decoder


def trace_growth(scores, adjacency, labels):
    states = []
    previous = None
    def trace(frame, event, arg):
        nonlocal previous
        if frame.f_code is decoder.grow_mask.__code__:
            visited = frame.f_locals.get('visited')
            if visited:
                current = tuple(sorted(int(v) for v in visited))
                if current != previous:
                    states.append(current)
                    previous = current
            return trace
        return None
    old = sys.gettrace()
    try:
        sys.settrace(trace)
        mask = decoder.grow_mask(scores, adjacency, labels, 'seed_ref', 0.03)
    finally:
        sys.settrace(old)
    return mask, states


def label_rgb(labels):
    ids = np.unique(labels)
    result = np.zeros(labels.shape + (3,), dtype=np.uint8)
    for identity in ids:
        if identity == 0:
            color = (40, 43, 48)
        else:
            rng = np.random.RandomState(int(identity) % (2**32 - 1))
            color = rng.randint(65, 235, size=3)
        result[labels == identity] = color
    return result


def heat(values, low, high):
    t = np.clip((values-low)/max(high-low, 1e-8), 0, 1)[..., None]
    a = np.array([37, 66, 125]); b = np.array([252, 223, 102])
    return np.asarray(a*(1-t)+b*t, dtype=np.uint8)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output_root', type=Path, default=Path('paper_figures/method_assets'))
    p.add_argument('--clip_checkpoint', default='checkpoints/open_clip_pytorch_model.bin')
    p.add_argument('--views', nargs='+', type=int, default=[0,1,2,3,4])
    args = p.parse_args()
    query = 'Portuguese egg tart'
    dataset = ROOT/'dataset/3dovs/bench'
    ae_path = ROOT/'autoencoder/ckpt/3dovs/bench/best_ckpt.pth'
    required = [ae_path, Path(args.clip_checkpoint)]
    for variant in ('official', 'ipr'):
        base = ROOT/('output/3dovs/bench_ipr_%s_s0/test/ours_30000_text' % variant)
        for index in args.views:
            required += [base/'feature_map_npy'/('%05d.npy'%index), base/'logits'/('%05d_logits.npy'%index)]
    absent = [str(f) for f in required if not f.is_file()]
    if absent:
        raise FileNotFoundError('Missing existing render/checkpoint files:\n'+'\n'.join(absent))
    out = args.output_root/datetime.now().strftime('bench_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True)
    meta = {'scene':'bench','query':query,'seed':0,'decoder':'seed_ref','threshold_ratio':0.03,
            'source_repo':str(ROOT),'missing_optional':[], 'views':[],
            'latent_visualization':'3 latent channels, per-channel 1st/99th percentile RGB; not semantic probabilities',
            'identity_colors':'Deterministic by ID; background 0 dark gray',
            'confidence_range':[0,1]}
    for folder in ('object_mask','object_mask_refined','object_confidence_refined','object_confidence_ipr','object_mask_ipr_report'):
        source = dataset/folder
        if source.is_dir():
            shutil.copytree(source, out/'preprocessing'/folder)
        else:
            meta['missing_optional'].append(str(source))
    for name in ('ilgs_3dovs_layout.json','queries.txt'):
        if (dataset/name).is_file():
            shutil.copy2(dataset/name,out/name)
    rgb_dir=out/'rgb'; rgb_dir.mkdir()
    for source in sorted((dataset/'images').iterdir()):
        if source.suffix.lower() in ('.jpg','.jpeg','.png'):
            with Image.open(source) as im:
                im=im.convert('RGB'); im.thumbnail((1200,1200))
                im.save(rgb_dir/(source.stem+'.jpg'),quality=95)
    # Export readable offline maps while retaining the original integer PNGs.
    for folder in ('object_mask','object_mask_refined','object_confidence_refined','object_confidence_ipr'):
        src = out/'preprocessing'/folder
        if not src.exists():
            continue
        dest=out/'preprocessing_visuals'/folder; dest.mkdir(parents=True)
        for f in sorted(src.glob('*.png')):
            a=np.asarray(Image.open(f))
            if a.ndim != 2:
                continue
            arr=heat(a.astype(float)/255.,0,1) if 'confidence' in folder else label_rgb(a)
            Image.fromarray(arr).save(dest/f.name)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    text=decoder.load_text_features([query],device,args.clip_checkpoint)
    ae=decoder.load_autoencoder('3dovs/bench',device,str(ae_path))
    records=[]
    for variant in ('official','ipr'):
        base=ROOT/('output/3dovs/bench_ipr_%s_s0/test/ours_30000_text'%variant)
        for index in args.views:
            print('Exporting %s view %s'%(variant,index),flush=True)
            dest=out/'query'/variant/str(index); dest.mkdir(parents=True)
            feature=base/'feature_map_npy'/('%05d.npy'%index)
            labels=np.load(base/'logits'/('%05d_logits.npy'%index)).astype(np.int64)
            sim=decoder.decode_similarity_maps(str(feature),ae,text,device,16384)[:,:,0]
            if sim.shape != labels.shape or not np.isfinite(sim).all():
                raise ValueError('Invalid similarity map or shape mismatch')
            scores=decoder.compute_id_similarity(sim,labels,np.unique(labels))
            adjacency=decoder.build_adjacency(labels,legacy_wrap=False)
            final,states=trace_growth(scores,adjacency,labels)
            Image.fromarray(final).save(dest/'final_mask.png')
            Image.fromarray(label_rgb(labels)).save(dest/'identity_labels.png')
            np.save(dest/'identity_ids.npy',labels)
            np.save(dest/'cosine_similarity.npy',sim)
            segment=np.zeros(sim.shape,dtype=np.float32)
            for identity,score in scores.items():
                segment[labels==identity]=score
            np.save(dest/'segment_similarity.npy',segment)
            latent=np.moveaxis(np.load(feature),0,-1)
            lo=np.percentile(latent,1,axis=(0,1)); hi=np.percentile(latent,99,axis=(0,1))
            visual=(np.clip((latent-lo)/np.maximum(hi-lo,1e-8),0,1)*255).astype(np.uint8)
            Image.fromarray(visual).save(dest/'language_latent_rgb.png')
            for k,state in enumerate(states):
                m=(np.isin(labels,state)*255).astype(np.uint8)
                Image.fromarray(m).save(dest/('step_%03d.png'%k))
            if states and not np.array_equal(final,(np.isin(labels,states[-1])*255).astype(np.uint8)):
                raise RuntimeError('Recorded trajectory does not match decoder output')
            saved=base/'test_mask'/str(index)/(query+'.png')
            same=None
            if saved.is_file():
                a=np.asarray(Image.open(saved).convert('L'))
                same=bool(a.shape==final.shape and np.array_equal(a>0,final>0))
                shutil.copy2(saved,dest/'previous_eval_mask.png')
            for folder,name in [('renders','render_rgb.png'),('objects_feature16','identity_feature_pca.png')]:
                f=base/folder/('%05d.png'%index)
                if f.is_file(): shutil.copy2(f,dest/name)
            info={'variant':variant,'view':index,'visited_ids':states,'num_states':len(states),
                  'saved_eval_matches':same,'scores':{str(k):float(v) for k,v in scores.items()},
                  'latent_rgb_percentiles':[lo.tolist(),hi.tolist()]}
            (dest/'trace.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
            meta['views'].append(info)
            records.append((dest,sim,segment))
    low=min(float(s.min()) for _,s,_ in records); high=max(float(s.max()) for _,s,_ in records)
    meta['shared_similarity_color_limits']=[low,high]
    for dest,sim,segment in records:
        Image.fromarray(heat(sim,low,high)).save(dest/'cosine_heatmap.png')
        Image.fromarray(heat(segment,low,high)).save(dest/'segment_heatmap.png')
    (out/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    archive=out.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        tar.add(out,arcname=out.name)
    print('ARCHIVE='+str(archive),flush=True)
    print('Missing preprocessing folders: '+str(meta['missing_optional']))
    print('Previous-mask mismatches: '+str([(r['variant'],r['view']) for r in meta['views'] if r['saved_eval_matches'] is False]))


if __name__=='__main__':
    main()
