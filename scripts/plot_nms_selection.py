#!/usr/bin/env python3
"""Reproduce the manuscript NMS selection figure from measured aggregate/run tables."""
from pathlib import Path
import csv
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / 'docs/results/NMS_HARDWARE_20261115.json'
RUNS = ROOT / 'docs/results/NMS_HARDWARE_RUNS_20261115.csv'
OUT = ROOT / 'docs/report/figures'


def main():
    rows = json.loads(SUMMARY.read_text())
    runs = list(csv.DictReader(RUNS.open()))
    assert len(rows) == 8 and len(runs) == 24
    assert [r['nms_iou'] for r in rows] == ['none', .3, .4, .5, .6, .7, .8, .9]
    assert all((r['TP'], r['FN']) == (323, 163) for r in rows)
    x = np.arange(8); selected = 2
    colors = ['#777777'] + ['#3274A1'] * 7
    colors[selected] = '#C35200'
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':8.5,
                         'axes.titlesize':9,'axes.labelsize':8.5,'xtick.labelsize':7.5,
                         'ytick.labelsize':8,'pdf.fonttype':42,'ps.fonttype':42,
                         'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False}):
        fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.35))
        fig.subplots_adjust(left=.065, right=.99, bottom=.25, top=.76, wspace=.40)
        values = [[r['mAP50_95_deployment']*100 for r in rows],
                  [r['FP'] for r in rows], [r['pipeline_FPS'] for r in rows]]
        for i, (ax, vals) in enumerate(zip(axes, values)):
            bars = ax.bar(x, vals, width=.68, color=colors, edgecolor='white', linewidth=.5, zorder=2)
            bars[selected].set_hatch('///'); bars[selected].set_edgecolor('#202020'); bars[selected].set_linewidth(.8)
            ax.set_xticks(x, ['Off','0.3','0.4','0.5','0.6','0.7','0.8','0.9'])
            ax.get_xticklabels()[selected].set_fontweight('bold')
            ax.set_xlabel('NMS IoU threshold', labelpad=3)
            ax.set_axisbelow(True); ax.grid(axis='y', color='#dedede', linewidth=.5)
            ax.tick_params(axis='x', length=0)
            ax.set_xlim(-.6,7.6)
            if i == 0:
                ax.set_title('(a) Detection AP', loc='left'); ax.set_ylabel('AP50:95 (%)')
                ax.set_ylim(0,38);ax.set_yticks([0,10,20,30])
                for j in [0,selected]:ax.text(j,vals[j]+1.0,f'{vals[j]:.2f}',ha='center',fontsize=7.5)
            elif i == 1:
                ax.set_title('(b) False positives',loc='left');ax.set_ylabel('FP count')
                ax.set_ylim(0,145);ax.set_yticks([0,50,100])
                for j,v in enumerate(vals):ax.text(j,v+3,str(v),ha='center',fontsize=7.5)
            else:
                ax.set_title('(c) Measured throughput',loc='left');ax.set_ylabel('Pipeline FPS')
                ax.set_ylim(0,28);ax.set_yticks([0,10,20])
                ax.errorbar(x,vals,yerr=[r['pipeline_FPS_SD'] for r in rows],fmt='none',ecolor='black',elinewidth=.7,capsize=2,zorder=4)
                for j,r in enumerate(rows):
                    ys=[float(q['pipeline_FPS']) for q in runs if q['nms_iou']==str(r['nms_iou'])]
                    assert len(ys)==3
                    ax.scatter(j+np.array([-.13,0,.13]),ys,s=5,color='#151515',zorder=5)
                ax.text(.5,.98,'3 runs; mean ± SD',transform=ax.transAxes,ha='center',va='top',fontsize=7)
        fig.legend(handles=[Patch(facecolor='#777777',label='No NMS'),Patch(facecolor='#3274A1',label='Other thresholds'),Patch(facecolor='#C35200',edgecolor='#202020',hatch='///',label='Default IoU = 0.4')],loc='upper center',bbox_to_anchor=(.5,1.015),ncol=3,frameon=False,fontsize=8)
        fig.text(.5,.035,'All settings: TP = 323, FN = 163, recall = 66.46%  |  500 validation images',ha='center',fontsize=8)
        for ext in ['pdf','svg','png']:
            fig.savefig(OUT/f'nms_selection.{ext}',dpi=300,facecolor='white')
        plt.close(fig)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={'figure':'NMS deployment threshold selection','destination':'course IEEE report, provisional general scientific figure; not publisher compliance certification','size_inches':[7.0,2.35],'PNG_DPI':300,'sources':{'summary_sha256':sha(SUMMARY),'runs_sha256':sha(RUNS)},'script_sha256':sha(Path(__file__)),'matplotlib_version':matplotlib.__version__,'numpy_version':np.__version__,'transformations':'AP fraction multiplied by100; no smoothing, normalization, exclusions or interpolation. All8 settings included.','uncertainty':'FPS arithmetic mean ± sample SD across3 independently launched500-image runs; black points show each run. No inferential accuracy error bars from repeated identical predictions.','axes':'All bar axes start at0; no dual axes. Off is a categorical no-NMS control, not IoU=0.','default_encoding':'orange bar plus hatch, bold tick and legend; not color alone','raw_table':'docs/results/NMS_HARDWARE_20261115.csv','outputs':{f'nms_selection.{e}':sha(OUT/f'nms_selection.{e}') for e in ['pdf','svg','png']}}
    (OUT/'nms_selection.provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
