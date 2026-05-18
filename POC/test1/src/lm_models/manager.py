"""
Instance Manager - Manages multiple LM Studio instances and model selection.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

import requests

from .models import LmInstance, LmInstanceConfig, ModelInfo

logger = logging.getLogger(__name__)

# Estimated VRAM in MB by parameter size tier (for informational purposes)
_VRAM_ESTIMATES = {
    "1B": 2000,
    "3B": 4000,
    "7B": 8000,
    "8B": 8000,
    "11B": 12000,
    "13B": 14000,
    "14B": 14000,
    "32B": 24000,
    "35B": 28000,
    "70B": 48000,
    "72B": 48000,
    "405B": 256000,
}


class InstanceManager:
    """Manages a collection of LM Studio instances."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize instance manager.

        Args:
            config_path: Path to config.json file. Defaults to config.json in project root.
        """
        if config_path is None:
            # Default: project root config.json
            config_path = str(Path(__file__).parents[2] / "config.json")
        self._config_path = Path(config_path)
        self._instances: dict[str, LmInstanceConfig] = {}
        self._active_id: str = "local"
        self._load()

    def _load(self) -> None:
        """Load instances from config file."""
        if not self._config_path.exists():
            # Create default local instance
            self._instances = {
                "local": LmInstanceConfig(
                    id="local",
                    hostname="localhost",
                    port=1234,
                    display_name="Local LM Studio",
                )
            }
            self._active_id = "local"
            self._save()
            return

        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)
            instances_data = data.get("lm_instances", {})
            self._active_id = data.get("active_instance", "local")
            
            # If no instances in config, create default local instance
            if not instances_data:
                self._instances = {
                    "local": LmInstanceConfig(
                        id="local",
                        hostname="localhost",
                        port=1234,
                        display_name="Local LM Studio",
                    )
                }
                self._active_id = "local"
                self._save()
                return
            
            for inst_id, inst_data in instances_data.items():
                self._instances[inst_id] = LmInstanceConfig.from_dict(inst_data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load LM instances from config: {e}")
            self._instances = {
                "local": LmInstanceConfig(
                    id="local",
                    hostname="localhost",
                    port=1234,
                    display_name="Local LM Studio",
                )
            }
            self._active_id = "local"

    def _save(self) -> None:
        """Save instances to config file."""
        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}

        # Update lm_instances section
        data["lm_instances"] = {
            inst_id: inst.to_dict() for inst_id, inst in self._instances.items()
        }
        data["active_instance"] = self._active_id

        # Also update legacy lm_studio section for backward compatibility
        active = self.get_active()
        if active:
            data.setdefault("lm_studio", {})["hostname"] = active.hostname
            data.setdefault("lm_studio", {})["port"] = active.port

        with open(self._config_path, "w") as f:
            json.dump(data, f, indent=2)

    # --- CRUD Operations ---

    def add_instance(self, config: LmInstanceConfig) -> None:
        """Add a new LM Studio instance.

        Args:
            config: Configuration for the new instance.
        """
        self._instances[config.id] = config
        if not self._active_id:
            self._active_id = config.id
        self._save()
        logger.info(f"Added LM Studio instance: {config.id} ({config.hostname}:{config.port})")

    def remove_instance(self, instance_id: str) -> bool:
        """Remove an LM Studio instance.

        Args:
            instance_id: ID of the instance to remove.

        Returns:
            True if removed, False if not found.
        """
        if instance_id not in self._instances:
            return False
        del self._instances[instance_id]
        # If the removed instance was active, switch to first available
        if self._active_id == instance_id and self._instances:
            self._active_id = next(iter(self._instances))
        self._save()
        logger.info(f"Removed LM Studio instance: {instance_id}")
        return True

    def get_instance(self, instance_id: str) -> Optional[LmInstanceConfig]:
        """Get an instance by ID.

        Args:
            instance_id: Instance ID.

        Returns:
            LmInstanceConfig or None.
        """
        return self._instances.get(instance_id)

    def get_all(self) -> dict[str, LmInstanceConfig]:
        """Get all instances.

        Returns:
            Dict of instance_id -> LmInstanceConfig.
        """
        return dict(self._instances)

    def get_active(self) -> Optional[LmInstanceConfig]:
        """Get the active instance.

        Returns:
            Active LmInstanceConfig or None.
        """
        return self._instances.get(self._active_id)

    def set_active(self, instance_id: str) -> bool:
        """Set the active instance.

        Args:
            instance_id: ID of the instance to activate.

        Returns:
            True if activated, False if not found.
        """
        if instance_id not in self._instances:
            return False
        self._active_id = instance_id
        self._save()
        logger.info(f"Active LM Studio instance switched to: {instance_id}")
        return True

    # --- Model Discovery ---

    def discover_models(self, instance_id: str) -> list[ModelInfo]:
        """Discover available models on an LM Studio instance.

        Args:
            instance_id: Instance ID.

        Returns:
            List of ModelInfo objects.
        """
        inst = self._instances.get(instance_id)
        if not inst:
            return []

        try:
            url = f"http://{inst.hostname}:{inst.port}/v1/models"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            models = []
            for m in data.get("data", []):
                model_id = m.get("id", "")
                if not model_id:
                    continue
                model_info = ModelInfo(
                    id=model_id,
                    created=m.get("created"),
                    owned_by=m.get("owned_by", "lmstudio"),
                )
                # Try to estimate VRAM from model name
                self._estimate_vram(model_info)
                models.append(model_info)

            inst.available_models = [m.id for m in models]
            inst.is_connected = True
            inst.connected_at = datetime.now()
            self._save()
            logger.info(f"Discovered {len(models)} models on {instance_id}")
            return models

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to discover models on {instance_id}: {e}")
            inst.is_connected = False
            self._save()
            return []

    def _estimate_vram(self, model_info: ModelInfo) -> None:
        """Estimate VRAM requirement from model name.

        Args:
            model_info: ModelInfo to update.
        """
        name = model_info.id.lower()
        for size_label, vram_mb in _VRAM_ESTIMATES.items():
            if size_label.lower() in name:
                model_info.size_label = size_label
                model_info.recommended_vram_mb = vram_mb
                break

    # --- Model Selection ---

    def select_model(self, instance_id: str, model_id: str) -> bool:
        """Select a model for an instance.

        Args:
            instance_id: Instance ID.
            model_id: Model ID to select.

        Returns:
            True if selected, False if not in available list.
        """
        inst = self._instances.get(instance_id)
        if not inst:
            return False
        if model_id not in inst.available_models:
            return False
        inst.selected_model = model_id
        self._save()
        logger.info(f"Selected model '{model_id}' on instance {instance_id}")
        return True

    # --- Backward Compatibility ---

    def get_active_hostname(self) -> str:
        """Get hostname of active instance (backward compat)."""
        active = self.get_active()
        return active.hostname if active else "localhost"

    def get_active_port(self) -> int:
        """Get port of active instance (backward compat)."""
        active = self.get_active()
        return active.port if active else 1234

    def get_active_model(self) -> str:
        """Get selected model of active instance (backward compat)."""
        active = self.get_active()
        return active.selected_model if active else ""