"""
LlmFee 料金計算のテスト
"""

from trail_status.services.llm_stats import LlmFee


def test_flat_rate():
    fee = LlmFee("gemini-2.5-flash")
    assert fee.calculate(1_000_000, "input") == 0.30
    assert fee.calculate(1_000_000, "output") == 2.50


def test_tiered_under_threshold():
    fee = LlmFee("gemini-2.5-pro")
    assert fee.calculate(200_000, "input") == 1.25 * 200_000 / 1_000_000


def test_tiered_over_threshold():
    fee = LlmFee("gemini-2.5-pro")
    assert fee.calculate(200_001, "input") == 2.50 * 200_001 / 1_000_000


def test_thoughts_treated_as_output():
    fee = LlmFee("gemini-2.5-flash")
    assert fee.calculate(1_000_000, "thoughts") == fee.calculate(1_000_000, "output")


def test_none_tokens_treated_as_zero():
    fee = LlmFee("gemini-2.5-flash")
    assert fee.calculate(None, "input") == 0.0


def test_unknown_model_fallbacks_to_gemini_pro():
    fee = LlmFee("unknown-model-xyz")
    # gemini-2.5-pro over tier (1M > 200k) にフォールバック
    assert fee.calculate(1_000_000, "input") == 2.50
