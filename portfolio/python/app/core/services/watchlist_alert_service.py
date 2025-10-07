from typing import List

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from core.database.models.watchlist import WatchlistAlert
from core.logging_config import get_logger

logger = get_logger(__name__)


class WatchlistAlertService:
    """Service for managing watchlist alerts and notifications."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_alerts(
        self, user_id: int, active_only: bool = True
    ) -> List[WatchlistAlert]:
        """Get all alerts for a user."""
        try:
            query = self.db.query(WatchlistAlert).filter(
                WatchlistAlert.user_id == user_id
            )

            if active_only:
                query = query.filter(WatchlistAlert.is_active == True)

            alerts = query.order_by(desc(WatchlistAlert.created_at)).all()
            return alerts

        except Exception as e:
            logger.error(f"Failed to get alerts for user {user_id}: {e}")
            raise

    def get_triggered_alerts(self, user_id: int) -> List[WatchlistAlert]:
        """Get all triggered alerts for a user."""
        try:
            alerts = (
                self.db.query(WatchlistAlert)
                .filter(
                    and_(
                        WatchlistAlert.user_id == user_id,
                        WatchlistAlert.is_triggered == True,
                    )
                )
                .order_by(desc(WatchlistAlert.triggered_at))
                .all()
            )

            return alerts

        except Exception as e:
            logger.error(f"Failed to get triggered alerts for user {user_id}: {e}")
            raise

    def reset_alert(self, alert_id: int, user_id: int) -> bool:
        """Reset a triggered alert so it can trigger again."""
        try:
            alert = (
                self.db.query(WatchlistAlert)
                .filter(
                    and_(
                        WatchlistAlert.id == alert_id, WatchlistAlert.user_id == user_id
                    )
                )
                .first()
            )

            if not alert:
                return False

            alert.is_triggered = False
            alert.triggered_at = None
            alert.triggered_value = None

            self.db.commit()

            logger.info(f"Reset alert {alert_id} for user {user_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reset alert {alert_id}: {e}")
            raise

    def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """Delete an alert."""
        try:
            alert = (
                self.db.query(WatchlistAlert)
                .filter(
                    and_(
                        WatchlistAlert.id == alert_id, WatchlistAlert.user_id == user_id
                    )
                )
                .first()
            )

            if not alert:
                return False

            self.db.delete(alert)
            self.db.commit()

            logger.info(f"Deleted alert {alert_id} for user {user_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete alert {alert_id}: {e}")
            raise

    def get_alerts_summary(self, user_id: int) -> dict:
        """Get summary of user's alerts."""
        try:
            total_alerts = (
                self.db.query(WatchlistAlert)
                .filter(WatchlistAlert.user_id == user_id)
                .count()
            )

            active_alerts = (
                self.db.query(WatchlistAlert)
                .filter(
                    and_(
                        WatchlistAlert.user_id == user_id,
                        WatchlistAlert.is_active == True,
                    )
                )
                .count()
            )

            triggered_alerts = (
                self.db.query(WatchlistAlert)
                .filter(
                    and_(
                        WatchlistAlert.user_id == user_id,
                        WatchlistAlert.is_triggered == True,
                    )
                )
                .count()
            )

            # Alerts by type
            alerts_by_type = (
                self.db.query(
                    WatchlistAlert.alert_type,
                    func.count(WatchlistAlert.id).label("count"),
                )
                .filter(WatchlistAlert.user_id == user_id)
                .group_by(WatchlistAlert.alert_type)
                .all()
            )

            return {
                "total_alerts": total_alerts,
                "active_alerts": active_alerts,
                "triggered_alerts": triggered_alerts,
                "alerts_by_type": [
                    {"type": item.alert_type, "count": item.count}
                    for item in alerts_by_type
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get alerts summary for user {user_id}: {e}")
            raise
