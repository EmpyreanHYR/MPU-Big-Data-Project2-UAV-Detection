"""Post-hoc diagnostics only: no inference, no overwrite of the frozen E0--E4 outputs."""
import collections,csv,json
from pathlib import Path
import numpy as np
from common import HERE,load_predictions,metrics,match,iou,sha,dump
from detection_eval import nms

def main():
 src=HERE/'outputs';out=HERE/'diagnostics_20261115';out.mkdir(exist_ok=False)
 pred=load_predictions(src/'source_predictions.npz');ann=json.loads((src/'annotations.json').read_text());cs=[json.loads(s) for s in (src/'candidates.jsonl').read_text().splitlines()];rs={(r['candidate_id'],r['crop_mode']):r for r in map(json.loads,(src/'vlm_responses.jsonl').read_text().splitlines())};ds=list(csv.DictReader((src/'candidate_decisions.csv').open()));cmap={c['candidate_id']:c for c in cs}
 confusion={g:dict(collections.Counter(r['baseline_identity']+'->'+r['vlm_label'] for r in ds if r['experiment']==g and r['queried']=='True')) for g in ['E2','E3','E4']}
 selected=[c for c in cs if c['selected']];areas={m:float(np.median([(c['bbox_xyxy'][2]-c['bbox_xyxy'][0])*(c['bbox_xyxy'][3]-c['bbox_xyxy'][1])/np.prod(c['crops'][m]['native_size']) for c in selected])) for m in ['context','local']}
 fp_details=[]
 for a in ann:
  ps=pred[a['image']];ids=np.flatnonzero(ps[:,4]>=.25);v=ps[ids];gt=np.array(a['UAV_boxes'],np.float32).reshape(-1,4);ok=match(v,gt)[:,0];mat=iou(v[:,:4],gt);covered=(mat[ok]>=.5).any(0)
  for j in np.flatnonzero(~ok):
   maximum=float(mat[j].max()) if len(gt) else 0.;covered_overlap=bool(((mat[j]>=.5)&covered).any())
   fp_details.append({'image_id':a['image'],'box_id':int(ids[j]),'max_iou_UAV':maximum,'overlaps_UAV_also_covered_by_TP':covered_overlap,'category':'IoU>=.5 matching conflict' if maximum>=.5 else '.1<=IoU<.5' if maximum>=.1 else 'IoU<.1'})
 summaries=[]
 def record(name,ps):
  m=metrics(ps,ann);summaries.append({'diagnostic':name,**{k:m[k] for k in ['TP','FP','FN','Precision_fixed','Recall_fixed','F1_fixed','mAP50_deployment','mAP50_95_deployment','bird_associated_FP']}})
 record('original_E0',pred)
 for mode in ['BIRD_only','both_negative','both_BIRD']:
  remove=collections.defaultdict(set)
  for c in selected:
   x=rs[c['candidate_id'],'context']['vlm_label'];y=rs[c['candidate_id'],'local']['vlm_label'];reject=x=='BIRD' if mode=='BIRD_only' else x in {'BIRD','BACKGROUND'} and y in {'BIRD','BACKGROUND'} if mode=='both_negative' else x==y=='BIRD'
   if reject:remove[c['image_id']].add(c['box_id'])
  ps={n:np.array([v for j,v in enumerate(vs) if j not in remove[n]],np.float32).reshape(-1,6) for n,vs in pred.items()};record(mode,ps)
 for threshold in [.5,.7]:
  ps={n:vs[nms(vs[:,:4],vs[:,4],threshold=threshold)] for n,vs in pred.items()};record(f'NMS_IoU_{threshold}',ps)
  if threshold==.5:
   order=[a['image'] for a in ann];np.savez_compressed(out/'posthoc_NMS05_predictions.npz',images=np.array(order),offsets=np.cumsum([0]+[len(ps[n]) for n in order]),detections=np.concatenate([ps[n] for n in order]))
 for name,rows in [('posthoc_metrics',summaries),('fp_overlap_diagnosis',fp_details)]:
  with (out/(name+'.csv')).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 evidence={'status':'posthoc exploratory diagnostics; not independent validation or a modification to E0--E4','confusion':confusion,'median_candidate_max_side_px':float(np.median([max(c['bbox_xyxy'][2]-c['bbox_xyxy'][0],c['bbox_xyxy'][3]-c['bbox_xyxy'][1]) for c in selected])),'median_candidate_area_fraction':areas,'FP_categories':dict(collections.Counter(r['category'] for r in fp_details)),'FP_overlapping_GT_also_covered_by_TP':sum(r['overlaps_UAV_also_covered_by_TP'] for r in fp_details),'prediction_source_sha256':sha(src/'source_predictions.npz'),'responses_sha256':sha(src/'vlm_responses.jsonl'),'no_GPU_inference':True,'NMS_protocol':'saved original-image-coordinate full 0.001-floor predictions; original NumPy greedy NMS, same scores, max_det300; original matcher, frozen annotation order; operating confidence0.25','remaining_gaps':['semantic positive controls','image-null/shuffle controls','FP16 numerical comparison','independent held-out confirmation','Pi/H10 timing measurement']}
 dump(out/'diagnosis.json',evidence);print(json.dumps({'evidence':evidence,'metrics':summaries},indent=2))
if __name__=='__main__':main()
