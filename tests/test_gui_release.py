"""Package-integrity checks use byte fixtures, never a model runtime or network."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gui_model_download', ROOT / 'scripts/download_gui_model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ModelPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def package(self, names=('model.hef', 'h10_metadata.json')):
        data = b'EXPLICIT TEST FIXTURE, NOT A MODEL'
        files = {n: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for n in names}
        archive = self.root / 'fixture.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for n in names:
                z.writestr(n, data)
        return archive, {'files': files, 'bytes': archive.stat().st_size,
                         'sha256': module.sha256(archive)}

    def test_install_verifies_and_never_overwrites(self):
        archive, manifest = self.package()
        target = self.root / 'installed'
        module.install_archive(archive, target, manifest)
        module.verify_files(target, manifest)
        with self.assertRaises(FileExistsError):
            module.install_archive(archive, target, manifest)
        (target / 'model.hef').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            module.verify_files(target, manifest)

    def test_bad_archive_hash_installs_nothing(self):
        archive, manifest = self.package()
        manifest['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            module.install_archive(archive, self.root / 'installed', manifest)
        self.assertFalse((self.root / 'installed').exists())

    def test_zip_paths_cannot_escape_output(self):
        archive, manifest = self.package(('../escape',))
        with self.assertRaises(ValueError):
            module.install_archive(archive, self.root / 'installed', manifest)
        self.assertFalse((self.root / 'escape').exists())
        self.assertFalse((self.root / 'installed').exists())


if __name__ == '__main__':
    unittest.main()
