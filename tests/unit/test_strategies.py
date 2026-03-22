"""
Unit Tests - Strategy Framework
Run: pytest tests/ -v --cov=src --cov-report=html
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import pandas as pd
import pytest

from src.strategies.base_strategy import (
    BaseStrategy, register_strategy, get_strategy,
    list_strategies, STRATEGY_REGISTRY)
import src.strategies.library.momentum


@pytest.fixture
def sample_ohlcv():
    """Synthetic OHLCV data — 500 daily bars."""
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 1000*(1+np.random.normal(0.001,0.015,n)).cumprod()
    high = close*(1+np.abs(np.random.normal(0,0.005,n)))
    low = close*(1-np.abs(np.random.normal(0,0.005,n)))
    open_ = close.shift(1).fillna(close.iloc[0])*(1+np.random.normal(0,0.003,n))
    volume = np.random.randint(100_000,10_000_000,n).astype(float)
    return pd.DataFrame({"Open":open_,"High":high,"Low":low,"Close":close,"Volume":volume},index=dates)


@pytest.fixture
def mom(): return STRATEGY_REGISTRY["MomentumStrategy"](momentum_period=126,ema_period=50)
@pytest.fixture
def mr(): return STRATEGY_REGISTRY["MeanReversionStrategy"]()
@pytest.fixture
def bo(): return STRATEGY_REGISTRY["BreakoutStrategy"]()


class TestRegistry:
    def test_all_registered(self):
        assert "MomentumStrategy" in STRATEGY_REGISTRY
        assert "MeanReversionStrategy" in STRATEGY_REGISTRY
        assert "BreakoutStrategy" in STRATEGY_REGISTRY

    def test_get_strategy(self):
        s = get_strategy("MomentumStrategy", momentum_period=126)
        assert s.NAME == "MomentumStrategy"

    def test_invalid_strategy(self):
        with pytest.raises(ValueError): get_strategy("DoesNotExist")

    def test_list_strategies(self):
        strats = list_strategies()
        names = [s["name"] for s in strats]
        assert "MomentumStrategy" in names
        assert len(strats) >= 3


class TestBaseStrategy:
    def test_repr(self, mom): assert "MomentumStrategy" in repr(mom)
    def test_get_params(self, mom):
        p = mom.get_parameters()
        assert "momentum_period" in p and "ema_period" in p

    def test_validate_valid(self, mom): assert mom.validate_parameters() is True

    def test_validate_invalid(self):
        with pytest.raises(AssertionError):
            STRATEGY_REGISTRY["MomentumStrategy"](momentum_period=5).validate_parameters()

    def test_stop_loss_long(self, mom):
        sl = mom.get_stop_loss(1000.0, 1, atr=20.0)
        assert sl < 1000.0
        assert sl == pytest.approx(1000.0 - 40.0)

    def test_stop_loss_short(self, mom):
        sl = mom.get_stop_loss(1000.0, -1, atr=20.0)
        assert sl > 1000.0

    def test_take_profit_rr(self, mom):
        entry, atr = 1000.0, 20.0
        sl = mom.get_stop_loss(entry, 1, atr)
        tp = mom.get_take_profit(entry, 1, atr)
        assert (tp-entry) / (entry-sl) >= 1.5

    def test_position_sizing(self, mom):
        qty = mom.get_position_size(1_000_000, 1000.0, 960.0)
        assert qty > 0 and isinstance(qty, int)
        assert qty == 250   # 1%*1M / 40Rs = 250


class TestMomentumSignals:
    def test_index_matches(self, mom, sample_ohlcv):
        sigs = mom.generate_signals(sample_ohlcv)
        assert len(sigs) == len(sample_ohlcv)
        assert sigs.index.equals(sample_ohlcv.index)

    def test_valid_values(self, mom, sample_ohlcv):
        sigs = mom.generate_signals(sample_ohlcv)
        assert set(sigs.unique()).issubset({-1,0,1})

    def test_no_nan(self, mom, sample_ohlcv):
        sigs = mom.generate_signals(sample_ohlcv)
        assert not sigs.isna().any()

    def test_has_entries(self, mom, sample_ohlcv):
        sigs = mom.generate_signals(sample_ohlcv)
        assert (sigs == 1).sum() > 0

    def test_look_ahead_bias(self, mom, sample_ohlcv):
        """Removing last bar should not change earlier signals."""
        full = mom.generate_signals(sample_ohlcv)
        partial = mom.generate_signals(sample_ohlcv.iloc[:-1])
        # Last signal of partial == second-to-last of full
        assert int(partial.iloc[-1]) == int(full.iloc[-2])

    def test_warmup_mostly_zero(self, mom, sample_ohlcv):
        sigs = mom.generate_signals(sample_ohlcv)
        warmup = mom.get_warmup_period()
        assert (sigs.iloc[:warmup] == 0).mean() > 0.85


class TestMeanReversionSignals:
    def test_signals_ok(self, mr, sample_ohlcv):
        sigs = mr.generate_signals(sample_ohlcv)
        assert len(sigs) == len(sample_ohlcv)
        assert set(sigs.unique()).issubset({-1,0,1})
        assert not sigs.isna().any()

    def test_validate(self, mr): assert mr.validate_parameters()


class TestBreakoutSignals:
    def test_signals_ok(self, bo, sample_ohlcv):
        sigs = bo.generate_signals(sample_ohlcv)
        assert len(sigs) == len(sample_ohlcv)
        assert not sigs.isna().any()

    def test_validate(self, bo): assert bo.validate_parameters()


class TestDataIntegrity:
    def test_ohlcv_sanity(self, sample_ohlcv):
        assert (sample_ohlcv["High"] >= sample_ohlcv["Low"]).all()
        assert (sample_ohlcv["High"] >= sample_ohlcv["Close"]).all()
        assert (sample_ohlcv["Low"] <= sample_ohlcv["Close"]).all()
        assert (sample_ohlcv["Close"] > 0).all()
        assert (sample_ohlcv["Volume"] >= 0).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
