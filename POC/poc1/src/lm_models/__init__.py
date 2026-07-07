"""
LM Models package - Model selection and discovery for LM Studio instances.
"""

from .models import LmInstance, LmInstanceConfig, ModelInfo
from .manager import InstanceManager

__all__ = [
    "LmInstance",
    "LmInstanceConfig",
    "ModelInfo",
    "InstanceManager",
]