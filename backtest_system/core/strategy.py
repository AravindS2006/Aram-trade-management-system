from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseStrategy(ABC):
    def __init__(self, data: pd.DataFrame, params: dict[str, Any] | None = None):
        self.data = data.copy()
        self.params = params if params is not None else {}
        self.signals = pd.DataFrame(index=self.data.index)
        self.signals['signal'] = 0 # 1=Long, -1=Short, 0=None
        
    @abstractmethod
    def generate_indicators(self):
        """Compute TA indicators here."""
        pass
        
    @abstractmethod
    def generate_signals(self):
        """Set self.signals['signal'] based on logic."""
        pass
        
    def get_data_with_signals(self) -> pd.DataFrame:
        self.generate_indicators()
        self.generate_signals()
        return pd.concat([self.data, self.signals], axis=1)
