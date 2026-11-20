"""Unit tests for sub-4B model catalog and specifications."""

from app.models.registry import ModelRegistry, ModelSpec


def test_model_registry_default():
    default_model = ModelRegistry.get_default_model()
    assert isinstance(default_model, ModelSpec)
    assert default_model.parameter_count_b < 4.0
    assert "Qwen2.5-Coder-3B" in default_model.display_name


def test_model_registry_list():
    models = ModelRegistry.list_models()
    assert len(models) >= 3
    for m in models:
        assert m.parameter_count_b <= 4.0
