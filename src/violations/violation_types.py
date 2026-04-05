from enum import Enum

class ViolationType(Enum):
    """
    Standard Traffic Violations.
    """
    RED_LIGHT = "Red Light"
    OVERSPEEDING = "Overspeeding"
    WRONG_LANE = "Wrong Lane"
    NO_HELMET = "No Helmet"
    STOP_LINE_CROSSING = "Stop Line Crossing"
    INVALID_PLATE = "Invalid License Plate"
    THREE_RIDING = "Triple Riding" # Bonus extra

def get_fine_amount(violation_type: ViolationType) -> int:
    """
    Standard fine amounts based on Indian MVA (Motor Vehicle Act).
    """
    fines = {
        ViolationType.RED_LIGHT: 500,
        ViolationType.OVERSPEEDING: 2000,
        ViolationType.WRONG_LANE: 1000,
        ViolationType.NO_HELMET: 1000,
        ViolationType.STOP_LINE_CROSSING: 500,
        ViolationType.INVALID_PLATE: 5000,
        ViolationType.THREE_RIDING: 1000
    }
    return fines.get(violation_type, 0)
