#!/usr/bin/env python3
"""Pure-data, reproducible IR-UAV export. Does not import Torch or start training."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import struct
import zipfile

import numpy as np
from PIL import Image

SOURCES = {'SIRST-UAVB':'sirst', 'UAV-CB':'uavcb', 'Tri-Modal-Anti-UAV':'trimodal',
           'AUVD-seg300':'auvd', 'Anti-UAV-detection':'anti410'}
TEST = 'Anti-UAV-detection'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def dump(path, data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def write_csv(path, rows, fields=None):
    rows=list(rows)
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)


def read_boxes(path, dataset, w, h):
    raw=path.read_bytes();boxes=[];bird=[];original=[];adjustments=[]
    if dataset=='UAV-CB':
        obj=json.loads(raw)
        if (obj['imageWidth'],obj['imageHeight'])!=(w,h):raise ValueError('LabelMe image dimensions disagree')
        for shape in obj['shapes']:
            if shape['label']!='drone' or shape['shape_type']!='rectangle':raise ValueError('Unexpected LabelMe class/shape')
            pts=np.array(shape['points'],dtype=float)
            x0,y0=pts.min(0);x1,y1=pts.max(0)
            boxes.append([0,x0/w,y0/h,x1/w,y1/h]);original.append('drone')
        conversion='labelme_rectangle_to_yolo_bbox'
    else:
        conversion='polygon_to_enclosing_yolo_bbox' if dataset=='AUVD-seg300' else 'native_yolo_bbox'
        for line in raw.decode('utf-8-sig').splitlines():
            fields=line.split()
            if not fields:continue
            cls=fields[0];coords=list(map(float,fields[1:]));original.append(cls)
            if dataset=='AUVD-seg300':
                if cls not in {'0','1','2'} or len(coords)<6 or len(coords)%2:raise ValueError('Invalid UAV polygon')
                pts=np.array(coords).reshape(-1,2);x0,y0=pts.min(0);x1,y1=pts.max(0)
            else:
                if len(coords)!=4 or cls not in ({'0','1'} if dataset=='SIRST-UAVB' else {'0'}):raise ValueError('Invalid native YOLO box/class')
                cx,cy,bw,bh=coords;x0,y0,x1,y1=cx-bw/2,cy-bh/2,cx+bw/2,cy+bh/2
            box=[int(cls),float(x0),float(y0),float(x1),float(y1)]
            if dataset=='SIRST-UAVB' and cls=='1':bird.append(box)
            else:boxes.append([0,*box[1:]])
    for b in boxes+bird:
        if not all(math.isfinite(x) for x in b):raise ValueError('Nonfinite annotation')
        if not (b[1]<b[3] and b[2]<b[4]):raise ValueError('Zero-area or reversed box')
        excess=max(-b[1]*w,-b[2]*h,(b[3]-1)*w,(b[4]-1)*h,0.)
        if excess>2.01:raise ValueError('Box exceeds image boundary by more than 2 pixels')
        before=list(b)
        for j in range(1,5):b[j]=min(1.,max(0.,b[j]))
        if not (b[1]<b[3] and b[2]<b[4]):raise ValueError('Box has no visible area')
        if b!=before:adjustments.append({'before_xyxy':before,'after_xyxy':list(b),'max_excess_pixels':excess,'rule':'clip_to_visible_image_boundary_max_2_pixels'})
    return boxes,bird,original,conversion,adjustments


class Union:
    def __init__(self,n):self.p=list(range(n))
    def find(self,x):
        while self.p[x]!=x:self.p[x]=self.p[self.p[x]];x=self.p[x]
        return x
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.p[max(a,b)]=min(a,b)


def subset_options(groups, seed):
    rng=random.Random(seed);names=sorted(groups);rng.shuffle(names)
    possible={0:()}
    for name in names:
        n=len(groups[name])
        for total,selected in list(possible.items()):
            if total+n not in possible:possible[total+n]=selected+(name,)
    return possible


def choose_validation(rows, seed=42):
    """Exact global 80/20 without splitting inferred/source-prefix components."""
    bysource=defaultdict(lambda:defaultdict(list))
    for r in rows:bysource[r['dataset']][r['group']].append(r)
    target=round(len(rows)*.2);states={0:(0.,{})}
    for ds in sorted(bysource):
        groups=bysource[ds];n=sum(map(len,groups.values()));options=subset_options(groups,seed)
        # Keep the best achievable totals near each source's 20% quota.
        totals=sorted(options,key=lambda t:(abs(t-n*.2),t))[:160]
        nextstates={}
        for a,(cost,selected) in states.items():
            for b in totals:
                if a+b>target:continue
                candidate=(cost+((b-n*.2)/max(1,n))**2,selected|{ds:options[b]})
                if a+b not in nextstates or candidate[0]<nextstates[a+b][0]:nextstates[a+b]=candidate
        states=nextstates
    if target not in states:raise ValueError('Exact 8:2 is incompatible with intact groups; do not silently split groups')
    selected=states[target][1]
    for r in rows:r['split']='val' if r['group'] in selected[r['dataset']] else 'train'
    assert sum(r['split']=='val' for r in rows)==target


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-root',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--inventory',required=True);ap.add_argument('--legacy-groups');ap.add_argument('--seed',type=int,default=42)
    args=ap.parse_args();raw=Path(args.raw_root);out=Path(args.output)
    if out.exists() or out.with_suffix('.zip').exists():raise FileExistsError('Use a new export directory')
    out.mkdir(parents=True);prov=out/'provenance';prov.mkdir()
    inventory=json.loads(Path(args.inventory).read_text());dump(prov/'source_archive_inventory.json',inventory)
    legacy={}
    if args.legacy_groups:
        with Path(args.legacy_groups).open(encoding='utf-8-sig',newline='') as f:
            for x in csv.DictReader(f):legacy[Path(x['image']).stem]=x['group']
    rows=[];thumbnails=[];descriptors=[]
    for ds,code in SOURCES.items():
        base=raw/ds
        if ds=='SIRST-UAVB':images=sorted((base/'images/all').glob('*.jpg'))
        elif ds=='UAV-CB':images=sorted(base.glob('*/thermal/*.jpg'))
        elif ds=='Tri-Modal-Anti-UAV':images=sorted((base/'images').glob('ir_*.jpg'))
        elif ds=='AUVD-seg300':images=sorted(base.glob('*/images/*.png'))
        else:images=sorted(base.glob('*.jpg'))
        if not images:raise ValueError(f'No selected IR images: {ds}')
        for image in images:
            stem=image.stem;rel=image.relative_to(raw).as_posix()
            if ds=='SIRST-UAVB':
                matches=[p for p in (base/'labels').glob('*/'+stem+'.txt') if p.is_file()]
                if len(matches)!=1:raise ValueError(f'Ambiguous annotation for {rel}')
                annotation=matches[0]
            elif ds=='UAV-CB':annotation=image.with_suffix('.json')
            elif ds in {'Tri-Modal-Anti-UAV','AUVD-seg300'}:annotation=Path(str(image).replace('/images/','/labels/')).with_suffix('.txt')
            else:annotation=image.with_suffix('.txt')
            with Image.open(image) as im:
                im.load();w,h=im.size
                pixel=hashlib.sha256(struct.pack('>II',w,h)+im.convert('RGB').tobytes()).hexdigest()
                small=np.asarray(im.convert('L').resize((64,48),Image.Resampling.BILINEAR),dtype=np.float32)
                desc=np.asarray(im.convert('L').resize((16,12),Image.Resampling.BILINEAR),dtype=np.float32).ravel()
            centered=desc-desc.mean();norm=float(np.linalg.norm(centered));desc=centered/max(norm,1e-9)
            annotation_error=''
            try:boxes,bird,classes,conversion,adj=read_boxes(annotation,ds,w,h)
            except ValueError as error:
                annotation_error=str(error);boxes,bird,adj=[],[],[]
                classes=sorted({ln.split()[0] for ln in annotation.read_text().splitlines() if ln.strip()}) if annotation.suffix=='.txt' else ['unresolved']
                conversion='invalid_annotation_not_exported'

            ident=code+'__'+stem
            row={'dataset':ds,'sample_id':ident,'source_image':rel,'source_annotation':annotation.relative_to(raw).as_posix(),
                 'source_archive':inventory['datasets'][ds]['archive_name'],
                 'source_archive_sha256':inventory['datasets'][ds]['archive_sha256'],
                 'source_image_sha256':sha(image),'source_annotation_sha256':sha(annotation),
                 'pixel_sha256':pixel,'width':w,'height':h,'original_classes':','.join(sorted(set(classes))),
                 'annotation_conversion':conversion,'uav_instances':len(boxes),'bird_instances_excluded':len(bird),
                 'negative':int(not boxes) if not annotation_error else '', 'coordinate_clip_count':len(adj),'annotation_error':annotation_error,
                 'status':'quarantined' if annotation_error else 'pending','reason':'invalid_source_annotation' if annotation_error else '','split':'excluded',
                 'duplicate_of':'','group':'','group_basis':'','output_image':'','output_label':'',
                 '_boxes':boxes,'_bird':bird,'_corrections':adj,'_image':image,'_annotation':annotation,'_std':float(small.std())}
            row['_signature']=tuple(sorted(tuple(round(x,7) for x in b) for b in boxes+bird))
            rows.append(row);thumbnails.append(small);descriptors.append(desc)
        print('READ',ds,len(images),flush=True)
    # Quarantine whole exact-pixel groups with conflicting annotations.
    bypixel=defaultdict(list)
    for i,r in enumerate(rows):
        if r['status']=='pending':bypixel[r['pixel_sha256']].append(i)
    for ids in bypixel.values():
        tests=[i for i in ids if rows[i]['dataset']==TEST]
        signatures={rows[i]['_signature'] for i in ids}
        if len(signatures)>1 and not tests:
            for i in ids:rows[i].update(status='quarantined',reason='identical_pixels_conflicting_annotations')
            continue
        keep=min(tests or ids,key=lambda i:rows[i]['sample_id'])
        rows[keep]['status']='kept'
        for i in ids:
            if i==keep:continue
            rows[i].update(status='excluded',reason='exact_duplicate_of_test' if tests else 'exact_duplicate',duplicate_of=rows[keep]['sample_id'])
    desc=np.stack(descriptors);small=np.stack(thumbnails);uf=Union(len(rows));groupkeys={};near=[]
    for i,r in enumerate(rows):
        if r['status']!='kept':continue
        ds=r['dataset'];stem=r['_image'].stem
        if ds in {'UAV-CB','Tri-Modal-Anti-UAV'}:
            key=(ds,stem.rsplit('_',1)[0]);basis='filename_prefix_inferred_sequence_not_verified_video'
        elif ds=='SIRST-UAVB' and stem in legacy:
            key=(ds,legacy[stem]);basis='previously_reviewed_inferred_background_family_not_video_id'
        elif ds==TEST:
            key=(ds,stem.rsplit('_',1)[0]);basis='Anti-UAV410_sequence_name'
        else:key=(ds,r['sample_id']);basis='image_content_group_original_video_unknown'
        r['group_basis']=basis
        if key in groupkeys:uf.join(i,groupkeys[key])
        else:groupkeys[key]=i
    # Strong near-identical content joins within a source; test stays fixed.
    # This is an image-similarity screen, never a claim of verified video identity.
    kept=[i for i,r in enumerate(rows) if r['status']=='kept']
    for start in range(0,len(kept),256):
        batch=kept[start:start+256];scores=desc[batch]@desc[kept].T
        ii,jj=np.where(scores>=.995)
        for a,b in zip(ii.tolist(),jj.tolist()):
            i,j=batch[a],kept[b]
            if i>=j:continue
            x,y=rows[i],rows[j]
            if min(x['_std'],y['_std'])<4:continue
            if x['dataset']!=y['dataset'] and TEST not in {x['dataset'],y['dataset']}:continue
            mae=float(np.abs(small[i]-small[j]).mean())
            if mae>.5:continue
            cross_test=(x['dataset']==TEST)!=(y['dataset']==TEST)
            near.append({'sample_a':x['sample_id'],'sample_b':y['sample_id'],'ncc':float(scores[a,b]),'mae_64x48':mae,'cross_test':int(cross_test)})
            if x['dataset']==y['dataset']:uf.join(i,j)
    for i,r in enumerate(rows):
        if r['status']=='kept':r['group']=r['dataset']+'::component-'+str(uf.find(i))
    # Conservatively quarantine training components resembling external test frames.
    blocked=set()
    index={r['sample_id']:i for i,r in enumerate(rows)}
    for pair in near:
        if pair['cross_test']:
            i,j=index[pair['sample_a']],index[pair['sample_b']]
            train=j if rows[i]['dataset']==TEST else i;blocked.add(uf.find(train))
    for i,r in enumerate(rows):
        if r['status']=='kept' and r['dataset']!=TEST and uf.find(i) in blocked:
            r.update(status='quarantined',reason='inferred_near_identical_content_to_test_group')
    pool=[r for r in rows if r['status']=='kept' and r['dataset']!=TEST]
    print('CANDIDATES_AFTER_CONTENT_AUDIT',dict(Counter(r['dataset'] for r in pool)),flush=True)
    choose_validation(pool,args.seed)
    for r in rows:
        if r['status']=='kept' and r['dataset']==TEST:r['split']='test'
    for split in ['train','val','test']:
        for kind in ['images','labels']:(out/kind/split).mkdir(parents=True)
    instances=[]
    for r in rows:
        source_annotation=out/'original_annotations'/r['dataset']/Path(r['source_annotation']).relative_to(r['dataset'])
        source_annotation.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r['_annotation'],source_annotation)
        if r['status']=='kept':
            split=r['split'];r['output_image']=f"images/{split}/{r['sample_id']}{r['_image'].suffix.lower()}";r['output_label']=f"labels/{split}/{r['sample_id']}.txt"
            shutil.copyfile(r['_image'],out/r['output_image'])
            lines=[]
            for _,x0,y0,x1,y1 in r['_boxes']:lines.append(f'0 {(x0+x1)/2:.10f} {(y0+y1)/2:.10f} {x1-x0:.10f} {y1-y0:.10f}')
            (out/r['output_label']).write_text('\n'.join(lines)+('\n' if lines else ''))
            r['output_image_sha256']=sha(out/r['output_image']);r['output_label_sha256']=sha(out/r['output_label'])
        instances.append({'sample_id':r['sample_id'],'dataset':r['dataset'],'source_annotation':r['source_annotation'],'uav_boxes_xyxy_normalized':r['_boxes'],'bird_boxes_excluded_xyxy_normalized':r['_bird'],'annotation_corrections':r['_corrections'],'annotation_error':r['annotation_error'],'status':r['status']})
    public=[{k:v for k,v in r.items() if not k.startswith('_')} for r in rows]
    write_csv(prov/'manifest_all_selected_ir.csv',public)
    write_csv(prov/'manifest_exported.csv',[r for r in public if r['status']=='kept'])
    write_csv(prov/'excluded_and_quarantined.csv',[r for r in public if r['status']!='kept'])
    write_csv(prov/'near_identical_pairs.csv',near,['sample_a','sample_b','ncc','mae_64x48','cross_test'])
    with (prov/'instances.jsonl').open('w') as f:
        for r in instances:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    lookup={(r['dataset'],Path(r['source_image']).stem):r for r in public}
    allimages=[]
    for ds,info in inventory['datasets'].items():
        for member in info['image_members']:
            row=lookup.get((ds,Path(member).stem))
            modal=(('/thermal/' in member) if ds=='UAV-CB' else Path(member).name.startswith('ir_') if ds=='Tri-Modal-Anti-UAV' else True)
            entry={'dataset':ds,'original_archive':info['archive_name'],'original_archive_sha256':info['archive_sha256'],'original_image_member':member}
            if row and modal:
                canonical_member=info['archive_prefix']+str(Path(row['source_image']).relative_to(ds))
                annotation_member=info['archive_prefix']+str(Path(row['source_annotation']).relative_to(ds))
                entry.update(canonical_sample_id=row['sample_id'],original_annotation_member=annotation_member,
                             relationship_to_canonical='selected_original' if member==canonical_member else 'original_archive_image_copy',
                             split=row['split'],status=row['status'],reason=row['reason'],output_image=row['output_image'],output_label=row['output_label'])
            else:entry.update(canonical_sample_id='',split='excluded',status='excluded',reason='non_infrared_modality' if not modal else 'not_selected_image',output_image='',output_label='')
            allimages.append(entry)
    write_csv(prov/'original_image_to_split.csv',allimages)
    # Portable YAML: no server path is embedded; the YAML directory is the root.
    (out/'dataset.yaml').write_text('train: images/train\nval: images/val\ntest: images/test\nnc: 1\nnames:\n  0: uav\n')
    counts={}
    for ds in SOURCES:
        counts[ds]={sp:sum(r['dataset']==ds and r['split']==sp and r['status']=='kept' for r in rows) for sp in ['train','val','test']}
    totals={sp:sum(x[sp] for x in counts.values()) for sp in ['train','val','test']}
    group_splits=defaultdict(set);hash_splits=defaultdict(set)
    for r in rows:
        if r['status']=='kept':group_splits[r['group']].add(r['split']);hash_splits[r['pixel_sha256']].add(r['split'])
    assert all(len(s)==1 for s in group_splits.values());assert all(len(s)==1 for s in hash_splits.values())
    assert totals['val']==round((totals['train']+totals['val'])*.2)
    assert sum(r['dataset']==TEST for r in rows)==2050
    kept_near_cross=sum(pair['cross_test'] and rows[index[pair['sample_a']]]['status']=='kept' and rows[index[pair['sample_b']]]['status']=='kept' for pair in near)
    assert kept_near_cross==0
    audit={'seed':args.seed,'ratio_train_val':[8,2],'totals':totals,'by_source':counts,
           'status_counts':dict(Counter(r['status'] for r in rows)), 'exclusion_reasons':dict(Counter(r['reason'] for r in rows if r['status']!='kept')),
           'test_negative_images':sum(r['dataset']==TEST and r['status']=='kept' and r['negative']==1 for r in rows),
           'test_boxes':sum(r['uav_instances'] for r in rows if r['dataset']==TEST and r['status']=='kept'),
           'annotation_boundary_clips':sum(r['coordinate_clip_count'] for r in rows),'invalid_annotation_images':sum(bool(r['annotation_error']) for r in rows),
           'cross_split_exact_pixel_duplicates':0,'cross_split_export_group_overlap':0,'retained_strong_near_identical_test_overlap':kept_near_cross,
           'near_policy':{'descriptor':'16x12 centered normalized luminance','ncc':.995,'mae_64x48_max':.5,'std_min':4,'test_action':'quarantine entire affected training component'},
           'original_video_disjointness':'not fully verifiable: original video IDs absent for some sources; groups are explicitly inferred',
           'training_started':False,'software':{'numpy':np.__version__,'pillow':Image.__version__}}
    dump(prov/'audit.json',audit)
    table='\n'.join(f"| {ds} | {v['train']} | {v['val']} | {v['test']} |" for ds,v in counts.items())
    (out/'README_数据说明.md').write_text(f'''# 红外无人机单类检测数据集\n\n生成日期：2026-10-30；seed={args.seed}；类别 0=uav。训练尚未启动。\n\n| 原始数据集 | train | val | test |\n|---|---:|---:|---:|\n{table}\n| 合计 | {totals['train']} | {totals['val']} | {totals['test']} |\n\n四源 train/val 总体按 8:2 分配，保持已建立的来源/内容组完整。单个来源比例可能略偏离 8:2。Anti-UAV-detection 全部只用于 test；原包文件名中的 train/val/test 不代表本项目划分。IRSTD-1k 不进入本包。\n\n## 使用和溯源\n\n下载 ZIP 并完整解压，用本目录 dataset.yaml；不含固定服务器绝对路径。图像保留原字节与尺寸，不缩放、不增强。images 和 labels 下 train/val/test 一一对应，空 TXT 为无人机负样本。\n\nprovenance/original_image_to_split.csv：原始归档每一张图像的来源与最终去向，包括原包中的重复副本、非红外图像、排除项；UTF-8 BOM，可用 Excel 打开。provenance/manifest_exported.csv：实际导出样本逐图清单，包括原始文件、标注、输出文件、来源组、类别、框数、文件哈希。manifest_all_selected_ir.csv 保留全部 IR 候选；excluded_and_quarantined.csv 记录去重与冲突/近重复隔离原因；instances.jsonl 保存转换后的 UAV 框及被排除的鸟框。original_annotations 保存原标注，source_archive_inventory.json 保存原包名称、哈希及成员索引。\n\nSIRST 只保留 class0 UAV 框，class1 鸟框留作审计；鸟类负样本不删除。UAV-CB 仅 thermal，LabelMe rectangle 转框。Tri-Modal 仅 ir_，保留原生框。AUVD class0/1/2 均映射 uav，多边形转最小轴对齐外接框。测试保留 {audit['test_negative_images']} 张空标签负样本。\n\n## 划分和限制\n\n完全重复图像只保留一份；像素相同而框冲突的组全部隔离。强近相同图像按 audit.json 的固定规则检测；测试固定，隔离与 test 强近似的完整训练候选组。near_identical_pairs.csv 可复核。现有来源前缀、先前审阅背景组及内容相似组用于阻止组跨划分；部分原始视频身份未知，因此不能宣称已证明全部原始视频或地点独立。相似度规则不等于语义/视频身份鉴定。\n\n查看 provenance/audit.json 获取实际计数、软件版本、检测规则及限制。SHA256SUMS.txt 覆盖全部打包文件（自身除外），下载后可重新核验。原始数据使用条件仍随各原始数据集，不因本整理包改变。\n\n无效/零面积源标注图像隔离，不转为负样本；边界外延不超过 2 像素且仍有可见面积的框裁至图像边界，原框与修正后坐标记录在 instances.jsonl，逐图计数见 coordinate_clip_count。超过该界限的框不静默修复。\n''',encoding='utf-8')
    # Reparse every exported label and verify copied image bytes before packaging.
    for r in rows:
        if r['status']!='kept':continue
        assert r['output_image_sha256']==r['source_image_sha256']
        label=(out/r['output_label']).read_text().splitlines()
        assert len(label)==r['uav_instances']
        for line in label:
            cls,cx,cy,bw,bh=map(float,line.split())
            assert cls==0 and bw>0 and bh>0
            assert -1e-6<=cx-bw/2<cx+bw/2<=1+1e-6
            assert -1e-6<=cy-bh/2<cy+bh/2<=1+1e-6
    audit['exported_image_label_pairs_verified']=sum(totals.values())
    dump(prov/'audit.json',audit)
    files=sorted(p for p in out.rglob('*') if p.is_file())
    with (out/'SHA256SUMS.txt').open('w') as f:
        for p in files:f.write(f'{sha(p)}  {p.relative_to(out).as_posix()}\n')
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,(Path(out.name)/p.relative_to(out)).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archive.with_suffix('.zip.sha256').write_text(f'{sha(archive)}  {archive.name}\n')
    print('EXPORT_SUCCESS',json.dumps(audit,ensure_ascii=False),flush=True)
    print('DOWNLOAD_ZIP',archive,'BYTES',archive.stat().st_size,flush=True)


if __name__=='__main__':main()
