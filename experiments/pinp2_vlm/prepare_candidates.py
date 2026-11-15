"""Replay saved H10 predictions and prepare GT-free crops; no Torch on local host."""
import argparse, io, json, math, random, shutil, subprocess, time, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from common import HERE, dump, sha, metrics, load_predictions, write_jsonl

def crop_bounds(box,w,h,scale,minimum):
    x1,y1,x2,y2=box; side=math.ceil(max(minimum,scale*max(x2-x1,y2-y1)))
    cw,ch=min(side,w),min(side,h)
    left=max(0,min(w-cw,math.floor((x1+x2-cw)/2)))
    top=max(0,min(h-ch,math.floor((y1+y2-ch)/2)))
    return [left,top,left+cw,top+ch]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--predictions',type=Path,required=True);ap.add_argument('--annotations',type=Path,required=True);ap.add_argument('--images-zip',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    start=time.time();out=a.out;out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads((HERE/'config.json').read_text())
    assert all(cfg[k]==v for k,v in {'seed':42,'base_confidence':.25,'vlm_gate_low':.25,'vlm_gate_high':.60,'max_vlm_calls_per_image':2,'crop_scale':4.,'crop_min_side':64,'local_scale':1.5,'local_min_side':16}.items()),'Fixed protocol config mismatch'
    shutil.copy2(HERE/'config.json',out/'config.json')
    ann=json.loads(a.annotations.read_text())['validation'];pred=load_predictions(a.predictions)
    assert len(ann)==len(pred)==500 and set(pred)=={x['image'] for x in ann}
    for p in pred.values(): assert np.isfinite(p).all() and (p[:,5]==0).all() and (p[:,4]>=.001-1e-8).all()
    met=metrics(pred,ann);dump(out/'baseline_metrics.json',met)
    assert (met['TP'],met['FP'],met['FN'])==(323,119,163),met
    assert abs(met['mAP50_95_deployment']-.24351)<.00001,met
    shutil.copy2(a.predictions,out/'source_predictions.npz');dump(out/'annotations.json',ann)
    write_jsonl(out/'baseline_predictions.jsonl',[{'image_id':name,'box_id':j,'bbox_xyxy':p[:4].tolist(),'score':float(p[4])} for name,ps in pred.items() for j,p in enumerate(ps)])
    candidates=[]
    for mode in ['context','local']:(out/'crops'/mode).mkdir(parents=True)
    with zipfile.ZipFile(a.images_zip) as z:
        for entry in ann:
            name=entry['image']; data=z.read(name)
            import hashlib
            assert hashlib.sha256(data).hexdigest()==entry['image_sha256'],name
            label=z.read(entry['label']);assert hashlib.sha256(label).hexdigest()==entry['label_sha256']
            im=Image.open(io.BytesIO(data)).convert('RGB');w,h=im.size
            assert (w,h)==(entry['width'],entry['height'])
            # Ground truth only audits provenance/evaluation, never crop choice.
            ps=pred[name]; chosen=[j for j,p in enumerate(ps) if .25<=p[4]<.60]
            chosen=sorted(chosen,key=lambda j:(float(ps[j,4]),j))[:2]
            for j,p in enumerate(ps):
                if p[4]<.25:continue
                box=p[:4].tolist();key=f'{Path(name).stem}__{j:03d}'
                rec={'image_id':name,'box_id':j,'candidate_id':key,'bbox_xyxy':box,'score':float(p[4]),'selected':j in chosen,'source_image_sha256':entry['image_sha256'],'crops':{}}
                for mode,scale,minimum in [('context',4.,64),('local',1.5,16)]:
                    bounds=crop_bounds(box,w,h,scale,minimum);crop=im.crop(bounds);path=out/'crops'/mode/(key+'.png');crop.save(path)
                    assert bounds[0]<= (box[0]+box[2])/2<=bounds[2] and bounds[1]<=(box[1]+box[3])/2<=bounds[3]
                    rec['crops'][mode]={'path':str(path.relative_to(out)),'bounds':bounds,'native_size':list(crop.size),'sha256':sha(path)}
                candidates.append(rec)
    write_jsonl(out/'candidates.jsonl',candidates)
    selected=random.Random(42).sample(candidates,20);sheet=Image.new('RGB',(1000,1000),'white');d=ImageDraw.Draw(sheet)
    for i,c in enumerate(selected):
        x=(i%5)*200;y=(i//5)*250
        im=Image.open(out/c['crops']['context']['path']);sheet.paste(im.resize((192,192)),(x,y))
        d.text((x+3,y+196),c['candidate_id'],fill='black');d.text((x+3,y+214),f'score {c["score"]:.4f}',fill='black')
    sheet.save(out/'crop_preview.jpg');dump(out/'crop_preview_selection.json',[c['candidate_id'] for c in selected])
    receipt={'predictions_path':str(a.predictions.resolve()),'predictions_sha256':sha(a.predictions),'annotations_path':str(a.annotations.resolve()),'annotations_sha256':sha(a.annotations),'images_zip_path':str(a.images_zip.resolve()),'images_zip_sha256':sha(a.images_zip),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE).decode().strip(),'images':500,'all_predictions':sum(map(len,pred.values())),'above_025':len(candidates),'selective_calls':sum(c['selected'] for c in candidates),'candidate_selection':'score ascending then source box_id, at most 2 per image in [0.25,0.60)','ap_source_floor':.001,'preparation_seconds':time.time()-start,'config_sha256':sha(HERE/'config.json')}
    receipt['started_unix']=start;receipt['completed_unix']=time.time()
    eligible=[c for c in candidates if .25<=c['score']<.6]
    dump(out/'selection_summary.json',{'candidate_images':len({c['image_id'] for c in candidates}),'images_without_candidates':500-len({c['image_id'] for c in candidates}),'all_candidates':len(candidates),'eligible_low_confidence':len(eligible),'high_confidence':sum(c['score']>=.6 for c in candidates),'selected_calls':sum(c['selected'] for c in candidates),'eligible_skipped_by_per_image_cap':sum(not c['selected'] for c in eligible)})
    dump(out/'preparation.json',receipt);print(json.dumps({'baseline':met,'preparation':receipt},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
