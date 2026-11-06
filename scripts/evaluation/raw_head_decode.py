"""NumPy decoding of verified pre-decoder head tensors; no model loading."""
import numpy as np
from detection_eval import postprocess

def sigmoid(x):return 1/(1+np.exp(-np.clip(x,-80,80)))
def decode(outputs,meta,geo,confidence=.25):
 family=meta['family'];strides=meta['strides'];parts=[]
 if family=='v5':
  for i,(raw,s) in enumerate(zip(outputs,strides)):
   raw=np.asarray(raw);raw=raw[0] if raw.ndim==4 else raw;na=meta['num_anchors'];h,w=raw.shape[1:];a=raw.reshape(na,6,h,w).transpose(0,2,3,1);v=sigmoid(a);yy,xx=np.meshgrid(np.arange(h),np.arange(w),indexing='ij');grid=np.stack([xx,yy],-1)[None];v[...,:2]=(v[...,:2]*2-.5+grid)*s;v[...,2:4]=(v[...,2:4]*2)**2*np.asarray(meta['anchors_pixels'][i])[:,None,None,:];parts.append(v.reshape(-1,6))
  return postprocess(np.concatenate(parts)[None],'v5',geo,confidence)
 boxes=[];scores=[]
 for i,s in enumerate(strides):
  b=np.asarray(outputs[2*i]);c=np.asarray(outputs[2*i+1]);b=b[0] if b.ndim==4 else b;c=c[0] if c.ndim==4 else c;h,w=b.shape[1:];reg=meta['reg_max'];b=b.reshape(4,reg,h*w)
  if reg>1:
   b=b-b.max(1,keepdims=True);e=np.exp(b);b=(e/e.sum(1,keepdims=True)*np.arange(reg)[None,:,None]).sum(1)
  else:b=b[:,0]
  yy,xx=np.meshgrid(np.arange(h)+.5,np.arange(w)+.5,indexing='ij');gx=xx.reshape(-1);gy=yy.reshape(-1);xyxy=np.stack([gx-b[0],gy-b[1],gx+b[2],gy+b[3]],1)*s;boxes.append(xyxy);scores.append(sigmoid(c.reshape(-1)))
 b=np.concatenate(boxes);score=np.concatenate(scores)
 if family=='e2e':
  order=np.argsort(-score,kind='stable')[:300];raw=np.concatenate([b[order],score[order,None],np.zeros((len(order),1))],1)[None];return postprocess(raw,'e2e',geo,confidence)
 xywh=np.concatenate([(b[:,:2]+b[:,2:])/2,b[:,2:]-b[:,:2]],1);raw=np.concatenate([xywh,score[:,None]],1).T[None];return postprocess(raw,'v8',geo,confidence)
