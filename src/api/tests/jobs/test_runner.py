"""ジョブランナー (_runner.py) のサマリログ出力をテストする。"""

import pytest

from stock.jobs._runner import MAX_FAILED_SYMBOLS_IN_LOG, _log_summary


@pytest.mark.parametrize(
    "failure_count,failed_symbols,expected_level",
    [
        (0, set(), "info"),
        (1, set(), "error"),
        (0, {"AAPL"}, "error"),
        (2, {"AAPL", "MSFT"}, "error"),
    ],
)
def test_log_summary_level_selection(mocker, failure_count, failed_symbols, expected_level):
    """失敗の有無で info / error が切り替わる"""
    mock_logger = mocker.patch("stock.jobs._runner.logger")

    _log_summary(
        "test_job",
        target_users=1,
        failure_count=failure_count,
        failed_symbols=failed_symbols,
    )

    expected = mock_logger.error if expected_level == "error" else mock_logger.info
    not_expected = mock_logger.info if expected_level == "error" else mock_logger.error
    expected.assert_called_once()
    not_expected.assert_not_called()


def test_log_summary_sorts_symbols(mocker):
    """失敗銘柄リストはソート済みで出力される"""
    mock_logger = mocker.patch("stock.jobs._runner.logger")

    _log_summary("test_job", target_users=2, failure_count=0, failed_symbols={"MSFT", "AAPL"})

    args = mock_logger.error.call_args.args
    assert ["AAPL", "MSFT"] in args


def test_log_summary_truncates_when_over_limit(mocker):
    """失敗銘柄が上限を超えたら配列を切り詰めて省略件数を併記する"""
    mock_logger = mocker.patch("stock.jobs._runner.logger")
    failed = {f"SYM{i:03d}" for i in range(MAX_FAILED_SYMBOLS_IN_LOG + 10)}

    _log_summary("test_job", target_users=1, failure_count=0, failed_symbols=failed)

    args = mock_logger.error.call_args.args
    truncated_lists = [a for a in args if isinstance(a, list)]
    assert len(truncated_lists) == 1
    assert len(truncated_lists[0]) == MAX_FAILED_SYMBOLS_IN_LOG
    assert 10 in args  # 省略件数
