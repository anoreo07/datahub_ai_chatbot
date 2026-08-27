"""Unit tests for Notification Repository."""
from unittest.mock import AsyncMock, MagicMock, patch

from database.repositories.notification_repository import NotificationRepository


class TestNotificationRepository:
    async def test_create_notification(self):
        """Test creating a notification."""
        with patch('database.repositories.notification_repository.AsyncSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value = mock_session

            repo = NotificationRepository(mock_session)
            assert repo._session == mock_session

    async def test_get_unread_by_user(self):
        """Test getting unread notifications for a user."""
        from database.models import Notification

        mock_notif = Notification(
            id=1, job_id=1, user_id="user1", type="test", title="Test", message="Test",
            status="running", is_read=False, read_at=None,
            job_metadata={}, created_at="2024-01-01T00:00:00Z"
        )

        with patch('database.repositories.notification_repository.AsyncSession') as MockSession:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_notif]
            mock_session.execute.return_value = mock_result
            MockSession.return_value = mock_session

            repo = NotificationRepository(mock_session)
            notifs = await repo.get_unread_by_user("user1")
            assert len(notifs) == 1
            assert notifs[0].is_read == False

    async def test_mark_read(self):
        """Test marking a notification as read."""
        from database.models import Notification

        mock_notif = Notification(
            id=1, job_id=1, user_id="user1", type="test", title="Test", message="Test",
            status="running", is_read=False, read_at=None,
            job_metadata={}, created_at="2024-01-01T00:00:00Z"
        )

        with patch('database.repositories.notification_repository.AsyncSession') as MockSession:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_notif
            mock_session.execute.return_value = mock_result
            mock_session.commit = AsyncMock()
            MockSession.return_value = mock_session

            repo = NotificationRepository(mock_session)
            result = await repo.mark_read(1)
            assert result is not None
            assert result.is_read == True
            mock_session.commit.assert_called_once()

    async def test_mark_all_read(self):
        """Test marking all notifications as read."""
        with patch('database.repositories.notification_repository.AsyncSession') as MockSession:
            mock_session = AsyncMock()
            mock_session.execute.return_value.rowcount = 3
            MockSession.return_value = mock_session

            repo = NotificationRepository(mock_session)
            count = await repo.mark_all_read("user1")
            assert count == 3
            mock_session.commit.assert_called_once()
