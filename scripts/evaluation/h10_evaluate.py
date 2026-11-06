"""Pi5/Hailo10H-only, actual 500-image inference; no CPU model fallback."""
import argparse,fcntl,json,platform,resource,statistics,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from hailo_platform import VDevice,FormatType,HEF
from detection_eval import sha,prepare,ground_truth,evaluate_records,summarize
from raw_head_decode import decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--shared-lock',type=Path,required=True);p.add_argument('--additional-lock',type=Path,action='append',default=[]);a=p.parse_args()
 assert platform.machine()=='aarch64' and 'Raspberry Pi 5' in Path('/proc/device-tree/model').read_text()
 locks=[]
 for path in [a.shared_lock,*a.additional_lock]:
  h=path.open('a');end=time.monotonic()+3600
  while True:
   try:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);break
   except BlockingIOError:assert time.monotonic()<end,'Hardware owner did not release lock';time.sleep(15)
  locks.append(h)
 identity=subprocess.check_output(['hailortcli','fw-control','identify'],text=True,stderr=subprocess.STDOUT);assert 'HAILO10H' in identity,identity
 busy=subprocess.run(['fuser','/dev/hailo0'],capture_output=True,text=True);assert busy.returncode==1,'Hailo device already in use; preserve other workloads'
 meta=json.loads((a.model_dir/'h10_metadata.json').read_text());hef=a.model_dir/'model.hef';assert sha(hef)==meta['hef_sha256'];manifest=json.loads((a.data/'validation_manifest.json').read_text());assert len(manifest['images'])==500 and manifest['GT']==486
 for row in manifest['images']:
  assert sha(a.data/row['image'])==row['image_sha256'] and sha(a.data/row['label'])==row['label_sha256']
 a.output.mkdir(parents=True,exist_ok=False);(a.output/'device_identity.txt').write_text(identity)
 def pixels(im):
  x,geo=prepare(im);return np.ascontiguousarray(np.rint(x[0].transpose(1,2,0)*255).astype(np.uint8)),geo
 init=time.perf_counter();raw_infos=HEF(str(hef)).get_output_vstream_infos();mapping=[];used=set()
 for expected in meta['output_shapes']:
  assert expected[0]==1;want=(expected[2],expected[3],expected[1]);matches=[x.name for x in raw_infos if tuple(x.shape)==want and x.name not in used];assert len(matches)==1,('ambiguous HEF output mapping',expected,matches);mapping.append(matches[0]);used.add(matches[0])
 assert len(used)==len(raw_infos)==len(meta['output_names']);infer_ms=[];pipeline_ms=[];preds=[];offsets=[0];records=[];per_image=[]
 with VDevice() as dev:
  infer=dev.create_infer_model(str(hef));infer.set_batch_size(1);infer.input().set_format_type(FormatType.UINT8);assert tuple(infer.input().shape)==(640,640,3)
  for name in mapping:infer.output(name).set_format_type(FormatType.FLOAT32)
  with infer.configure() as configured:
   buffers={name:np.empty(infer.output(name).shape,dtype=np.float32) for name in mapping};bindings=configured.create_bindings(output_buffers=buffers)
   def run(x):
    bindings.input().set_buffer(x);configured.run([bindings],timeout=10000)
    return [np.asarray(bindings.output(name).get_buffer()).transpose(2,0,1)[None] for name in mapping]
   x,_=pixels(Image.open(a.data/manifest['images'][0]['image']).convert('RGB'))
   for _ in range(20):run(x)
   init=time.perf_counter()-init;started=time.perf_counter()
   for i,row in enumerate(manifest['images']):
    t=time.perf_counter();image=Image.open(a.data/row['image']).convert('RGB');x,geo=pixels(image);tick=time.perf_counter();raw=run(x);infer_ms.append((time.perf_counter()-tick)*1000);assert all(np.isfinite(v).all() for v in raw),'Non-finite device output';fixed=decode(raw,meta,geo,.25);pipeline_ms.append((time.perf_counter()-t)*1000)
    det=decode(raw,meta,geo,.001);gt=ground_truth(a.data/row['label'],image.width,image.height);record=evaluate_records(det,gt);records.append(record);preds.append(det.copy());offsets.append(offsets[-1]+len(det));tp=int(record['correct_fixed'][:,0].sum());per_image.append({'image':row['image'],'TP':tp,'FP':len(fixed)-tp,'FN':len(gt)-tp,'GT':len(gt)})
    if i in [0,149,299,499]:
     draw=ImageDraw.Draw(image)
     for box in gt:draw.rectangle(box.tolist(),outline=(0,255,80),width=1)
     for box in fixed:draw.rectangle(box[:4].tolist(),outline=(255,50,50),width=1)
     image.save(a.output/f'sample_{i:03}.jpg')
    if i%50==0:print('H10_PROGRESS',meta['model_id'],i+1,'/500',flush=True)
 metrics=summarize(records);assert metrics['GT']==486;result={'status':'completed','model_id':meta['model_id'],'weights_sha256':meta['weights_sha256'],'raw_onnx_sha256':meta['raw_onnx_sha256'],'hef_sha256':sha(hef),'validation_manifest_sha256':sha(a.data/'validation_manifest.json'),'device':'Raspberry Pi5 + HAILO10H','runtime':__import__('hailo_platform').__version__,'H10_used':True,'precision':meta['quantization'],'warmup':20,'measured_runs':500,'batch':1,'input':640,'initialization_seconds':init,'metrics':metrics,'output_mapping':dict(zip(meta['output_names'],mapping)),'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'evaluation_wall_seconds':time.perf_counter()-started,'per_image':per_image,'inference_ms':infer_ms,'pipeline_ms':pipeline_ms,'timing_scope':'Synchronous HailoRT device call includes PCIe transfer/dequantization and tensor view creation; pipeline includes JPEG/PIL letterbox/uint8 formatting/NPU call/NumPy host decoder/NMS/coordinate restoration. Excludes calibration, initialization, AP-floor scoring, drawing, encoding and network; not camera FPS'}
 for prefix,values in [('inference',infer_ms),('pipeline',pipeline_ms)]:
  result.update({prefix+'_mean_ms':statistics.mean(values),prefix+'_p50_ms':float(np.percentile(values,50)),prefix+'_p95_ms':float(np.percentile(values,95)),prefix+'_FPS':1000/statistics.mean(values)})
 temp=Path('/sys/class/thermal/thermal_zone0/temp');result['temperature_C']=int(temp.read_text())/1000 if temp.exists() else None
 np.savez_compressed(a.output/'detections.npz',detections=np.concatenate(preds),offsets=np.asarray(offsets),images=np.asarray([r['image'] for r in manifest['images']]))
 (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');(a.output/'completed.json').write_text(json.dumps({'status':'completed','model_id':meta['model_id'],'H10_used':True,'images':500,'result_sha256':sha(a.output/'result.json'),'detections_sha256':sha(a.output/'detections.npz'),'hef_sha256':sha(hef)},indent=2)+'\n');print('H10_COMPLETED',meta['model_id'],metrics,flush=True)

if __name__=='__main__':main()
