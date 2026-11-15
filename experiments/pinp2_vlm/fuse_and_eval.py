"""Fixed-protocol E0--E4 evaluation using the unmodified repository evaluator."""
import argparse, collections, csv, json, random, time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from common import dump,sha,read_jsonl,write_jsonl,load_predictions,metrics,match

def csvwrite(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def fixed_metrics(pred,ann,threshold):
    tp=fp=gt_count=0
    for a in ann:
        p=pred[a['image']];p=p[p[:,4].astype(float)>=threshold];gt=np.asarray(a['UAV_boxes'],np.float32).reshape(-1,4)
        t=int(match(p,gt)[:,0].sum());tp+=t;fp+=len(p)-t;gt_count+=len(gt)
    precision=tp/(tp+fp) if tp+fp else 0;recall=tp/gt_count
    return {'threshold':threshold,'TP':tp,'FP':fp,'FN':gt_count-tp,'Precision':precision,'Recall':recall,'F1':2*precision*recall/(precision+recall) if precision+recall else 0,'FP_per_image':fp/len(ann)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out;start=time.perf_counter()
    ann=json.loads((out/'annotations.json').read_text());pred=load_predictions(out/'source_predictions.npz');candidates=read_jsonl(out/'candidates.jsonl');responses=read_jsonl(out/'vlm_responses.jsonl')
    lookup={(r['candidate_id'],r['crop_mode']):r for r in responses};assert len(lookup)==len(responses)==len(candidates)+sum(c['selected'] for c in candidates)
    for c in candidates:
        for mode in ['context']+(['local'] if c['selected'] else []):assert lookup[c['candidate_id'],mode]['crop_sha256']==c['crops'][mode]['sha256']
    byann={a['image']:a for a in ann};baseline_identity={}
    for n,p in pred.items():
        indices=np.flatnonzero(p[:,4]>=.25);gt=np.asarray(byann[n]['UAV_boxes'],np.float32).reshape(-1,4);ok=match(p[indices],gt)[:,0]
        for j,k in zip(indices,ok):baseline_identity[n,int(j)]=bool(k)
    results=[];details=[];full_metrics={};fused_all=[]
    for group,mode,selective in [('E0',None,False),('E2','context',False),('E3','context',True),('E4','local',True)]:
        remove=collections.defaultdict(set);queried=[];deleted_tp=deleted_fp=0
        for c in candidates:
            query=mode is not None and (not selective or c['selected']);r=lookup[c['candidate_id'],mode] if query else None
            reject=query and r['vlm_label'] in {'BIRD','BACKGROUND'}
            if query:queried.append(r)
            if reject:
                remove[c['image_id']].add(c['box_id']);tp=baseline_identity[c['image_id'],c['box_id']];deleted_tp+=tp;deleted_fp+=not tp
            if group!='E0':details.append({'experiment':group,'candidate_id':c['candidate_id'],'image_id':c['image_id'],'box_id':c['box_id'],'score':c['score'],'queried':query,'vlm_label':r['vlm_label'] if r else 'NOT_QUERIED','baseline_identity':'TP' if baseline_identity[c['image_id'],c['box_id']] else 'FP','removed':reject})
        fused={n:np.asarray([p for j,p in enumerate(ps) if j not in remove[n]],dtype=np.float32).reshape(-1,6) for n,ps in pred.items()}
        met=metrics(fused,ann);full_metrics[group]=met
        final_identity={}
        for name,ps in pred.items():
            ids=[j for j,p in enumerate(ps) if j not in remove[name] and p[4]>=.25]
            gt=np.asarray(byann[name]['UAV_boxes'],np.float32).reshape(-1,4)
            ok=match(ps[ids],gt)[:,0]
            for j,t in zip(ids,ok):final_identity[name,j]=bool(t)
        fp_to_tp=sum(not baseline_identity[k] and v for k,v in final_identity.items())
        tp_to_fp=sum(baseline_identity[k] and not v for k,v in final_identity.items())
        for row in details:
            if row['experiment']==group:row['final_identity']='REMOVED' if row['removed'] else ('TP' if final_identity[row['image_id'],row['box_id']] else 'FP')
        assert met['TP']==323-deleted_tp+fp_to_tp-tp_to_fp
        assert met['FP']==119-deleted_fp-fp_to_tp+tp_to_fp
        lat=[r['latency_ms'] for r in queried];counts=collections.Counter(r['vlm_label'] for r in queried)
        results.append({'experiment':group,'TP':met['TP'],'FP':met['FP'],'FN':met['FN'],'Precision':met['Precision_fixed'],'Recall':met['Recall_fixed'],'F1':met['F1_fixed'],'miss_rate':met['miss_rate'],'FP_per_image':met['FP_per_image'],'AP50':met['mAP50_deployment'],'AP50_95':met['mAP50_95_deployment'],'removed_FP_original':deleted_fp,'removed_TP_original':deleted_tp,'net_FP_reduction':119-met['FP'],'FN_increase':met['FN']-163,'rematched_FP_to_TP':fp_to_tp,'rematched_TP_to_FP':tp_to_fp,'bird_associated_FP':met['bird_associated_FP'],'calls':len(queried),'calls_per_image':len(queried)/500,'UAV':counts['UAV'],'BIRD':counts['BIRD'],'BACKGROUND':counts['BACKGROUND'],'UNCERTAIN':counts['UNCERTAIN'],'invalid_rate':sum(not r['valid_response'] for r in queried)/len(queried) if queried else 0,'uncertain_rate':counts['UNCERTAIN']/len(queried) if queried else 0,'mean_ms':float(np.mean(lat)) if lat else 0,'p95_ms':float(np.percentile(lat,95)) if lat else 0,'summed_review_seconds':sum(lat)/1000})
        for n,ps in pred.items():
            for j,p in enumerate(ps):fused_all.append({'experiment':group,'image_id':n,'box_id':j,'bbox_xyxy':p[:4].tolist(),'score':float(p[4]),'keep_for_AP':j not in remove[n],'keep_at_025':j not in remove[n] and bool(p[4]>=.25)})
        if group=='E3':
            image_order=[a['image'] for a in ann];offsets=np.cumsum([0]+[len(fused[n]) for n in image_order]);np.savez_compressed(out/'E3_fused_full_predictions.npz',images=np.array(image_order),offsets=offsets,detections=np.concatenate([fused[n] for n in image_order]))
    assert (results[0]['TP'],results[0]['FP'],results[0]['FN'])==(323,119,163)
    csvwrite(out/'metrics.csv',results);dump(out/'full_metrics.json',full_metrics);csvwrite(out/'candidate_decisions.csv',details);csvwrite(out/'removed_tp_fp.csv',[r for r in details if r['removed']]);csvwrite(out/'rematched_survivors.csv',[r for r in details if not r['removed'] and r['baseline_identity']!=r['final_identity']]);write_jsonl(out/'fused_predictions.jsonl',fused_all)
    thresholds=sorted({.25,1.0}|{float(p[4]) for ps in pred.values() for p in ps if p[4]>=.25})
    sweep=[fixed_metrics(pred,ann,t) for t in thresholds];csvwrite(out/'E1_threshold_sweep.csv',sweep)
    comparisons={}
    for r in results[1:]:
        nearest=min(sweep,key=lambda q:(abs(q['Recall']-r['Recall']),q['FP'],-q['Recall']))
        higher=min([q for q in sweep if q['Recall']>=r['Recall']],key=lambda q:(q['FP'],q['Recall']))
        dominating=[q for q in sweep if q['Recall']>=r['Recall'] and q['FP']<=r['FP'] and (q['Recall']>r['Recall'] or q['FP']<r['FP'])]
        comparisons[r['experiment']]={'nearest_recall_E1':nearest,'minimum_FP_E1_at_same_or_higher_recall':higher,'E1_dominates':bool(dominating),'difference_FP_at_nearest_recall':r['FP']-nearest['FP'],'nearest_recall_comparison_is_retrospective':True}
    dump(out/'matched_recall_comparison.json',comparisons)
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,4.5));ax.plot([s['Recall']*100 for s in sweep],[s['FP'] for s in sweep],label='E1: YOLO threshold sweep',color='#617386',linewidth=1.6)
    for r,color in zip(results,['#333333','#9970ab','#d95f02','#1b9e77']):ax.scatter(r['Recall']*100,r['FP'],s=55,label=r['experiment'],color=color,zorder=3);ax.annotate(r['experiment'],(r['Recall']*100,r['FP']),xytext={'E0':(-28,-16),'E2':(8,8),'E3':(8,20),'E4':(8,-23)}[r['experiment']],textcoords='offset points')
    ax.set(xlabel='Recall (%)',ylabel='False positives / 500 images',title='PinP2-YOLO + Qwen2.5-VL: fixed validation set');ax.set_ylim(-7,132);ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(out/'fp_recall.png',dpi=180);fig.savefig(out/'fp_recall.pdf');plt.close(fig)
    # Representative paired examples selected only after prediction, stratified by outcome.
    e3=[r for r in details if r['experiment']=='E3'];rng=random.Random(42);selected=[]
    for removed,identity in [(True,'FP'),(True,'TP'),(False,'TP'),(False,'FP')]:
        pool=[r for r in e3 if r['removed']==removed and r['baseline_identity']==identity];rng.shuffle(pool);selected.extend(pool[:5])
    rest=[r for r in e3 if r not in selected];rng.shuffle(rest);selected+=rest[:20-len(selected)];selected=selected[:20]
    cmap={c['candidate_id']:c for c in candidates};exampledir=out/'error_examples';exampledir.mkdir(exist_ok=True);sheet=Image.new('RGB',(1000,1200),'white');draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(selected):
        c=cmap[r['candidate_id']];x=(i%4)*250;y=(i//4)*240
        for mode,dx in [('context',0),('local',125)]:
            image=Image.open(out/c['crops'][mode]['path']).convert('RGB');sheet.paste(image.resize((122,122)),(x+dx,y));image.save(exampledir/(r['candidate_id']+'_'+mode+'.png'))
        l=lookup.get((c['candidate_id'],'local'));draw.text((x+2,y+128),r['candidate_id'],fill='black');draw.text((x+2,y+145),f"E0:{r['baseline_identity']} E3:{'REMOVE' if r['removed'] else 'KEEP'}",fill='black');draw.text((x+2,y+162),'context: '+r['vlm_label'],fill='black');draw.text((x+2,y+179),'local: '+(l['vlm_label'] if l else 'NOT_QUERIED'),fill='black');draw.text((x+2,y+196),f"score {r['score']:.4f}",fill='black')
    sheet.save(out/'error_examples.jpg');dump(exampledir/'index.json',selected)
    dump(out/'evaluation_receipt.json',{'evaluation_seconds':time.perf_counter()-start,'responses_sha256':sha(out/'vlm_responses.jsonl'),'metrics_sha256':sha(out/'metrics.csv'),'frozen_protocol':True,'all_500_previously_used_for_YOLO_selection':True,'GT_used_for_VLM':False,'AP_policy':'original 0.001-floor list with only reviewed negative candidates removed; unreviewed below .25 retained','E1_policy':'all exact confidence breakpoints from .25; retrospective operating-point diagnostic, not tuned test performance','AP_image_order':'frozen annotation manifest order; stable sorting for tied scores; exported E3 NPZ follows this order','E3_E4_candidate_ids_identical':True,'E2_E3_context_cache_shared':True})
    print(json.dumps({'results':results,'matched_recall':comparisons},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
