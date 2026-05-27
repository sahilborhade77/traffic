import numpy as np

from src.violations.phone_detector import PhoneDetector


class _MockTensor:
    def __init__(self, value):
        self.value = np.array(value, dtype=float)

    def cpu(self):
        return self

    def numpy(self):
        return self.value


class _MockBox:
    def __init__(self, confidence=0.88):
        self.conf = [_MockTensor(confidence)]


class _MockBoxes(list):
    pass


class _MockResults:
    def __init__(self, has_phone=True):
        self.boxes = _MockBoxes([_MockBox()]) if has_phone else _MockBoxes()


class _MockModelManager:
    def __init__(self, has_phone=True):
        self.has_phone = has_phone
        self.calls = []

    def detect(self, frame, conf, classes):
        self.calls.append({"shape": frame.shape, "conf": conf, "classes": classes})
        return _MockResults(has_phone=self.has_phone)


def test_phone_detector_flags_driver_phone_region():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector = PhoneDetector(conf_threshold=0.45, cooldown_frames=60)
    model_manager = _MockModelManager(has_phone=True)

    violation = detector.check(
        frame=frame,
        track_id=101,
        vehicle_bbox=(100, 120, 360, 360),
        model_manager=model_manager,
        frame_id=100
    )

    assert violation is not None
    assert violation.track_id == 101
    assert violation.confidence == 0.88
    assert model_manager.calls[0]["classes"] == [67]


def test_phone_detector_cooldown_prevents_duplicate_flags():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector = PhoneDetector(conf_threshold=0.45, cooldown_frames=60)
    model_manager = _MockModelManager(has_phone=True)

    first = detector.check(frame, 101, (100, 120, 360, 360), model_manager, frame_id=100)
    second = detector.check(frame, 101, (100, 120, 360, 360), model_manager, frame_id=120)

    assert first is not None
    assert second is None
