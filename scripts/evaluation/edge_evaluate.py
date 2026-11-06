#!/usr/bin/env python3
"""Pi-only CPU ONNX full-validation inference. Never imports Torch."""
import argparse,fcntl,json,time,statistics,sys,platform,resource
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import onnxruntime as ort
from detection_eval import sha,prepare,postprocess,ground_truth,evaluate_records,summarize

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True,type=Path);p.add_argument('--data',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--threads',type=int,default=4);p.add_argument('--shared-lock',type=Path,required=True);args=p.parse_args()
 assert platform.machine()=='aarch64';device=Path('/proc/device-tree/model').read_text().strip('\0');assert 'Raspberry Pi 5' in device
 cfg=json.loads(args.config.read_text());model=args.config.parent/cfg['onnx_file'];assert sha(model)==cfg['onnx_sha256'];manifest=json.loads((args.data/'validation_manifest.json').read_text());assert len(manifest['images'])==500
 for row in manifest['images']:
  assert sha(args.data/row['image'])==row['image_sha256'] and sha(args.data/row['label'])==row['label_sha256']
 hardware_lock=args.shared_lock.open('a');fcntl.flock(hardware_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 args.output.mkdir(parents=True,exist_ok=False)
 opts=ort.SessionOptions();opts.intra_op_num_threads=args.threads;opts.inter_op_num_threads=1
 t=time.perf_counter();session=ort.InferenceSession(str(model),sess_options=opts,providers=['CPUExecutionProvider']);initialization=time.perf_counter()-t
 sample=Image.open(args.data/manifest['images'][0]['image']);x,_=prepare(sample)
 for _ in range(20):session.run(None,{'images':x})
 infer_ms=[];pipeline_ms=[];records=[];summary_samples=[];all_preds=[];offsets=[0];started=time.perf_counter()
 for i,row in enumerate(manifest['images']):
  t=time.perf_counter();image=Image.open(args.data/row['image']).convert('RGB');x,geo=prepare(image);a=time.perf_counter();raw=session.run(None,{'images':x})[0];infer_ms.append((time.perf_counter()-a)*1000);assert np.isfinite(raw).all(), 'Non-finite ONNX output';det=postprocess(raw,cfg['family'],geo,.25);pipeline_ms.append((time.perf_counter()-t)*1000)
  # Low-confidence AP processing is outside deployment-latency timing.
  ap_det=postprocess(raw,cfg['family'],geo,.001);fixed=ap_det[ap_det[:,4]>=.25];assert fixed.shape==det.shape and np.allclose(fixed,det,rtol=1e-5,atol=1e-3)
  gt=ground_truth(args.data/row['label'],image.width,image.height);record=evaluate_records(ap_det,gt);records.append(record);all_preds.append(ap_det);offsets.append(offsets[-1]+len(ap_det))
  summary_samples.append({'image':row['image'],'TP':int(record['correct_fixed'][:,0].sum()),'GT':len(gt),'predictions':len(det)})
  if i in (0,149,299,499):
   draw=ImageDraw.Draw(image)
   for box in gt:draw.rectangle(box.tolist(),outline=(0,255,80),width=1)
   for box in det:draw.rectangle(box[:4].tolist(),outline=(255,50,50),width=1)
   image.save(args.output/f'sample_{i:03}.jpg')
  if i%50==0:print('EDGE_PROGRESS',cfg['model_id'],i+1,'/500',flush=True)
 metrics=summarize(records);assert metrics['GT']==486
 temp=Path('/sys/class/thermal/thermal_zone0/temp');result={'status':'completed','model_id':cfg['model_id'],'weights_sha256':cfg['weights_sha256'],'onnx_sha256':sha(model),'validation_manifest_sha256':sha(args.data/'validation_manifest.json'),'device':device,'runtime':ort.__version__,'providers':session.get_providers(),'precision':'FP32','input':640,'batch':1,'threads':args.threads,'warmup':20,'measured_runs':500,'initialization_seconds':initialization,'inference_mean_ms':statistics.mean(infer_ms),'inference_p50_ms':float(np.percentile(infer_ms,50)),'inference_p95_ms':float(np.percentile(infer_ms,95)),'inference_FPS':1000/statistics.mean(infer_ms),'pipeline_mean_ms':statistics.mean(pipeline_ms),'pipeline_p50_ms':float(np.percentile(pipeline_ms,50)),'pipeline_p95_ms':float(np.percentile(pipeline_ms,95)),'pipeline_FPS':1000/statistics.mean(pipeline_ms),'evaluation_wall_seconds':time.perf_counter()-started,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'temperature_C':int(temp.read_text())/1000 if temp.exists() else None,'timing_scope':'warm file-cache JPEG read/PIL RGB-letterbox114/normalize/ORT CPU/filter-or-NMS/coordinate restoration; excludes integrity audit, init, AP-floor postprocessing, drawing, encoding, network; not camera FPS','H10_used':False,'metrics':metrics,'per_image':summary_samples,'inference_ms':infer_ms,'pipeline_ms':pipeline_ms}
 np.savez_compressed(args.output/'detections.npz',detections=np.concatenate(all_preds),offsets=np.asarray(offsets),images=np.asarray([x['image'] for x in manifest['images']]))
 (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(args.output/'completed.json').write_text(json.dumps({'status':'completed','model_id':cfg['model_id'],'images':500,'metrics':metrics,'result_sha256':sha(args.output/'result.json'),'detections_sha256':sha(args.output/'detections.npz')},indent=2)+'\n');print('EDGE_COMPLETED',cfg['model_id'],metrics,flush=True)
if __name__=='__main__':main()
