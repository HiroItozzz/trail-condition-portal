import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TokenStats:
    def __init__(
        self,
        input_tokens: int,
        thoughts_tokens: int,
        pure_output_tokens: int,
        input_letter_count: int,
        output_letter_count: int,
        model: str,
    ):
        self.input_tokens = input_tokens
        self.thoughts_tokens = thoughts_tokens
        self.pure_output_tokens = pure_output_tokens
        self.input_letter_count = input_letter_count
        self.output_letter_count = output_letter_count
        self.model_name = model
        # 遅延計算用のキャッシュ
        self._input_fee = None
        self._thoughts_fee = None
        self._output_fee = None

    @property
    def input_fee(self) -> float:
        if self._input_fee is None:
            self._input_fee = LlmFee(self.model_name).calculate(self.input_tokens, "input")
        return self._input_fee

    @property
    def thoughts_fee(self) -> float:
        if self._thoughts_fee is None:
            self._thoughts_fee = LlmFee(self.model_name).calculate(self.thoughts_tokens, "thoughts")
        return self._thoughts_fee

    @property
    def pure_output_fee(self) -> float:
        if self._output_fee is None:
            self._output_fee = LlmFee(self.model_name).calculate(self.pure_output_tokens, "output")
        return self._output_fee

    @property
    def total_fee(self) -> float:
        return self.input_fee + self.thoughts_fee + self.pure_output_fee

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"

    def to_dict(self) -> dict:
        return {
            "model": self.model_name,
            "input_tokens": self.input_tokens,
            "thoughts_tokens": self.thoughts_tokens,
            "output_tokens": self.pure_output_tokens,
            "input_letter_count": self.input_letter_count,
            "output_letter_count": self.output_letter_count,
            "input_fee": self.input_fee,
            "thoughts_fee": self.thoughts_fee,
            "output_fee": self.pure_output_fee,
            "total_fee": self.total_fee,
        }


class BaseLlmFee(ABC):
    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def fees(self):
        pass

    @abstractmethod
    def model_list(self):
        pass

    @abstractmethod
    def calculate(self, tokens: int, token_type: str) -> float:
        pass


class LlmFee(BaseLlmFee):
    """2025/12/09現在"""

    _fees = {
        "gemini-2.5-flash": {"input": 0.03, "output": 2.5},  # $per 1M tokens
        "gemini-2.5-pro": {
            "under_0.2M": {"input": 1.25, "output": 10.00},
            "over_0.2M": {"input": 2.5, "output": 15.0},
        },
        "deepseek": {"input(cache_hit)": 0.028, "input(cache_miss)": 0.28, "output": 0.42},
    }
    _model_list = ["gemini-2.5-flash", "gemini-2.5-pro", "deepseek-chat", "deepseek-reasoner"]

    @property
    def fees(self):
        return self._fees

    @property
    def model_list(self):
        return self._model_list

    def calculate(self, tokens, token_type: str) -> float:
        model_name = self.model
        token_type = "output" if token_type == "thoughts" else token_type
        if self.model not in self.model_list:
            logger.warning("料金表に登録されていないモデルです")
            logger.warning("'gemini-2.5-proの料金で試算します")
            model_name = "gemini-2.5-pro"
        if model_name.startswith("deepseek"):
            base_fee = self.fees["deepseek"]
            token_type = "output" if token_type == "thoughts" else token_type
            if token_type == "output":
                dollar_per_1M_tokens = base_fee["output"]
            else:
                dollar_per_1M_tokens = base_fee["input(cache_miss)"]
        elif model_name == "gemini-2.5-flash":
            dollar_per_1M_tokens = self.fees[self.model][token_type]
        else:
            base_fee = self.fees["gemini-2.5-pro"]
            if tokens <= 200000:
                dollar_per_1M_tokens = base_fee["under_0.2M"][token_type]
            else:
                dollar_per_1M_tokens = base_fee["over_0.2M"][token_type]

        return dollar_per_1M_tokens * tokens / 1000000
