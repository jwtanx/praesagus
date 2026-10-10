"""Synthetic preview validates count integrity and escapes display content."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/daily-market-brief/preview_ta_signals.py'
spec = importlib.util.spec_from_file_location('ta_preview', SCRIPT)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def assessment():
    return dict(synthetic=True, ticker='<img src=x onerror=alert(1)>', cutoff='synthetic-cutoff',
                expected_session='synthetic-session',
                counts=dict(bullish=1, bearish=0, neutral=1, unavailable=1, evaluated=2, expected=3),
                indicators=[dict(name=name, status=status, reasons=['<script>bad</script>']) for name, status in
                            [('KDJ', 'bullish_event'), ('MACD', 'neutral'), ('BOLL', 'unavailable')]])


def test_preview_is_accessible_escaped_and_explicitly_synthetic():
    result = preview.render_preview(assessment())
    assert 'Synthetic simulation.' in result
    assert 'Evaluated 2 / 3' in result and 'Unavailable 1' in result
    assert result.count('<details>') == 3 and result.count('<summary>') == 3
    assert '<script>' not in result and '<img' not in result
    assert '&lt;script&gt;' in result and '&lt;img' in result
    assert 'Forecast direction, targets and confidence remain separate.' in result


@pytest.mark.parametrize('mutation', ['real', 'counts', 'duplicate', 'status', 'nonfinite'])
def test_invalid_assessment_cannot_be_previewed(mutation):
    value = assessment()
    if mutation == 'real': value['synthetic'] = False
    elif mutation == 'counts': value['counts']['neutral'] = 2
    elif mutation == 'duplicate': value['indicators'][1]['name'] = 'KDJ'
    elif mutation == 'status': value['indicators'][0]['status'] = 'recommend_buy'
    else: value['indicators'][0]['current_values'] = {'K': float('nan')}
    with pytest.raises(ValueError): preview.render_preview(value)


def test_cli_never_overwrites_existing_output_or_writes_inside_repo(tmp_path, monkeypatch):
    module = ModuleType('ingest.ta_signal_assessment')
    module.synthetic_demo = lambda: dict(record={}, calendar={}, cutoff='synthetic-cutoff')
    module.assess_ticker = lambda *args, **kwargs: assessment()
    monkeypatch.setitem(sys.modules, module.__name__, module)
    output = tmp_path / 'demo.html'
    assert preview.main(['--output', str(output)]) == 0
    original = output.read_bytes()
    assert preview.main(['--output', str(output)]) == 1
    assert output.read_bytes() == original
    assert preview.main(['--output', str(preview.REPO / 'preview.html')]) == 1
    assert not (preview.REPO / 'preview.html').exists()
