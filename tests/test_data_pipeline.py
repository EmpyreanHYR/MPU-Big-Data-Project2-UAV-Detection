"""Preparation tests use generated tiny images, never a real benchmark split."""
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))


@unittest.skipUnless(importlib.util.find_spec("PIL"),"Install the data optional dependency")
class DataPreparation(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.raw=self.root/'raw';self.raw.mkdir()
        self.manifest=self.root/'manifest.csv'
        self.mapping=self.root/'class_map.json'
        self.mapping.write_text(json.dumps({'0':'uav','1':'bird'}))
        self.rows=[]
        for i in range(6):
            Image.new('RGB',(40,30),(i+10,i+20,i+30)).save(self.raw/f'{i}.png')
            (self.raw/f'{i}.txt').write_text('0 0.5 0.5 0.1 0.1\n1 0.2 0.2 0.1 0.1\n')
            self.rows.append({'image':f'{i}.png','annotation':f'{i}.txt','format':'yolo',
                              'group':f'seq{i//2}','split':['train','val','test'][i//2]})
        self.write_manifest()

    def tearDown(self):self.temp.cleanup()

    def write_manifest(self):
        with self.manifest.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['image','annotation','format','group','split'])
            writer.writeheader();writer.writerows(self.rows)

    def prepare(self,name='prepared'):
        from uav_detection.data.prepare import prepare_dataset
        return prepare_dataset(self.manifest,self.raw,self.mapping,self.root/name)

    def test_prepare_filter_and_audit(self):
        from uav_detection.data.prepare import audit_prepared
        result=self.prepare()
        self.assertEqual(result['images'],{'train':2,'val':2,'test':2})
        self.assertEqual(result['uav_boxes'],6)
        self.assertEqual(result['bird_boxes_for_error_analysis'],6)
        self.assertEqual(audit_prepared(self.root/'prepared')['status'],'PASS')
        for path in (self.root/'prepared/labels').rglob('*.txt'):
            lines=path.read_text().splitlines()
            self.assertEqual(len(lines),1)
            self.assertTrue(lines[0].startswith('0 '))

    def test_unknown_class_and_bad_boxes_fail_without_output(self):
        for line in ['9 0.5 0.5 0.1 0.1','0 nan 0.5 0.1 0.1','0 0.99 0.5 0.5 0.5','0 0.5 0.5 0 0.1']:
            with self.subTest(line=line):
                (self.raw/'0.txt').write_text(line)
                with self.assertRaises(ValueError):self.prepare()
                self.assertFalse((self.root/'prepared').exists())

    def test_source_group_cannot_cross_splits(self):
        self.rows[2]['group']='seq0';self.write_manifest()
        with self.assertRaises(ValueError):self.prepare()

    def test_reencoded_pixel_duplicate_cannot_cross_splits(self):
        from PIL import Image
        with Image.open(self.raw/'0.png') as im:im.save(self.raw/'2.png',compress_level=0)
        with self.assertRaises(ValueError):self.prepare()

    def test_conflicting_annotations_for_same_pixels(self):
        shutil.copyfile(self.raw/'0.png',self.raw/'1.png')
        (self.raw/'1.txt').write_text('0 0.5 0.5 0.2 0.1')
        with self.assertRaises(ValueError):self.prepare()

    def test_auto_splits_keep_whole_groups_deterministically(self):
        for row in self.rows:row['split']=''
        self.write_manifest();self.prepare('first');self.prepare('second')
        a=json.loads((self.root/'first/manifest.json').read_text())['images']
        b=json.loads((self.root/'second/manifest.json').read_text())['images']
        self.assertEqual([(x['source_image'],x['split']) for x in a],[(x['source_image'],x['split']) for x in b])
        for group in {x['group'] for x in a}:
            self.assertEqual(len({x['split'] for x in a if x['group']==group}),1)

    def test_partial_splits_missing_group_or_annotation_rejected(self):
        original=[dict(r) for r in self.rows]
        for change in [{'split':''},{'group':''},{'annotation':'missing.txt'},{'image':'../outside.png'}]:
            self.rows=[dict(r) for r in original];self.rows[0].update(change);self.write_manifest()
            with self.subTest(change=change),self.assertRaises(ValueError):self.prepare()

    def test_one_pixel_voc_box_preserved(self):
        from uav_detection.data.prepare import prepare_dataset
        for i,row in enumerate(self.rows):
            row['format']='voc';row['annotation']=f'{i}.xml'
            (self.raw/f'{i}.xml').write_text('<annotation><size><width>40</width><height>30</height></size><object><name>0</name><bndbox><xmin>1</xmin><ymin>1</ymin><xmax>1</xmax><ymax>1</ymax></bndbox></object></annotation>')
        self.write_manifest()
        result=prepare_dataset(self.manifest,self.raw,self.mapping,self.root/'prepared',voc_mode='one-based-inclusive')
        self.assertEqual(result['uav_boxes'],6)
        sample=next((self.root/'prepared/labels').rglob('*.txt')).read_text().split()
        self.assertAlmostEqual(float(sample[3]),1/40)
        self.assertAlmostEqual(float(sample[4]),1/30)

    def test_voc_requires_convention(self):
        self.rows[0]['format']='voc';self.write_manifest()
        with self.assertRaises(ValueError):self.prepare()

    def test_verified_negative_is_explicit_empty_label(self):
        self.rows[1].update(annotation='',format='negative');self.write_manifest()
        result=self.prepare();self.assertEqual(result['uav_boxes'],5)
        self.assertEqual(sum(not x.read_text() for x in (self.root/'prepared/labels').rglob('*.txt')),1)

    def test_tampered_labels_and_unmanifested_images_fail_audit(self):
        from uav_detection.data.prepare import audit_prepared
        self.prepare();folder=self.root/'prepared'
        path=next((folder/'labels').rglob('*.txt'));original=path.read_text();path.write_text('')
        with self.assertRaises(ValueError):audit_prepared(folder)
        path.write_text(original)
        shutil.copyfile(self.raw/'0.png',folder/'images/train/unmanifested.png')
        with self.assertRaises(ValueError):audit_prepared(folder)

    def test_existing_output_is_preserved(self):
        out=self.root/'prepared';out.mkdir();(out/'keep').write_text('unique')
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual((out/'keep').read_text(),'unique')


if __name__=='__main__':unittest.main()
