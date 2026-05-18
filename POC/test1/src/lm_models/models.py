"""
LM Instance Models - Data classes for LM Studio instances and models.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ModelInfo:
    """Information about a model available on an LM Studio instance."""
    id: str
    object: str = "model"
    owned_by: str = "lmstudio"
    created: Optional[int] = None
    # Optional metadata populated from GGUF headers
    size_label: Optional[str] = None        # e.g. "35B-A3B"
    quantization: Optional[str] = None      # e.g. "IQ2_XXS"
    recommended_vram_mb: Optional[int] = None  # Estimated VRAM requirement

    def to_dict(self) -> dict:
        """Convert to API response dict."""
        result = {
            "id": self.id,
            "object": self.object,
            "owned_by": self.owned_by,
        }
        if self.created is not None:
            result["created"] = self.created
        if self.size_label:
            result["size_label"] = self.size_label
        if self.quantization:
            result["quantization"] = self.quantization
        if self.recommended_vram_mb:
            result["recommended_vram_mb"] = self.recommended_vram_mb
        return result


@dataclass
class LmInstanceConfig:
    """Configuration for a single LM Studio instance."""
    id: str                              # Unique identifier (e.g. "local", "remote-gpu")
    hostname: str                        # Hostname or IP address
    port: int = 1234                     # HTTP port
    display_name: str = ""               # Human-readable name (defaults to id)
    selected_model: str = ""             # Currently selected model ID
    available_models: list = field(default_factory=list)  # Discovered model IDs
    is_connected: bool = False           # Last known connection status
    connected_at: Optional[datetime] = None  # When last connected

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.id

    def to_dict(self) -> dict:
        """Convert to API response dict."""
        return {
            "id": self.id,
            "hostname": self.hostname,
            "port": self.port,
            "display_name": self.display_name,
            "selected_model": self.selected_model,
            "available_models": self.available_models,
            "is_connected": self.is_connected,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LmInstanceConfig":
        """Create from API request dict."""
        return cls(
            id=data["id"],
            hostname=data["hostname"],
            port=data.get("port", 1234),
            display_name=data.get("display_name", ""),
            selected_model=data.get("selected_model", ""),
            available_models=data.get("available_models", []),
            is_connected=data.get("is_connected", False),
        )


@dataclass
class LmInstance:
    """Full instance with connection info and model picker."""
    config: LmInstanceConfig
    # Whether this instance is currently active (used by Discord bot)
    is_active: bool = False