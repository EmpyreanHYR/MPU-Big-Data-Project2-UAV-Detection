"""Audit original dataset bytes/classes against frozen validation and analysis annotations."""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np
from common import dump,sha

def boxes(text,w,h):
    u=[];b=[]
    for line in text.splitlines():
        if not line.strip():continue
        c,x,y,bw,bh=map(float,line.split());assert c in [0,1]
        (u if c==0 else b).append([(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h])
    return [np.asarray(v,np.float32).reshape(-1,4) for v in [u,b]]
def main():
    p=argparse.ArgumentParser();p.add_argument('--original-zip',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();ann=json.loads((a.out/'annotations.json').read_text());prep=json.loads((a.out/'preparation.json').read_text())
    with zipfile.ZipFile(a.original_zip) as orig,zipfile.ZipFile(prep['images_zip_path']) as val:
        for r in ann:
            assert hashlib.sha256(orig.read(r['source_image_member'])).hexdigest()==r['image_sha256']
            u,b=boxes(orig.read(r['source_label_member']).decode(),r['width'],r['height']);vu,vb=boxes(val.read(r['label']).decode(),r['width'],r['height']);assert len(vb)==0
            for actual,expected in [(u,vu),(u,np.array(r['UAV_boxes'],np.float32).reshape(-1,4)),(b,np.array(r['bird_boxes'],np.float32).reshape(-1,4))]:assert actual.shape==expected.shape and np.allclose(actual,expected,atol=.002,rtol=0),r['image']
    receipt={'status':'passed','images':len(ann),'UAV_GT':sum(len(r['UAV_boxes']) for r in ann),'bird_GT':sum(len(r['bird_boxes']) for r in ann),'original_zip_sha256':sha(a.original_zip),'all_original_image_bytes_match_frozen_sha':True,'all_frozen_and_original_UAV_boxes_match_analysis_annotations':True,'all_original_bird_boxes_match':True,'coordinate_tolerance_pixels':.002}
    dump(a.out/'dataset_audit.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
