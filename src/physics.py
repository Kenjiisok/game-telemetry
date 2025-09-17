"""
Physics Calculations Module
Handles G-force calculations and other physics-related computations for racing telemetry
"""
import math
from typing import Dict, Tuple


def calculate_gforce(acceleration_value: float, gravity: float = 9.81) -> float:
    """
    Convert acceleration to G-force

    Args:
        acceleration_value: Raw acceleration value in m/s²
        gravity: Gravitational acceleration constant (default: 9.81 m/s²)

    Returns:
        G-force value (positive or negative)
    """
    if gravity != 0:
        return acceleration_value / gravity
    return 0.0


def process_gforce_data(longitudinal: float, lateral: float, vertical: float = 0.0) -> Dict[str, float]:
    """
    Process raw acceleration data into comprehensive G-force information

    Args:
        longitudinal: Forward/backward acceleration in m/s²
        lateral: Left/right acceleration in m/s²
        vertical: Up/down acceleration in m/s² (optional)

    Returns:
        Dictionary containing all G-force components and total magnitude
    """
    gforce_data = {
        'longitudinal': calculate_gforce(longitudinal),
        'lateral': calculate_gforce(lateral),
        'vertical': calculate_gforce(vertical),
        'total': calculate_gforce(math.sqrt(longitudinal**2 + lateral**2 + vertical**2))
    }

    return gforce_data


def get_gforce_direction_symbol(gforce_value: float, axis: str = 'longitudinal') -> str:
    """
    Get directional symbol for G-force display

    Args:
        gforce_value: G-force value
        axis: 'longitudinal' or 'lateral'

    Returns:
        Unicode symbol representing direction
    """
    threshold = 0.1

    if axis == 'longitudinal':
        if gforce_value > threshold:
            return "▼"  # Forward/acceleration
        elif gforce_value < -threshold:
            return "▲"  # Backward/braking
        else:
            return "●"  # Neutral

    elif axis == 'lateral':
        if gforce_value > threshold:
            return "◀"  # Left
        elif gforce_value < -threshold:
            return "▶"  # Right
        else:
            return "●"  # Neutral

    return "●"


def smooth_gforce_data(new_value: float, previous_values: list, smoothing_factor: float = 0.3) -> float:
    """
    Apply smoothing filter to G-force data to reduce noise

    Args:
        new_value: Latest G-force reading
        previous_values: List of previous readings
        smoothing_factor: Weight for new value (0.0 to 1.0)

    Returns:
        Smoothed G-force value
    """
    if not previous_values:
        return new_value

    # Simple exponential moving average
    previous_avg = sum(previous_values) / len(previous_values)
    return (smoothing_factor * new_value) + ((1 - smoothing_factor) * previous_avg)


def calculate_braking_rate(longitudinal_gforce: float, is_braking: bool, not_impacted: bool = True) -> float:
    """
    Calculate braking rate based on longitudinal G-force

    Args:
        longitudinal_gforce: Longitudinal G-force value
        is_braking: Whether the vehicle is currently braking
        not_impacted: Whether the vehicle is not impacted/crashed

    Returns:
        Braking rate in G-force (0.0 if not braking)
    """
    if is_braking and not_impacted and longitudinal_gforce < 0:
        return abs(longitudinal_gforce)
    return 0.0


def gforce_to_circle_coordinates(longitudinal: float, lateral: float,
                                radius: float, center_x: float, center_y: float) -> Tuple[float, float]:
    """
    Convert G-force values to coordinates for friction circle display

    Args:
        longitudinal: Longitudinal G-force
        lateral: Lateral G-force
        radius: Circle radius for scaling
        center_x: Center X coordinate
        center_y: Center Y coordinate

    Returns:
        Tuple of (x, y) coordinates for circle display
    """
    # Scale G-forces to circle coordinates
    # Note: Invert Y axis for typical display orientation
    x = lateral * radius + center_x
    y = -longitudinal * radius + center_y  # Negative for standard orientation

    return (x, y)


class GForceCalculator:
    """
    Advanced G-force calculator with history and filtering capabilities
    """

    def __init__(self, history_size: int = 10, smoothing_factor: float = 0.3):
        self.history_size = history_size
        self.smoothing_factor = smoothing_factor
        self.longitudinal_history = []
        self.lateral_history = []
        self.vertical_history = []

        # Peak tracking
        self.max_longitudinal = 0.0
        self.max_lateral = 0.0
        self.max_total = 0.0

    def update(self, longitudinal: float, lateral: float, vertical: float = 0.0) -> Dict[str, float]:
        """
        Update G-force calculations with new telemetry data

        Args:
            longitudinal: Raw longitudinal acceleration
            lateral: Raw lateral acceleration
            vertical: Raw vertical acceleration

        Returns:
            Processed G-force data with smoothing applied
        """
        # Convert to G-forces
        raw_gforces = process_gforce_data(longitudinal, lateral, vertical)

        # Apply smoothing
        smoothed_longitudinal = smooth_gforce_data(
            raw_gforces['longitudinal'], self.longitudinal_history, self.smoothing_factor
        )
        smoothed_lateral = smooth_gforce_data(
            raw_gforces['lateral'], self.lateral_history, self.smoothing_factor
        )
        smoothed_vertical = smooth_gforce_data(
            raw_gforces['vertical'], self.vertical_history, self.smoothing_factor
        )

        # Update history
        self._update_history(smoothed_longitudinal, smoothed_lateral, smoothed_vertical)

        # Update peaks
        self._update_peaks(smoothed_longitudinal, smoothed_lateral)

        # Calculate total
        total_gforce = math.sqrt(smoothed_longitudinal**2 + smoothed_lateral**2 + smoothed_vertical**2)

        return {
            'longitudinal': smoothed_longitudinal,
            'lateral': smoothed_lateral,
            'vertical': smoothed_vertical,
            'total': total_gforce,
            'max_longitudinal': self.max_longitudinal,
            'max_lateral': self.max_lateral,
            'max_total': self.max_total
        }

    def _update_history(self, longitudinal: float, lateral: float, vertical: float):
        """Update history buffers with new values"""
        for history, value in [
            (self.longitudinal_history, longitudinal),
            (self.lateral_history, lateral),
            (self.vertical_history, vertical)
        ]:
            history.append(value)
            if len(history) > self.history_size:
                history.pop(0)

    def _update_peaks(self, longitudinal: float, lateral: float):
        """Update peak G-force tracking"""
        self.max_longitudinal = max(self.max_longitudinal, abs(longitudinal))
        self.max_lateral = max(self.max_lateral, abs(lateral))

        total = math.sqrt(longitudinal**2 + lateral**2)
        self.max_total = max(self.max_total, total)

    def reset_peaks(self):
        """Reset peak tracking values"""
        self.max_longitudinal = 0.0
        self.max_lateral = 0.0
        self.max_total = 0.0

    def get_circle_coordinates(self, radius: float, center_x: float, center_y: float) -> Tuple[float, float]:
        """
        Get current G-force position for friction circle display

        Returns:
            Tuple of (x, y) coordinates
        """
        if not self.longitudinal_history or not self.lateral_history:
            return (center_x, center_y)

        current_long = self.longitudinal_history[-1]
        current_lat = self.lateral_history[-1]

        return gforce_to_circle_coordinates(current_long, current_lat, radius, center_x, center_y)