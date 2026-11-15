"""NumPy-only common I/O; original evaluator is imported without modification."""
import sys, json, hashlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/evaluation'))
from detection_eval import match, iou, evaluate_records, summarize

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
def write_jsonl(path, rows):
    with Path(path).open('w') as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + '\n')
def read_jsonl(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def load_predictions(path):
    z = np.load(path, allow_pickle=False)
    return {str(n): z['detections'][z['offsets'][i]:z['offsets'][i+1]].copy() for i,n in enumerate(z['images'])}
def metrics(predictions, annotations, threshold=.25):
    records=[]; bird_fp=0
    for a in annotations:
        p=predictions[a['image']]; gt=np.asarray(a['UAV_boxes'],dtype=np.float32).reshape(-1,4)
        r=evaluate_records(p,gt); fixed=p[p[:,4]>=threshold]
        r['correct_fixed']=match(fixed,gt); records.append(r)
        fp=fixed[~r['correct_fixed'][:,0]]
        bird_fp+=int(match(fp,np.asarray(a['bird_boxes'],dtype=np.float32).reshape(-1,4))[:,0].sum())
    result=summarize(records,threshold)
    result['fixed_matching']=f'filter conf {threshold} first; original IoU-first one-to-one matcher'
    result['bird_associated_FP']=bird_fp
    return result
