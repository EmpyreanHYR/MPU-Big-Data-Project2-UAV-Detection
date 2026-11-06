"""Pure annotation/split tests; no Torch/model imports."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).resolve().parents[1]/'scripts/consolidate_ir_datasets.py'
spec=importlib.util.spec_from_file_location('consolidate',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Consolidation(unittest.TestCase):
    def test_polygon_envelope_and_native_class_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'label.txt';p.write_text('2 0.2 0.3 0.5 0.3 0.4 0.6\n')
            boxes,birds,classes,conversion,_=m.read_boxes(p,'AUVD-seg300',100,100)
            self.assertEqual(boxes,[[0,.2,.3,.5,.6]])
            self.assertEqual(classes,['2']);self.assertEqual(birds,[])
            self.assertEqual(conversion,'polygon_to_enclosing_yolo_bbox')
    def test_labelme_four_point_rectangle(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'label.json';p.write_text(json.dumps({'imageWidth':100,'imageHeight':50,'shapes':[{'label':'drone','shape_type':'rectangle','points':[[40,10],[20,30],[20,10],[40,30]]}]}))
            self.assertEqual(m.read_boxes(p,'UAV-CB',100,50)[0],[[0,.2,.2,.4,.6]])
    def test_bird_is_negative_and_empty_test_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'label.txt';p.write_text('1 0.5 0.5 0.2 0.2\n')
            boxes,birds,*_=m.read_boxes(p,'SIRST-UAVB',100,100)
            self.assertEqual(boxes,[]);self.assertEqual(len(birds),1)
            p.write_text('');self.assertEqual(m.read_boxes(p,m.TEST,100,100)[0],[])
    def test_invalid_box_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'label.txt';p.write_text('0 0.0 0.5 0.2 0.2\n')
            with self.assertRaises(ValueError):m.read_boxes(p,m.TEST,100,100)
    def test_one_pixel_border_clip_has_explicit_before_after_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'label.txt';p.write_text('0 0.987500 0.526367 0.028125 0.025391\n')
            boxes,_,_,_,corrections=m.read_boxes(p,m.TEST,640,512)
            self.assertEqual(boxes[0][3],1.)
            self.assertEqual(len(corrections),1)
            self.assertGreater(corrections[0]['before_xyxy'][3],1.)
            self.assertAlmostEqual(corrections[0]['max_excess_pixels'],1.)
    def test_zero_area_annotation_is_not_a_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'label.txt';p.write_text('0 0 0 0 0\n')
            with self.assertRaisesRegex(ValueError,'Zero-area'):
                m.read_boxes(p,m.TEST,640,512)
    def test_global_exact_ratio_keeps_groups_and_is_deterministic(self):
        base=[{'dataset':ds,'group':f'{ds}-{g}'} for ds in ['A','B'] for g,n in [('one',3),('two',4),('three',3)] for _ in range(n)]
        a=[dict(x) for x in base];b=[dict(x) for x in base]
        m.choose_validation(a,42);m.choose_validation(b,42)
        self.assertEqual(a,b);self.assertEqual(sum(x['split']=='val' for x in a),4)
        self.assertTrue(all(len({r['split'] for r in a if r['group']==g})==1 for g in {r['group'] for r in a}))

if __name__=='__main__':unittest.main()
