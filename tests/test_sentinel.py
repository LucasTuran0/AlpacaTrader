import pytest

from backend.agency import sentinel as sentinel_module


class _FakePrompt:
    def __init__(self, response_content):
        self._response_content = response_content

    def __or__(self, _llm):
        class _FakeChain:
            def __init__(self, response_content):
                self._response_content = response_content

            async def ainvoke(self, _payload):
                class _Resp:
                    def __init__(self, content):
                        self.content = content

                return _Resp(self._response_content)

        return _FakeChain(self._response_content)


class _Article:
    def __init__(self, headline):
        self.headline = headline


class _NewsSet:
    def __init__(self, headlines):
        self.data = {"news": [_Article(h) for h in headlines]}


class _Provider:
    def __init__(self, response):
        self._response = response

    def get_news(self, _symbols, limit=5):
        _ = limit
        return self._response


def _make_sentinel(provider):
    s = sentinel_module.SentinelShield.__new__(sentinel_module.SentinelShield)
    s.provider = provider
    s.llm = object()
    return s


def test_vix_regime_thresholds():
    s = _make_sentinel(_Provider(None))
    assert s.analyze_vix_regime(19.99) == "SAFE"
    assert s.analyze_vix_regime(20.00) == "SHIELD_ACTIVE"
    assert s.analyze_vix_regime(29.99) == "SHIELD_ACTIVE"
    assert s.analyze_vix_regime(30.00) == "CRISIS"


@pytest.mark.asyncio
async def test_news_response_shape_handling(monkeypatch):
    monkeypatch.setattr(
        sentinel_module.PromptTemplate,
        "from_template",
        lambda _template: _FakePrompt("0.25"),
    )
    s = _make_sentinel(_Provider(_NewsSet(["NVDA rallies on earnings"])))
    score = await s.analyze_sentiment(["NVDA"])
    assert score == 0.25


@pytest.mark.asyncio
async def test_sentiment_parser_handles_list_content(monkeypatch):
    monkeypatch.setattr(
        sentinel_module.PromptTemplate,
        "from_template",
        lambda _template: _FakePrompt([{"type": "text", "text": "0.42"}]),
    )
    s = _make_sentinel(_Provider(_NewsSet(["TSLA launches new model"])))
    score = await s.analyze_sentiment(["TSLA"])
    assert score == 0.42
