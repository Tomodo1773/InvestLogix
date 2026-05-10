"""ジョブランナー (_runner.py) のサマリログ出力をテストする。

DBやセッション依存のテストは既存の API テスト経由で担保されているため、
ここでは集計後のサマリログ整形ロジックに絞ってテストする。
"""

import pytest

from stock.jobs._runner import MAX_FAILED_SYMBOLS_IN_LOG, _log_summary


def test_log_summary_no_failures(mocker):
    """失敗が0件のときは info レベルでサマリを出力する"""
    mock_logger = mocker.patch("stock.jobs._runner.logger")

    _log_summary("test_job", target_users=3, failure_count=0, failed_symbols=set())

    mock_logger.info.assert_called_once()
    mock_logger.error.assert_not_called()
    args = mock_logger.info.call_args.args
    # フォーマット文字列の引数として target_users / failed_symbol_count などが渡る
    assert "test_job" in args
    assert 3 in args  # target_users
    assert 0 in args  # failed_symbol_count


def test_log_summary_with_failed_symbols(mocker):
    """失敗銘柄があるときは error レベル、ソート済みリストで出力する"""
    mock_logger = mocker.patch("stock.jobs._runner.logger")

    _log_summary("test_job", target_users=2, failure_count=0, failed_symbols={"MSFT", "AAPL"})

    mock_logger.error.assert_called_once()
    mock_logger.info.assert_not_called()
    args = mock_logger.error.call_args.args
    # 失敗銘柄リストはソート済みで渡る
    assert ["AAPL", "MSFT"] in args
    assert 2 in args  # failed_symbol_count


def test_log_summary_with_user_failure_only(mocker):
    """銘柄失敗ゼロでもユーザー単位の失敗があれば error レベルで出力する"""
    mock_logger = mocker.patch("stock.jobs._runner.logger")

    _log_summary("test_job", target_users=2, failure_count=1, failed_symbols=set())

    mock_logger.error.assert_called_once()
    mock_logger.info.assert_not_called()


def test_log_summary_truncates_when_over_limit(mocker):
    """失敗銘柄が上限を超えたら配列を切り詰めて省略件数を併記する"""
    mock_logger = mocker.patch("stock.jobs._runner.logger")
    failed = {f"SYM{i:03d}" for i in range(MAX_FAILED_SYMBOLS_IN_LOG + 10)}

    _log_summary("test_job", target_users=1, failure_count=0, failed_symbols=failed)

    args = mock_logger.error.call_args.args
    # 引数中の list (failed_symbols) は切り詰められている
    truncated_lists = [a for a in args if isinstance(a, list)]
    assert len(truncated_lists) == 1
    assert len(truncated_lists[0]) == MAX_FAILED_SYMBOLS_IN_LOG
    # 省略件数 10 が引数に含まれる
    assert 10 in args


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
