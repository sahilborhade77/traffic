"""
Feature 7: Repeat Offender Detection
--------------------------------------
Queries violation history and applies fine multipliers 
defined in violations.yaml for repeat offenders.
Runs on DB queries — zero VRAM.
"""

import logging
import yaml
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class RepeatOffenderEngine:
    """
    Checks vehicle violation history and applies multipliers from violations.yaml.
    Integrates with ViolationDatabase to look up prior offenses.
    """
    def __init__(self, db_manager, violations_config_path: str = 'config/violations.yaml'):
        self.db = db_manager
        
        # Load fine multipliers from config
        if Path(violations_config_path).exists():
            with open(violations_config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.multipliers = config.get('fine_multipliers', {})
        else:
            self.multipliers = {
                'repeat_offender_30_days': 1.5,
                'repeat_offender_90_days': 2.0,
                'night_time': 1.5,
                'school_zone': 2.0
            }
        logger.info(f"RepeatOffenderEngine loaded. Multipliers: {self.multipliers}")

    def calculate_fine(
        self,
        plate_number: str,
        base_fine: float,
        violation_timestamp: Optional[datetime] = None,
        is_school_zone: bool = False
    ) -> dict:
        """
        Calculate final fine amount with all applicable multipliers.
        
        Returns:
            dict with 'final_fine', 'multiplier', 'reason'
        """
        if violation_timestamp is None:
            violation_timestamp = datetime.now()

        multiplier = 1.0
        reasons = []

        # ── Check repeat offenses ──
        violations_30 = self.db.get_violations_by_plate(plate_number, days=30)
        violations_90 = self.db.get_violations_by_plate(plate_number, days=90)

        if len(violations_30) >= 1:
            m = self.multipliers.get('repeat_offender_30_days', 1.5)
            multiplier = max(multiplier, m)
            reasons.append(f"Repeat offender (30 days): ×{m}")
            logger.warning(f"REPEAT OFFENDER (30d): {plate_number} | {len(violations_30)} prior violations")

        elif len(violations_90) >= 2:
            m = self.multipliers.get('repeat_offender_90_days', 2.0)
            multiplier = max(multiplier, m)
            reasons.append(f"Repeat offender (90 days): ×{m}")
            logger.warning(f"REPEAT OFFENDER (90d): {plate_number} | {len(violations_90)} prior violations")

        # ── Night-time check (10 PM – 6 AM) ──
        hour = violation_timestamp.hour
        if hour >= 22 or hour < 6:
            m = self.multipliers.get('night_time', 1.5)
            multiplier = max(multiplier, m)
            reasons.append(f"Night-time violation: ×{m}")

        # ── School zone check ──
        if is_school_zone:
            m = self.multipliers.get('school_zone', 2.0)
            multiplier = max(multiplier, m)
            reasons.append(f"School zone: ×{m}")

        final_fine = round(base_fine * multiplier, 2)
        reason_str = " | ".join(reasons) if reasons else "Standard fine"

        return {
            'base_fine': base_fine,
            'multiplier': multiplier,
            'final_fine': final_fine,
            'reason': reason_str,
            'prior_violations_30d': len(violations_30),
            'prior_violations_90d': len(violations_90)
        }
