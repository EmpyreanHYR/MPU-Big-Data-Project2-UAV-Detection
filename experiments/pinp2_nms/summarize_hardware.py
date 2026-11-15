"""Verify every returned hardware run and summarize the three independent repeats."""
import argparse,csv,json,sys,statistics
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/pinp2_vlm'))
from common import sha,load_predictions,metrics,dump
from detection_eval import nms

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--annotations',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--offline-sweep',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False);ann=json.loads(a.annotations.read_text());ref=load_predictions(a.reference);offline=json.loads(a.offline_sweep.read_text());plan=json.loads((a.input/'tools/benchmark_plan.json').read_text());assert sha(a.reference)==plan['reference_sha256']
 assert json.loads((a.input/'results/queue_completed.json').read_text())['runs']==24
 sources=json.loads((a.input/'source_manifest.json').read_text());assert all(sha(a.input/k)==v for k,v in sources.items())
 rows=[];groups={}
 for rep,order in enumerate(plan['orders'],1):
  for threshold in order:
   d=a.input/'results'/f'nms{threshold}_r{rep}';receipt=json.loads((d/'completed.json').read_text());result=json.loads((d/'result.json').read_text());assert receipt['result_sha256']==sha(d/'result.json') and receipt['detections_sha256']==sha(d/'detections.npz')
   assert result['status']=='completed' and result['H10_used'] and result['fresh_predictions_equal_frozen'] and result['repeat']==rep and result['measured_runs']==500
   assert result['worker_sha256']==sha(a.input/'tools/h10_nms_worker.py') and result['plan_sha256']==sha(a.input/'tools/benchmark_plan.json')
   for key in ['hef_sha256','weights_sha256','validation_manifest_sha256','reference_sha256']:assert result[key]==plan[key]
   assert result['nms_iou_effective']==(None if threshold=='none' else threshold)
   assert 'HAILO10H' in (d/'device_identity.txt').read_text()
   pred=load_predictions(d/'detections.npz');assert set(pred)==set(ref)
   for name,v in ref.items():
    expected=v if threshold=='none' else v[nms(v[:,:4],v[:,4],threshold)]
    assert np.array_equal(pred[name],expected),(rep,threshold,name)
   recomputed=metrics(pred,ann);expected=next(x for x in offline if x['source']=='H10' and x['nms_iou']==threshold)
   for key in ['TP','FP','FN','mAP50_deployment','mAP50_95_deployment']:
    assert np.isclose(recomputed[key],result['metrics'][key],atol=1e-12,rtol=0),(rep,threshold,key)
    assert np.isclose(recomputed[key],expected[key],atol=1e-12,rtol=0),(rep,threshold,key,'offline')
   for key in ['pipeline_ms','inference_ms','NMS_ms']:
    values=np.asarray(result[key]);assert values.shape==(500,) and np.isfinite(values).all() and (values>=0).all()
   for prefix,arr in [('pipeline','pipeline_ms'),('inference','inference_ms'),('NMS','NMS_ms')]:
    assert np.isclose(np.mean(result[arr]),result[prefix+'_mean_ms'],atol=1e-10,rtol=0)
    assert np.isclose(np.percentile(result[arr],95),result[prefix+'_p95_ms'],atol=1e-10,rtol=0)
   row={'nms_iou':threshold,'repeat':rep,**{k:result[k] for k in ['pipeline_mean_ms','pipeline_p95_ms','pipeline_FPS','inference_mean_ms','NMS_mean_ms','NMS_p95_ms','peak_RSS_KiB']},**{k:recomputed[k] for k in ['TP','FP','FN','mAP50_95_deployment']},'temperature_before_C':result['before']['temperature_C'],'temperature_after_C':result['after']['temperature_C'],'throttled_before':result['before']['throttled'],'throttled_after':result['after']['throttled'],'cpu_governor':result['before']['cpu_governor']}
   rows.append(row);groups.setdefault(str(threshold),[]).append(row)
 summary=[]
 for threshold in ['none',.3,.4,.5,.6,.7,.8,.9]:
  runs=groups[str(threshold)];assert len(runs)==3;r={'nms_iou':threshold,'repeats':3,'images_per_repeat':500,**{k:runs[0][k] for k in ['TP','FP','FN','mAP50_95_deployment']}}
  for key in ['pipeline_mean_ms','pipeline_p95_ms','pipeline_FPS','inference_mean_ms','NMS_mean_ms','NMS_p95_ms','peak_RSS_KiB']:
   values=[x[key] for x in runs];r[key]=statistics.mean(values);r[key+'_SD']=statistics.stdev(values)
  r['maximum_temperature_C']=max(x['temperature_after_C'] for x in runs);r['all_throttled_flags_zero']=all(x[k]=='throttled=0x0' for x in runs for k in ['throttled_before','throttled_after']);summary.append(r)
 for filename,data in [('per_run',rows),('hardware_summary',summary)]:
  dump(a.output/(filename+'.json'),data)
  with (a.output/(filename+'.csv')).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 evidence={'status':'completed','actual_H10_runs':24,'actual_measured_images':12000,'warmup_device_calls':480,'returned_predictions_equal_offline_NMS':True,'all_metrics_recomputed_in_canonical_order':True,'source_hashes_and_return_receipts_verified':True,'evaluator_sha256':sha(ROOT/'scripts/evaluation/detection_eval.py'),'summary_convention':'Arithmetic mean and sample SD of three run-level summaries; P95 column is mean of each run P95, not pooled P95. FPS is mean of per-run1000/mean_ms.','timing_scope':plan['timing'],'comparison_scope':'All eight variants remeasured on same device; earlier22.72FPS is historical and is not reused. Differences in whole-pipeline means may reflect measurement variation; NMS stage measured directly.','all_throttled_flags_zero':all(x['all_throttled_flags_zero'] for x in summary),'script_sha256':sha(__file__)};dump(a.output/'verification.json',evidence)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
