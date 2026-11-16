"""Pi-only in-process H10 adapter; no image encoding, HTTP or CPU fallback."""
from pathlib import Path
import platform
import sys
import time
from PIL import Image
from .core import ROOT, boxes_array


class LocalH10:
    def __init__(self, model_dir, lock_paths):
        if platform.system() != 'Linux' or platform.machine() != 'aarch64':
            raise RuntimeError('Local H10 requires Raspberry Pi / 本机模式仅支持树莓派')
        sys.path.insert(0, str(ROOT / 'scripts/deployment'))
        from serve_gui import H10Engine
        self.engine = H10Engine(Path(model_dir), lock_paths)
        self.last_transport = {'encoding': 'rgb_in_memory', 'upload_bytes': 0}

    def health(self):
        return {**self.engine.info, 'transport': 'local_memory', 'network_bytes_per_frame': 0}

    def detect(self, rgb, **unused):
        start = time.perf_counter()
        result = self.engine.detect(Image.fromarray(rgb))
        return boxes_array(result['boxes_xyxy_score_class']), (time.perf_counter()-start)*1000, result['pipeline_ms']

    def close(self):
        self.engine.close()
