"""週次通知ジョブのテスト。"""

from unittest.mock import AsyncMock

import pytest

from stock.jobs.update_and_notify import _action
from stock.models import User


@pytest.mark.asyncio
@pytest.mark.parametrize("notification_sent", [True, False])
async def test_action_reports_notification_result(mocker, notification_sent: bool) -> None:
    update = mocker.patch(
        "stock.jobs.update_and_notify.PortfolioService.update_and_notify",
        new_callable=AsyncMock,
        return_value={"notification_sent": notification_sent},
    )
    db = AsyncMock()
    user = User(user_id=7, username="test", email="test@example.com", slack_user_id="U123")

    result = await _action(db, user)

    assert result.succeeded is notification_sent
    update.assert_awaited_once_with(7)
