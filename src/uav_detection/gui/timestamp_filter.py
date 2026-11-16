"""Optional timestamp suppression for explicitly verified, hash-bound media only."""
from __future__ import annotations

from pathlib import Path
import numpy as np
from .core import digest


class TimestampFilter:
    def __init__(self, enabled=False, source=None, kind="image", profiles=None):
        self.enabled = bool(enabled)
        self.profile = None
        self.reason = "off"
        if not self.enabled:
            return
        self.reason = "unrecognized_media"
        if kind not in {"image", "video"} or source is None or not Path(source).is_file():
            return
        profile = (profiles or {}).get(digest(source))
        if profile is None:
            return
        size = np.asarray(profile.get("size"), dtype=float)
        region = np.asarray(profile.get("region"), dtype=float)
        coverage = float(profile.get("coverage", .5))
        if (size.shape != (2,) or region.shape != (4,) or not np.isfinite(size).all()
                or not np.isfinite(region).all() or np.any(size <= 0)
                or np.any(region < 0) or np.any(region[2:] <= region[:2])
                or np.any(region[2:] > size) or not 0 < coverage <= 1):
            raise ValueError("Invalid verified timestamp profile / 时间区域配置无效")
        self.profile = {"name": str(profile.get("name", "Verified media")), "size": size.tolist(),
                        "region": region.tolist(), "coverage": coverage}
        self.reason = "verified_media"

    def apply(self, boxes, width, height):
        info = {"enabled": self.enabled, "applied": False, "reason": self.reason, "removed": 0}
        if self.profile is None:
            return boxes.copy(), info
        if [width, height] != self.profile["size"]:
            info["reason"] = "size_mismatch"
            return boxes.copy(), info
        region = np.asarray(self.profile["region"])
        area = np.maximum(0, boxes[:, 2:4] - boxes[:, :2]).prod(1)
        intersection = np.maximum(0, np.minimum(boxes[:, 2:4], region[2:])
                                  - np.maximum(boxes[:, :2], region[:2])).prod(1)
        remove = intersection / np.maximum(area, 1e-12) >= self.profile["coverage"]
        info.update(applied=True, removed=int(remove.sum()), profile=self.profile)
        return boxes[~remove].copy(), info
