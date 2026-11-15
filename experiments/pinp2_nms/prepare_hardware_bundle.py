"""Build a Pi-only worker from the preserved evaluator; preparation never runs inference."""
import argparse, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 src=(ROOT/'scripts/evaluation/h10_evaluate.py').read_text()
 src=src.replace('from detection_eval import sha,prepare,ground_truth,evaluate_records,summarize','from detection_eval import sha,prepare,ground_truth,evaluate_records,summarize,nms')
 src=src.replace("a=p.parse_args()", "p.add_argument('--nms-iou',type=float);p.add_argument('--repeat',type=int,required=True);p.add_argument('--reference',type=Path,required=True);a=p.parse_args();assert a.nms_iou is None or a.nms_iou in [.3,.4,.5,.6,.7,.8,.9];assert a.repeat in [1,2,3];assert len(a.additional_lock)>=1")
 src=src.replace('time.monotonic()+3600','time.monotonic()+300')
 src=src.replace("a.output.mkdir(parents=True,exist_ok=False)","z=np.load(a.reference,allow_pickle=False);reference={str(n):z['detections'][z['offsets'][i]:z['offsets'][i+1]] for i,n in enumerate(z['images'])};assert set(reference)=={r['image'] for r in manifest['images']};assert meta['family']=='e2e';a.output.mkdir(parents=True,exist_ok=False)")
 src=src.replace('infer_ms=[];pipeline_ms=[]','infer_ms=[];pipeline_ms=[];nms_ms=[]')
 src=src.replace('fixed=decode(raw,meta,geo,.25);pipeline_ms.append((time.perf_counter()-t)*1000)', 'fixed=decode(raw,meta,geo,.25);tn=time.perf_counter();fixed=fixed if a.nms_iou is None else fixed[nms(fixed[:,:4],fixed[:,4],a.nms_iou)];nms_ms.append((time.perf_counter()-tn)*1000);pipeline_ms.append((time.perf_counter()-t)*1000)')
 src=src.replace("det=decode(raw,meta,geo,.001);gt=", "det=decode(raw,meta,geo,.001);assert np.array_equal(det,reference[row['image']]),'Fresh H10 predictions differ from frozen reference';det=det if a.nms_iou is None else det[nms(det[:,:4],det[:,4],a.nms_iou)];assert np.array_equal(fixed,det[det[:,4]>=.25]);gt=")
 src=src.replace("'status':'completed','model_id'", "'status':'completed','nms_applied':a.nms_iou is not None,'nms_iou_effective':a.nms_iou,'repeat':a.repeat,'fresh_predictions_equal_frozen':True,'reference_sha256':sha(a.reference),'NMS_ms':nms_ms,'worker_sha256':sha(__file__),'model_id'")
 src=src.replace("[('inference',infer_ms),('pipeline',pipeline_ms)]", "[('inference',infer_ms),('pipeline',pipeline_ms),('NMS',nms_ms)]")
 src=src.replace("'temperature_C']=", "'temperature_C']=")
 src=src.replace("temp=Path('/sys/class/thermal/thermal_zone0/temp');", "result['throttled']=subprocess.check_output(['vcgencmd','get_throttled'],text=True,timeout=3).strip();temp=Path('/sys/class/thermal/thermal_zone0/temp');")
 (a.output/'h10_nms_worker.py').write_text(src)
 for name in ['detection_eval.py','raw_head_decode.py']:shutil.copy2(ROOT/'scripts/evaluation'/name,a.output/name)
 orders=[['none',.3,.4,.5,.6,.7,.8,.9],[.6,.7,.8,.9,'none',.3,.4,.5],[.9,.8,.7,.6,.5,.4,.3,'none']]
 (a.output/'benchmark_plan.json').write_text(json.dumps({'status':'prepared_not_run','orders':orders,'images_each':500,'warmups_each':20,'repeats':3,'input':640,'batch':1,'confidence':.25,'AP_floor':.001,'NMS_coordinates':'restored and clipped original image coordinates','timing':'Image read, PIL letterbox, UINT8 conversion, actual H10 call, finite checks, fixed-threshold decoder and NMS. AP-floor replay/verification/metrics excluded. NMS-only and full pipeline recorded separately.','comparison':'New no-NMS controls only; do not add Mac NMS latency to historical H10 latency. Report per-repeat mean/P95/FPS and temperature/throttling; no camera FPS.','guard':'GNU timeout 900s, TERM then KILL after20s, exact own spawned child only; no retry or fallback. Two existing shared hardware locks plus fuser device-idle check.','requirements':'Verify original HEF/metadata and data hashes, both existing lock paths, and Pi5/HAILO10H identity before launch.'},indent=2)+'\n')
 print(a.output)
if __name__=='__main__':main()
