from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import LLMError
from src.llm.providers.llama import call_llama, validate_llama_setup


@pytest.mark.asyncio
async def test_validate_llama_setup_missing_path():
    """Test validation when model path doesn't exist."""
    with pytest.raises(LLMError, match="model path does not exist"):
        validate_llama_setup("/nonexistent/path")


@pytest.mark.asyncio
async def test_validate_llama_setup_missing_files():
    """Test validation when required files are missing."""
    with patch("pathlib.Path.exists") as mock_exists, patch("pathlib.Path.__truediv__") as mock_div:
        # Mock path exists but files don't
        mock_exists.side_effect = lambda: True
        mock_div.return_value = MagicMock(exists=lambda: False)  # All files return False for exists

        with pytest.raises(LLMError, match="Missing required Llama model files"):
            validate_llama_setup("/mock/path")


@pytest.mark.asyncio
async def test_call_llama_cuda_fallback():
    """Test CUDA fallback when not available."""
    with (
        patch("torch.cuda.is_available", return_value=False),
        patch("src.llm.providers.llama.validate_llama_setup"),
        patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer,
        patch("transformers.AutoModelForCausalLM.from_pretrained") as mock_model,
    ):
        # Setup mocks
        mock_tokenizer.return_value = MagicMock()
        mock_model.return_value = MagicMock()

        messages = [{"role": "user", "content": "Test"}]
        await call_llama(messages, device_map="cuda")

        # Verify model was loaded with CPU device map
        mock_model.assert_called_once()
        assert mock_model.call_args[1]["device_map"] == "cpu"


@pytest.mark.asyncio
async def test_call_llama_empty_response():
    """Test handling of empty model response."""
    with (
        patch("src.llm.providers.llama.validate_llama_setup"),
        patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer,
        patch("transformers.AutoModelForCausalLM.from_pretrained") as mock_model,
    ):
        # Setup mocks to return empty response
        mock_tokenizer.return_value = MagicMock()
        mock_tokenizer.return_value.decode.return_value = "Assistant:"
        mock_model.return_value = MagicMock()

        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(LLMError, match="Llama generated empty response"):
            await call_llama(messages)


@pytest.fixture
def mock_llama_setup():
    """Fixture to mock basic Llama setup."""
    with (
        patch("src.llm.providers.llama.validate_llama_setup"),
        patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer,
        patch("transformers.AutoModelForCausalLM.from_pretrained") as mock_model,
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.get_device_properties") as mock_props,
    ):
        # Mock GPU with 800GB memory (enough for all models)
        mock_props.return_value.total_memory = 800 * 1024 * 1024 * 1024  # 800GB in bytes
        mock_tokenizer.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        yield mock_tokenizer, mock_model


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_size,model_path",
    [
        ("8B", "/path/to/llama-8b"),
        ("70B", "/path/to/llama-70b"),
        ("405B", "/path/to/llama-405b"),
    ],
)
async def test_llama_model_sizes(mock_llama_setup, model_size, model_path):
    """Test Llama models of different sizes."""
    mock_tokenizer, mock_model = mock_llama_setup

    # Configure mock response based on model size
    mock_tokenizer.return_value.decode.return_value = f"Assistant: Response from {model_size} model"

    messages = [{"role": "user", "content": "Test prompt"}]
    response = await call_llama(messages, model_path=model_path)

    assert f"Response from {model_size} model" in response
    mock_model.assert_called_once()

    # Verify model loading parameters
    model_args = mock_model.call_args[1]
    assert model_args["device_map"] == "cuda"  # Should use CUDA since we mocked enough memory
    assert model_args["torch_dtype"] == "auto"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_size,memory_requirement",
    [
        ("8B", 16),  # 16GB minimum
        ("70B", 140),  # 140GB minimum
        ("405B", 780),  # 780GB minimum
    ],
)
async def test_llama_memory_requirements(mock_llama_setup, model_size, memory_requirement):
    """Test memory requirement checks for different model sizes."""
    mock_tokenizer, mock_model = mock_llama_setup

    with patch("torch.cuda.get_device_properties") as mock_props:
        # Test with 8GB GPU
        mock_props.return_value.total_memory = 8 * 1024 * 1024 * 1024  # 8GB in bytes

        messages = [{"role": "user", "content": "Test prompt"}]
        await call_llama(messages, model_path=f"/path/to/llama-{model_size}")

        # Verify device mapping based on memory requirements
        model_args = mock_model.call_args[1]
        expected_device = "cpu" if memory_requirement > 8 else "cuda"
        assert model_args["device_map"] == expected_device, (
            f"Expected {expected_device} for {model_size} model with 8GB GPU"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_size,expected_tokens",
    [
        ("8b", 2048),
        ("70b", 4096),
        ("405b", 8192),
    ],
)
async def test_llama_context_windows(mock_llama_setup, model_size, expected_tokens):
    """Test different context window sizes for each model."""
    mock_tokenizer, mock_model = mock_llama_setup

    # Create a long input message
    long_message = "Test " * 1000
    messages = [{"role": "user", "content": long_message}]

    await call_llama(messages, model_path=f"/path/to/llama-{model_size}")

    # Verify tokenizer was called with correct max_length
    call_kwargs = mock_tokenizer.return_value.call_args[1]
    assert call_kwargs["max_length"] == expected_tokens
    assert call_kwargs["truncation"] is True


@pytest.mark.asyncio
async def test_llama_generation_params():
    """Test generation parameters for different scenarios."""
    with (
        patch("src.llm.providers.llama.validate_llama_setup"),
        patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer,
        patch("transformers.AutoModelForCausalLM.from_pretrained") as mock_model,
    ):
        mock_tokenizer.return_value = MagicMock()
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value.eos_token_id = 2

        test_cases: list[dict[str, dict[str, float] | str]] = [
            {
                "desc": "Creative writing",
                "generation_params": {"temperature": 0.9, "top_p": 0.95},
                "expected": {"temperature": 0.9, "top_p": 0.95},
            },
            {
                "desc": "Factual response",
                "generation_params": {"temperature": 0.2, "top_p": 0.1},
                "expected": {"temperature": 0.2, "top_p": 0.1},
            },
        ]

        messages = [{"role": "user", "content": "Test prompt"}]

        for case in test_cases:
            await call_llama(messages, **case["generation_params"])  # type: ignore
            generate_args = mock_model.return_value.generate.call_args[1]

            for param, value in case["expected"].items():  # type: ignore
                assert generate_args[param] == value, f"Failed {case['desc']}: {param} mismatch"


@pytest.mark.asyncio
async def test_llama_error_recovery():
    """Test error recovery and fallback mechanisms."""
    with (
        patch("src.llm.providers.llama.validate_llama_setup"),
        patch("transformers.AutoTokenizer.from_pretrained"),
        patch("transformers.AutoModelForCausalLM.from_pretrained") as mock_model,
    ):
        # Simulate CPU memory error
        mock_model.side_effect = RuntimeError(
            "DefaultCPUAllocator: not enough memory: you tried to allocate 52428800 bytes."
        )

        messages = [{"role": "user", "content": "Test prompt"}]

        with pytest.raises(LLMError) as exc_info:
            await call_llama(messages)

        assert "not enough memory" in str(exc_info.value)
