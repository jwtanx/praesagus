from connectors.financial.signals import classify_insider_signal


def test_non_market_form4_transaction_is_not_short_signal():
    signal, reason = classify_insider_signal(
        transaction_code="F",
        acquired_disposed="D",
        transaction_value=500_000,
        is_officer=True,
        is_director=False,
    )

    assert signal.value == "watch"
    assert "Non-market" in reason


def test_open_market_sale_keeps_short_signal():
    signal, reason = classify_insider_signal(
        transaction_code="S",
        acquired_disposed="D",
        transaction_value=500_000,
        is_officer=True,
        is_director=False,
    )

    assert signal.value == "short"
    assert "Insider sale" in reason
