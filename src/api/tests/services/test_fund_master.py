"""投資信託の台帳のテスト"""

import pytest

from stock.services.fund_master import Fund, get_fund_symbol


class TestGetFundSymbol:
    """get_fund_symbol関数のテスト"""

    def test_exact_match(self):
        assert get_fund_symbol("eMAXIS Slim 全世界株式(オール・カントリー)") == "JP90C000H1T1"

    def test_fullwidth_variants_map_to_same_symbol(self):
        """SBI証券CSVの全角/半角の表記揺れを吸収する"""
        variants = [
            "SBI・S・米国高配当株式ファンド(年4回決算型)",
            "ＳＢＩ・Ｓ・米国高配当株式ファンド(年４回決算型)",
            "ＳＢＩ・Ｓ・米国高配当株式ファンド（年４回決算型）",
        ]
        for variant in variants:
            assert get_fund_symbol(variant) == "JP90C000REE2", variant

    def test_space_variants(self):
        """空白の有無や全角空白の違いを吸収する"""
        assert get_fund_symbol("ｅＭＡＸＩＳ　Ｓｌｉｍ先進国株式インデックス") == "JP90C000ENC5"

    def test_unknown_fund(self):
        assert get_fund_symbol("未知のファンド") is None

    def test_empty_string(self):
        assert get_fund_symbol("") is None


def test_source_code_required_except_mufg():
    """三菱UFJ以外は運用会社でのコードが無いと台帳に載せられない"""
    with pytest.raises(ValueError, match="source_code"):
        Fund("テストファンド", "sbi_am")
