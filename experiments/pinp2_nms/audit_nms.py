"""Replay frozen predictions; no model/runtime inference. Never modifies source artifacts."""
import argparse, csv, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'experiments/pinp2_vlm'))
from common import load_predictions, metrics, match, iou, sha, dump
from detection_eval import nms

THRESHOLDS = [.3, .4, .5, .6, .7, .8, .9]

def reference_nms(boxes, scores, threshold, max_det=300):
    # Independent scalar greedy implementation, including stable ties and strict > suppression.
    remaining = sorted(range(len(scores)), key=lambda j: (-float(scores[j]), j))[:30000]
    keep = []
    while remaining and len(keep) < max_det:
        j = remaining.pop(0); keep.append(j); next_ids = []
        for k in remaining:
            a, b = boxes[j], boxes[k]
            intersection = max(0., float(min(a[2], b[2])-max(a[0], b[0]))) * max(0., float(min(a[3], b[3])-max(a[1], b[1])))
            aa = max(0., float(a[2]-a[0]))*max(0., float(a[3]-a[1]))
            ab = max(0., float(b[2]-b[0]))*max(0., float(b[3]-b[1]))
            if intersection/(aa+ab-intersection+1e-7) <= threshold: next_ids.append(k)
        remaining = next_ids
    return np.asarray(keep, dtype=int)

def checks():
    rng = np.random.default_rng(42); tested = 0
    fixtures = [(np.empty((0,4)),np.empty(0)),(np.array([[0,0,3,3],[0,0,3,3],[10,10,13,13]],float),np.array([.5,.5,.4]))]
    for count in [1,10,100,301]:
        xy = rng.uniform(0,50,(count,2)); boxes=np.c_[xy,xy+rng.uniform(1,20,(count,2))]
        fixtures.append((boxes,rng.integers(0,10,count)/10))
    for boxes,scores in fixtures:
        for threshold in [0.,.3,.5,.7,1.]:
            for cap in [1,300]:
                assert np.array_equal(nms(boxes,scores,threshold,cap), reference_nms(boxes,scores,threshold,cap)); tested+=1
    boxes=np.array([[0,0,3,3],[1,0,4,3]],float); boundary=float(iou(boxes[:1],boxes[1:])[0,0])
    assert len(nms(boxes,np.array([.9,.8]),boundary))==2
    assert len(nms(boxes,np.array([.9,.8]),np.nextafter(boundary,0)))==1
    return {'independent_random_and_edge_cases':tested,'strict_IoU_boundary_passed':True}

def fp_diagnostics(pred, ann):
    rows=[]
    for a in ann:
        p=pred[a['image']];p=p[p[:,4]>=.25];gt=np.asarray(a['UAV_boxes'],np.float32).reshape(-1,4)
        correct=match(p,gt)[:,0]; overlaps=iou(p[:,:4],gt); covered=(overlaps[correct]>=.5).any(0)
        for j in np.flatnonzero(~correct):
            maximum=float(overlaps[j].max()) if len(gt) else 0.
            rows.append({'image':a['image'],'max_iou_UAV':maximum,'duplicate_matching_conflict':bool(((overlaps[j]>=.5)&covered).any())})
    return {'FP':len(rows),'FP_overlapping_already_detected_UAV':sum(r['duplicate_matching_conflict'] for r in rows),'FP_UAV_IoU_01_05':sum(.1<=r['max_iou_UAV']<.5 for r in rows),'FP_UAV_IoU_under01':sum(r['max_iou_UAV']<.1 for r in rows)},rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--h10',type=Path,required=True);ap.add_argument('--fp32',type=Path,required=True);ap.add_argument('--annotations',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);ann=json.loads(args.annotations.read_text());order=[a['image'] for a in ann];assert len(order)==len(set(order))==500
    evidence={'status':'offline post-hoc validation, no hardware timing','thresholds':THRESHOLDS,'confidence':.25,'AP_floor':.001,'max_det':300,'protocol':'Apply greedy NMS after original-coordinate restoration/clipping to frozen top-300 predictions; unchanged scores, original evaluator, canonical annotation order. No access to discarded pre-top-300 boxes.','checks':checks(),'sources':{'annotations_sha256':sha(args.annotations)},'duplicate_diagnosis':{}}
    rows=[];paired=[]
    for name,path in [('FP32',args.fp32),('H10',args.h10)]:
        source=load_predictions(path);assert set(source)==set(order)
        assert all(np.isfinite(p).all() and (p[:,5]==0).all() and (p[:,4]>=.001).all() for p in source.values())
        evidence['sources'][name+'_sha256']=sha(path)
        evidence['duplicate_diagnosis'][name],details=fp_diagnostics(source,ann)
        dump(args.output/(name+'_fp_overlap.json'),details)
        fixed={a['image']:match(source[a['image']][source[a['image']][:,4]>=.25],np.asarray(a['UAV_boxes'],np.float32).reshape(-1,4))[:,0] for a in ann}
        for threshold in [None,*THRESHOLDS]:
            preds={};suppressed_tp=0;changed=0;tp_losses=0;tp_gains=0
            for a in ann:
                image=a['image'];p=source[image];idx=np.arange(len(p)) if threshold is None else nms(p[:,:4],p[:,4],threshold)
                preds[image]=p[idx]
                q=p[p[:,4]>=.25];qids=np.flatnonzero(p[:,4]>=.25); retained=set(idx.tolist())
                suppressed_tp+=sum(bool(ok) and int(j) not in retained for j,ok in zip(qids,fixed[image]))
                if threshold is not None:
                    # Scalar reference on every real candidate set; confidence filtering must commute.
                    assert np.array_equal(idx,reference_nms(p[:,:4],p[:,4],threshold))
                    assert np.array_equal(p[idx][p[idx,4]>=.25],q[nms(q[:,:4],q[:,4],threshold)])
                gt=np.asarray(a['UAV_boxes'],np.float32).reshape(-1,4);tp=int(match(preds[image][preds[image][:,4]>=.25],gt)[:,0].sum());old=int(fixed[image].sum())
                tp_losses+=max(0,old-tp);tp_gains+=max(0,tp-old);changed+=old!=tp
                paired.append({'source':name,'nms_iou':threshold,'image':image,'old_TP':old,'new_TP':tp})
            result=metrics(preds,ann)
            row={'source':name,'nms_iou':'none' if threshold is None else threshold,**{k:result[k] for k in ['TP','FP','FN','Precision_fixed','Recall_fixed','F1_fixed','mAP50_deployment','mAP50_95_deployment','bird_associated_FP']},'original_TP_boxes_suppressed':suppressed_tp,'images_with_TP_change':changed,'paired_TP_losses':tp_losses,'paired_TP_gains':tp_gains,'detections_at_floor':sum(map(len,preds.values()))}
            rows.append(row)
            if threshold==.5:
                np.savez_compressed(args.output/(name+'_NMS05_predictions.npz'),images=np.array(order),offsets=np.cumsum([0]+[len(preds[n]) for n in order]),detections=np.concatenate([preds[n] for n in order]))
    for name,values in [('threshold_sweep',rows),('paired_image_counts',paired)]:
        with (args.output/(name+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    evidence['checks']['real_prediction_reference_and_confidence_commutation']='500 images x 2 sources x 7 thresholds passed'
    evidence['evaluator_sha256']=sha(ROOT/'scripts/evaluation/detection_eval.py');evidence['script_sha256']=sha(__file__)
    dump(args.output/'audit.json',evidence);dump(args.output/'threshold_sweep.json',rows)
    for r in rows: print(r)
if __name__=='__main__':main()
