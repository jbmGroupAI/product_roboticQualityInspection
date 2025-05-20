import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from dataclasses import dataclass
from typing import List, Tuple, Optional
import cupy as cp

@dataclass
class GapConfig:
    GAP_THRESHOLD: float = 8.0  # Multiplier for median absolute deviation
    MIN_DIP_DEPTH: float = 30.0  # Minimum depth to consider a dip significant
    MAX_GAP_WIDTH: int = 200    # Maximum number of points in a dip to consider it a gap
    MIN_ANOMALY_GROUP_SIZE: int = 5  # Minimum size for anomaly group to be considered
    MAX_GROUP_JOIN_GAP: int = 3  # Maximum index gap to join groups
    USE_GPU: bool = False  # Whether to use GPU acceleration

class GapDetector:
    def __init__(self, config: Optional[GapConfig] = None):
        self.config = config or GapConfig()
        self.gpu_available = False
        try:
            # Test if CUDA is available
            test_array = cp.array([1, 2, 3])
            test_result = cp.sum(test_array)
            self.gpu_available = True
            print("GPU acceleration enabled for gap detection")
        except Exception:
            print("GPU acceleration not available for gap detection")
            # Create dummy cp module
            class DummyCP:
                def __getattr__(self, name):
                    return getattr(np, name)
            cp = DummyCP()

    def to_gpu(self, data):
        """Convert numpy array to GPU array if GPU is available"""
        if self.config.USE_GPU and self.gpu_available:
            return cp.asarray(data)
        return data

    def to_cpu(self, data):
        """Convert GPU array back to numpy array if needed"""
        if self.config.USE_GPU and self.gpu_available and isinstance(data, cp.ndarray):
            return cp.asnumpy(data)
        return data

    def detect_gaps(self, x_data: np.ndarray, z_data: np.ndarray) -> List[Tuple[float, float, float]]:
        """
        Detect gaps in the profile data.
        Returns list of tuples (x_min, x_max, width) for each detected gap.
        """
        if len(x_data) < 10:
            return []

        try:
            # Convert data to GPU if available
            x_data = self.to_gpu(x_data)
            z_data = self.to_gpu(z_data)

            # First pass: identify general trend using robust smoothing
            window = min(101, len(z_data) - 2)
            if window < 5:
                return []

            if window % 2 == 0:
                window -= 1

            # Apply filter to get expected trend
            z_trend = savgol_filter(self.to_cpu(z_data), window, 2)
            z_trend = self.to_gpu(z_trend)

            # Find significant deviations from trend
            deviations = z_trend - z_data

            # Use dynamic threshold based on robust statistics
            med_deviation = cp.median(deviations)
            mad = cp.median(cp.abs(deviations - med_deviation))
            dynamic_threshold = med_deviation + self.config.GAP_THRESHOLD * mad

            # Find significant negative deviations
            candidate_indices = cp.where(deviations > dynamic_threshold)[0]
            candidate_indices = self.to_cpu(candidate_indices)

            if len(candidate_indices) == 0:
                return []

            # Group adjacent indices into contiguous segments
            segments = []
            current_segment = [candidate_indices[0]]

            for i in range(1, len(candidate_indices)):
                if candidate_indices[i] - candidate_indices[i-1] <= 3:
                    current_segment.append(candidate_indices[i])
                else:
                    if len(current_segment) >= 3:
                        segments.append(current_segment)
                    current_segment = [candidate_indices[i]]

            if len(current_segment) >= 3:
                segments.append(current_segment)

            # Process segments to find valid gaps
            gaps = []
            for segment in segments:
                start_idx = max(0, min(segment) - 2)
                end_idx = min(len(z_data) - 1, max(segment) + 2)

                segment_z = self.to_cpu(z_data[start_idx:end_idx+1])
                if len(segment_z) > 0:
                    min_z = np.min(segment_z)
                    max_z = np.max(segment_z)
                    dip_depth = max_z - min_z

                    if dip_depth > self.config.MIN_DIP_DEPTH:
                        # Find edges of the gap
                        left_edge = start_idx
                        while left_edge > 0:
                            if left_edge < 3 or (self.to_cpu(z_data[left_edge]) < self.to_cpu(z_data[left_edge-1])):
                                left_edge -= 1
                            else:
                                break

                        right_edge = end_idx
                        while right_edge < len(z_data) - 1:
                            if right_edge > len(z_data) - 3 or (self.to_cpu(z_data[right_edge]) < self.to_cpu(z_data[right_edge+1])):
                                right_edge += 1
                            else:
                                break

                        gap_width = right_edge - left_edge
                        if gap_width <= self.config.MAX_GAP_WIDTH:
                            x_min = self.to_cpu(x_data[left_edge])
                            x_max = self.to_cpu(x_data[right_edge])
                            width = x_max - x_min
                            gaps.append((x_min, x_max, width))

            return gaps

        except Exception as e:
            print(f"Gap detection encountered an issue: {e}")
            return []

    def visualize_gaps(self, x_data: np.ndarray, z_data: np.ndarray, gaps: List[Tuple[float, float, float]]):
        """
        Visualize the detected gaps on a plot.
        """
        plt.figure(figsize=(12, 6))
        plt.plot(x_data, z_data, 'b-', label='Profile')
        
        for x_min, x_max, width in gaps:
            plt.axvline(x=x_min, color='r', linestyle='--', alpha=0.5)
            plt.axvline(x=x_max, color='r', linestyle='--', alpha=0.5)
            plt.text((x_min + x_max)/2, min(z_data), f'Width: {width:.2f}',
                    horizontalalignment='center', verticalalignment='top',
                    bbox=dict(facecolor='white', alpha=0.7))

        plt.title('Detected Gaps in Profile')
        plt.xlabel('X Position')
        plt.ylabel('Z Height')
        plt.grid(True)
        plt.legend()
        plt.show() 