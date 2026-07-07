"""
LM Instances API - Flask Blueprint for LM Studio instance management.
"""

import logging
from flask import Blueprint, jsonify, request
from .manager import InstanceManager

logger = logging.getLogger(__name__)

# Module-level instance manager (initialized by app.py)
_instance_manager: InstanceManager = None  # type: ignore
_client = None  # type: ignore  # LMStudioClient reference


def init_instance_manager(config_path: str, client=None) -> InstanceManager:
    """Create and initialize the InstanceManager.

    Args:
        config_path: Path to config.json.
        client: Optional LMStudioClient reference to sync with.

    Returns:
        Initialized InstanceManager.
    """
    global _instance_manager, _client
    _instance_manager = InstanceManager(config_path=config_path)
    _client = client
    return _instance_manager


def _sync_client_selected_model(mgr: InstanceManager) -> None:
    """Sync the selected model from InstanceManager to the LMStudioClient.

    Called after model selection to ensure the client uses the newly
    selected model for subsequent chat requests.
    """
    if _client is None:
        return
    active = mgr.get_active()
    if active and active.selected_model:
        _client.selected_model = active.selected_model


def get_instance_manager() -> InstanceManager:
    """Get the global InstanceManager."""
    return _instance_manager


def register_lm_blueprints(bp: Blueprint) -> None:
    """Register LM Studio instance API endpoints with a Blueprint.

    Args:
        bp: Flask Blueprint instance.
    """

    @bp.route("/api/lm_instances", methods=["GET"])
    def list_instances():
        """Get all LM Studio instances."""
        mgr = get_instance_manager()
        instances = mgr.get_all()
        active = mgr.get_active()
        return jsonify({
            "success": True,
            "instances": {
                inst_id: inst.to_dict()
                for inst_id, inst in instances.items()
            },
            "active_id": mgr._active_id if hasattr(mgr, '_active_id') else (active.id if active else None),
        })

    @bp.route("/api/lm_instances", methods=["POST"])
    def add_instance():
        """Add a new LM Studio instance."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        instance_id = data.get("id")
        hostname = data.get("hostname")
        if not instance_id or not hostname:
            return jsonify({"success": False, "error": "id and hostname are required"}), 400

        mgr = get_instance_manager()
        if mgr.get_instance(instance_id):
            return jsonify({"success": False, "error": f"Instance '{instance_id}' already exists"}), 400

        from .models import LmInstanceConfig
        config = LmInstanceConfig(
            id=instance_id,
            hostname=hostname,
            port=data.get("port", 1234),
            display_name=data.get("display_name", instance_id),
        )
        mgr.add_instance(config)
        return jsonify({"success": True, "message": f"Instance '{instance_id}' added"})

    @bp.route("/api/lm_instances/<instance_id>", methods=["GET"])
    def get_instance(instance_id: str):
        """Get a specific instance."""
        mgr = get_instance_manager()
        inst = mgr.get_instance(instance_id)
        if not inst:
            return jsonify({"success": False, "error": f"Instance '{instance_id}' not found"}), 404
        return jsonify({"success": True, "instance": inst.to_dict()})

    @bp.route("/api/lm_instances/<instance_id>", methods=["DELETE"])
    def remove_instance(instance_id: str):
        """Remove an LM Studio instance."""
        mgr = get_instance_manager()
        if instance_id == "local":
            return jsonify({"success": False, "error": "Cannot remove the default 'local' instance"}), 400
        if not mgr.remove_instance(instance_id):
            return jsonify({"success": False, "error": f"Instance '{instance_id}' not found"}), 404
        return jsonify({"success": True, "message": f"Instance '{instance_id}' removed"})

    @bp.route("/api/lm_instances/<instance_id>/activate", methods=["POST"])
    def activate_instance(instance_id: str):
        """Activate an LM Studio instance."""
        mgr = get_instance_manager()
        if not mgr.set_active(instance_id):
            return jsonify({"success": False, "error": f"Instance '{instance_id}' not found"}), 404
        return jsonify({"success": True, "message": f"Instance '{instance_id}' activated"})

    @bp.route("/api/lm_instances/<instance_id>/discover", methods=["POST"])
    def discover_models(instance_id: str):
        """Discover models on an LM Studio instance."""
        mgr = get_instance_manager()
        inst = mgr.get_instance(instance_id)
        if not inst:
            return jsonify({"success": False, "error": f"Instance '{instance_id}' not found"}), 404

        models = mgr.discover_models(instance_id)
        return jsonify({
            "success": True,
            "instance_id": instance_id,
            "models": [m.to_dict() for m in models],
            "count": len(models),
        })

    @bp.route("/api/lm_instances/<instance_id>/models", methods=["GET"])
    def get_instance_models(instance_id: str):
        """Get available models for an instance."""
        mgr = get_instance_manager()
        inst = mgr.get_instance(instance_id)
        if not inst:
            return jsonify({"success": False, "error": f"Instance '{instance_id}' not found"}), 404
        return jsonify({
            "success": True,
            "instance_id": instance_id,
            "models": inst.available_models,
            "selected": inst.selected_model,
        })

    @bp.route("/api/lm_instances/<instance_id>/select_model", methods=["POST"])
    def select_model(instance_id: str):
        """Select a model for an instance."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        model_id = data.get("model_id")
        if not model_id:
            return jsonify({"success": False, "error": "model_id is required"}), 400

        mgr = get_instance_manager()
        if not mgr.select_model(instance_id, model_id):
            return jsonify({"success": False, "error": f"Failed to select model '{model_id}' on '{instance_id}'"}), 400
        
        # Sync selected model to the LMStudioClient so it takes effect immediately
        _sync_client_selected_model(mgr)
        
        return jsonify({"success": True, "message": f"Model '{model_id}' selected"})

    @bp.route("/api/lm_instances/active", methods=["GET"])
    def get_active_instance():
        """Get the currently active LM Studio instance."""
        mgr = get_instance_manager()
        active = mgr.get_active()
        if not active:
            return jsonify({"success": False, "error": "No active instance"}), 404
        return jsonify({"success": True, "instance": active.to_dict()})

    @bp.route("/api/lm_instances/active/model", methods=["GET"])
    def get_active_model():
        """Get the selected model of the active instance."""
        mgr = get_instance_manager()
        active = mgr.get_active()
        if not active:
            return jsonify({"success": False, "error": "No active instance"}), 404
        return jsonify({
            "success": True,
            "instance_id": active.id,
            "model": active.selected_model,
            "available_models": active.available_models,
        })

    @bp.route("/api/lm_instances/active/model", methods=["POST"])
    def set_active_model():
        """Select a model on the active instance."""
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        model_id = data.get("model_id")
        if not model_id:
            return jsonify({"success": False, "error": "model_id is required"}), 400

        mgr = get_instance_manager()
        active = mgr.get_active()
        if not active:
            return jsonify({"success": False, "error": "No active instance"}), 404

        if not mgr.select_model(active.id, model_id):
            return jsonify({"success": False, "error": f"Failed to select model '{model_id}'"}), 400
        
        # Sync selected model to the LMStudioClient so it takes effect immediately
        _sync_client_selected_model(mgr)
        
        return jsonify({"success": True, "model": model_id})
