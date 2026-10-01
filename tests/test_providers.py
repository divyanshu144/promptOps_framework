from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest

from promptops.core.adapters import make_adapter, default_model
from promptops.core.adapters.openai import OpenAIAdapter
from promptops.core.adapters.mistral import MistralAdapter
from promptops.core.adapters.anthropic import AnthropicAdapter


@pytest.mark.parametrize('provider,cls', [('openai', OpenAIAdapter), ('mistral', MistralAdapter), ('anthropic', AnthropicAdapter), ('claude', AnthropicAdapter)])
def test_factory_defaults(provider, cls):
    assert isinstance(make_adapter(provider), cls)
    assert default_model(provider)
    assert default_model('claude') == default_model('anthropic')


@pytest.mark.asyncio
@pytest.mark.parametrize('cls', [OpenAIAdapter, MistralAdapter])
async def test_chat_routing_usage_and_cleanup(monkeypatch, cls):
    import openai
    response = NS(choices=[NS(message=NS(content='grounded answer'))], usage=NS(prompt_tokens=10, completion_tokens=5, total_tokens=15))
    client = NS(chat=NS(completions=NS(create=AsyncMock(return_value=response))), models=NS(list=AsyncMock()), close=AsyncMock())
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(openai, 'AsyncOpenAI', factory)
    adapter = cls(api_key='test-only')
    result = await adapter.generate(default_model(adapter.provider), 'system', 'question', {'max_tokens': 20, 'format': 'json', 'seed': 42})
    assert result.output == 'grounded answer'
    assert result.total_tokens == 15
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs['messages'][1]['content'] == 'question'
    assert kwargs['response_format'] == {'type': 'json_object'}
    if cls is MistralAdapter:
        assert factory.call_args.kwargs['base_url'] == 'https://api.mistral.ai/v1'
        assert kwargs['random_seed'] == 42
    else:
        assert 'base_url' not in factory.call_args.kwargs
    client.close.assert_awaited_once()
    assert await adapter.health_check()
    client.models.list.assert_awaited_once()
    client.chat.completions.create.side_effect = RuntimeError('provider failure')
    with pytest.raises(RuntimeError):
        await adapter.generate('model', '', '', {})
    assert client.close.await_count == 3


@pytest.mark.asyncio
async def test_claude_usage_and_cleanup(monkeypatch):
    import anthropic
    client = NS(messages=NS(create=AsyncMock(return_value=NS(content=[NS(text='one'), NS(type='other'), NS(text='two')], usage=NS(input_tokens=10, output_tokens=5)))), close=AsyncMock())
    monkeypatch.setattr(anthropic, 'AsyncAnthropic', MagicMock(return_value=client))
    result = await AnthropicAdapter(api_key='test-only').generate('claude', 'system', 'question', {'max_tokens': 20})
    assert result.output == 'onetwo'
    assert result.total_tokens == 15
    assert client.messages.create.call_args.kwargs['system'] == 'system'
    client.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('cls,key', [(OpenAIAdapter, 'OPENAI_API_KEY'), (MistralAdapter, 'MISTRAL_API_KEY'), (AnthropicAdapter, 'ANTHROPIC_API_KEY')])
async def test_missing_credentials_fail_without_request(monkeypatch, cls, key):
    monkeypatch.delenv(key, raising=False)
    adapter = cls()
    assert not await adapter.health_check()
    with pytest.raises(ValueError, match=key):
        await adapter.generate('model', '', '', {})


@pytest.mark.asyncio
@pytest.mark.parametrize('status,expected', [(200, True), (401, False)])
async def test_claude_health_is_non_generating(monkeypatch, status, expected):
    import httpx
    client = AsyncMock()
    client.get.return_value = NS(status_code=status)
    client.__aenter__.return_value = client
    monkeypatch.setattr(httpx, 'AsyncClient', MagicMock(return_value=client))
    assert await AnthropicAdapter(api_key='test-only').health_check() is expected
    assert client.get.call_args.args[0].endswith('/v1/models')


@pytest.mark.parametrize('provider', ['openai', 'claude', 'mistral'])
def test_cli_selects_generation_and_cross_provider_judge_defaults(monkeypatch, provider):
    from typer.testing import CliRunner
    from promptops import cli
    runner = AsyncMock(return_value={'aggregate_metrics': {}})
    monkeypatch.setattr(cli, 'run_dataset', runner)
    monkeypatch.setattr(cli, 'make_adapter', lambda name: name)
    result = CliRunner().invoke(cli.app, ['run', '--provider', provider, '--judge-provider', 'openai'])
    assert result.exit_code == 0, result.output
    args = runner.call_args.args
    assert args[1].model == default_model(provider)
    assert args[3] == default_model('openai')
    assert runner.call_args.kwargs['judge_adapter'] == 'openai'
