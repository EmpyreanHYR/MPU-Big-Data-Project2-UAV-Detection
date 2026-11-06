"""Shared NumPy-only postprocessing and object-level detection metrics."""
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image

IOU_THRESHOLDS=np.linspace(.5,.95,10)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(image,size=640):
 image=image.convert('RGB');w,h=image.size;r=min(size/w,size/h);nw,nh=round(w*r),round(h*r);left,top=(size-nw)//2,(size-nh)//2
 canvas=Image.new('RGB',(size,size),(114,114,114));canvas.paste(image.resize((nw,nh),Image.Resampling.BILINEAR),(left,top))
 return np.ascontiguousarray(np.asarray(canvas,dtype=np.float32).transpose(2,0,1)[None]/np.float32(255)),(r,left,top,w,h)
def xywh2xyxy(a):
 b=np.array(a,copy=True);b[...,:2]=a[...,:2]-a[...,2:4]/2;b[...,2:4]=a[...,:2]+a[...,2:4]/2;return b
def iou(a,b):
 a=np.asarray(a).reshape(-1,4);b=np.asarray(b).reshape(-1,4)
 intersection=np.maximum(0,np.minimum(a[:,None,2:],b[None,:,2:])-np.maximum(a[:,None,:2],b[None,:,:2])).prod(2)
 area_a=np.maximum(0,a[:,2:]-a[:,:2]).prod(1);area_b=np.maximum(0,b[:,2:]-b[:,:2]).prod(1)
 return intersection/(area_a[:,None]+area_b[None,:]-intersection+1e-7)
def nms(boxes,scores,threshold=.7,max_det=300):
 order=np.argsort(-scores,kind='stable')[:30000];keep=[]
 while len(order) and len(keep)<max_det:
  index=order[0];keep.append(index)
  if len(order)==1:break
  rest=order[1:];order=rest[iou(boxes[index:index+1],boxes[rest])[0]<=threshold]
 return np.asarray(keep,dtype=int)
def postprocess(raw,family,geometry,confidence=.25,nms_iou=.7,max_det=300):
 raw=np.asarray(raw);raw=raw[0] if raw.ndim==3 else raw
 if family=='e2e':
  assert raw.shape[1]==6,raw.shape;boxes=raw[:,:4];scores=raw[:,4];classes=raw[:,5];assert not np.any((scores>=confidence)&(classes!=0))
 elif family=='v8':
  assert raw.shape[0]==5,raw.shape;raw=raw.T;boxes=xywh2xyxy(raw[:,:4]);scores=raw[:,4]
 elif family=='v5':
  assert raw.shape[1]==6,raw.shape;boxes=xywh2xyxy(raw[:,:4]);scores=raw[:,4]*raw[:,5]
 elif family=='rtdetr':
  assert raw.shape[1] in (5,6),raw.shape
  if raw.shape[1]==6:assert not np.any((raw[:,4]>=confidence)&(raw[:,5]!=0))
  boxes=xywh2xyxy(raw[:,:4])*640;scores=raw[:,4]
 else:raise ValueError(family)
 mask=(scores>=confidence)&np.isfinite(scores)&np.isfinite(boxes).all(1);boxes=boxes[mask];scores=scores[mask]
 if family in ('v8','v5'):indices=nms(boxes,scores,nms_iou,max_det)
 else:indices=np.argsort(-scores,kind='stable')[:max_det]
 boxes=boxes[indices].copy();scores=scores[indices];r,left,top,w,h=geometry
 boxes[:,[0,2]]=((boxes[:,[0,2]]-left)/r).clip(0,w);boxes[:,[1,3]]=((boxes[:,[1,3]]-top)/r).clip(0,h)
 valid=(boxes[:,2]>boxes[:,0])&(boxes[:,3]>boxes[:,1]);boxes=boxes[valid];scores=scores[valid]
 return np.concatenate([boxes,scores[:,None],np.zeros((len(scores),1),dtype=boxes.dtype)],axis=1).astype(np.float32)
def ground_truth(label,w,h):
 rows=[]
 for line in Path(label).read_text().splitlines():
  if not line.strip():continue
  c,x,y,bw,bh=map(float,line.split());assert c==0 and bw>0 and bh>0
  rows.append([x*w,y*h,bw*w,bh*h])
 return xywh2xyxy(np.asarray(rows,dtype=np.float32).reshape(-1,4))
def match(predictions,gt):
 correct=np.zeros((len(predictions),10),dtype=bool)
 if not len(predictions) or not len(gt):return correct
 matrix=iou(gt,predictions[:,:4])
 # Same IoU-first unique detection/GT convention as native YOLO validators.
 for t,threshold in enumerate(IOU_THRESHOLDS):
  gi,di=np.where(matrix>=threshold)
  if not len(gi):continue
  pairs=np.column_stack((gi,di,matrix[gi,di]));pairs=pairs[np.argsort(-pairs[:,2],kind='stable')]
  pairs=pairs[np.unique(pairs[:,1],return_index=True)[1]];pairs=pairs[np.argsort(-pairs[:,2],kind='stable')];pairs=pairs[np.unique(pairs[:,0],return_index=True)[1]]
  correct[pairs[:,1].astype(int),t]=True
 return correct
def compute_ap(recall,precision):
 mrec=np.concatenate(([0.],recall,[1.]));mpre=np.concatenate(([1.],precision,[0.]));mpre=np.flip(np.maximum.accumulate(np.flip(mpre)));x=np.linspace(0,1,101)
 integrate=np.trapezoid if hasattr(np,"trapezoid") else np.trapz
 return float(integrate(np.interp(x,mrec,mpre),x))
def summarize(records,confidence=.25):
 total_gt=sum(x['gt_count'] for x in records);assert total_gt>0
 scores=np.concatenate([x['scores'] for x in records]);correct=np.concatenate([x['correct'] for x in records],axis=0)
 order=np.argsort(-scores,kind='stable');scores=scores[order];correct=correct[order];chosen=scores>=confidence
 tp=sum(int(x['correct_fixed'][:,0].sum()) for x in records);fp=int(chosen.sum()-tp);fn=total_gt-tp;P=tp/(tp+fp) if tp+fp else 0;R=tp/total_gt
 if len(scores):
  tp_curve=correct.cumsum(0);fp_curve=(~correct).cumsum(0);recall=tp_curve/total_gt;precision=tp_curve/np.maximum(tp_curve+fp_curve,1);aps=[compute_ap(recall[:,i],precision[:,i]) for i in range(10)]
 else:aps=[0.]*10
 negative=[x for x in records if x['gt_count']==0];negative_fp=sum(int((x['scores']>=confidence).sum()) for x in negative)
 return {'images':len(records),'GT':total_gt,'TP':tp,'FP':fp,'FN':fn,'miss_rate':fn/total_gt,'Precision_fixed':P,'Recall_fixed':R,'F1_fixed':2*P*R/(P+R) if P+R else 0.,'mAP50_deployment':aps[0],'mAP50_95_deployment':float(np.mean(aps)),'AP_by_IoU':aps,'FP_per_image':fp/len(records),'negative_images':len(negative),'negative_images_with_FP':sum(bool((x['scores']>=confidence).any()) for x in negative),'negative_FP_count':negative_fp,'confidence':confidence,'match_IoU':.5,'AP_confidence_floor':.001,'fixed_matching':'filter conf0.25 first, then independent one-to-one GT matching','matching':'IoU-first one-to-one; 10 IoUs .50:.05:.95; 101-point precision-envelope trapezoid AP'}
def evaluate_records(predictions,gt):return {'gt_count':len(gt),'scores':predictions[:,4].copy(),'correct':match(predictions,gt),'correct_fixed':match(predictions[predictions[:,4]>=.25],gt)}
