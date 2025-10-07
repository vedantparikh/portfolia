from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session, joinedload

from core.database.models.watchlist import (
    Watchlist,
    WatchlistAlert,
    WatchlistItem,
    WatchlistPerformance,
)
from core.logging_config import get_logger
from core.schemas.watchlist import (
    WatchlistAlertCreate,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistUpdate,
)
from core.services.market_data_service import MarketDataService

logger = get_logger(__name__)


class WatchlistService:
    """Enhanced service for watchlist operations with performance tracking and alerts."""

    def __init__(self, db: Session):
        self.db = db
        self.market_data_service = MarketDataService()

    def create_watchlist(
        self, user_id: int, watchlist_data: WatchlistCreate
    ) -> Watchlist:
        """Create a new watchlist for a user."""
        try:
            # Check if this is the first watchlist (make it default)
            existing_watchlists = (
                self.db.query(Watchlist).filter(Watchlist.user_id == user_id).count()
            )

            is_default = existing_watchlists == 0

            # Create watchlist
            watchlist = Watchlist(
                user_id=user_id,
                name=watchlist_data.name,
                description=watchlist_data.description,
                is_default=is_default,
                is_public=watchlist_data.is_public,
                color=watchlist_data.color,
                sort_order=existing_watchlists,
            )

            self.db.add(watchlist)
            self.db.commit()
            self.db.refresh(watchlist)

            logger.info(f"Created watchlist '{watchlist.name}' for user {user_id}")
            return watchlist

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create watchlist for user {user_id}: {e}")
            raise

    def get_user_watchlists(
        self, user_id: int, include_items: bool = False
    ) -> List[Watchlist]:
        """Get all watchlists for a user."""
        try:
            query = (
                self.db.query(Watchlist)
                .filter(Watchlist.user_id == user_id)
                .order_by(Watchlist.sort_order, Watchlist.name)
            )

            if include_items:
                query = query.options(
                    # Eager load items with ordering
                    joinedload(Watchlist.items).joinedload(WatchlistItem.watchlist)
                )

            watchlists = query.all()

            # Add item count for each watchlist
            for watchlist in watchlists:
                watchlist.item_count = len(watchlist.items)

            return watchlists

        except Exception as e:
            logger.error(f"Failed to get watchlists for user {user_id}: {e}")
            raise

    def get_watchlist(self, watchlist_id: int, user_id: int) -> Optional[Watchlist]:
        """Get a specific watchlist by ID (user must own it)."""
        try:
            watchlist = (
                self.db.query(Watchlist)
                .filter(
                    and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
                )
                .options(joinedload(Watchlist.items))  # Add this line to load items
                .first()
            )

            return watchlist

        except Exception as e:
            logger.error(
                f"Failed to get watchlist {watchlist_id} for user {user_id}: {e}"
            )
            raise

    def update_watchlist(
        self, watchlist_id: int, user_id: int, update_data: WatchlistUpdate
    ) -> Optional[Watchlist]:
        """Update a watchlist."""
        try:
            watchlist = self.get_watchlist(watchlist_id, user_id)
            if not watchlist:
                return None

            # Update fields
            for field, value in update_data.dict(exclude_unset=True).items():
                setattr(watchlist, field, value)

            watchlist.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(watchlist)

            logger.info(f"Updated watchlist '{watchlist.name}' for user {user_id}")
            return watchlist

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update watchlist {watchlist_id}: {e}")
            raise

    def delete_watchlist(self, watchlist_id: int, user_id: int) -> bool:
        """Delete a watchlist and all its items."""
        try:
            watchlist = self.get_watchlist(watchlist_id, user_id)
            if not watchlist:
                return False

            # Don't allow deletion of default watchlist if it's the only one
            if watchlist.is_default:
                other_watchlists = (
                    self.db.query(Watchlist)
                    .filter(
                        and_(Watchlist.user_id == user_id, Watchlist.id != watchlist_id)
                    )
                    .count()
                )

                if other_watchlists == 0:
                    raise ValueError("Cannot delete the only watchlist")

            watchlist_name = watchlist.name
            self.db.delete(watchlist)
            self.db.commit()

            logger.info(f"Deleted watchlist '{watchlist_name}' for user {user_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete watchlist {watchlist_id}: {e}")
            raise

    async def add_item_to_watchlist(
        self, watchlist_id: int, user_id: int, item_data: WatchlistItemCreate
    ) -> Optional[WatchlistItem]:
        """Add a stock symbol to a watchlist with initial price tracking."""
        try:
            # Verify watchlist ownership
            watchlist = self.get_watchlist(watchlist_id, user_id)
            if not watchlist:
                return None

            # Check if symbol already exists in this watchlist
            existing_item = (
                self.db.query(WatchlistItem)
                .filter(
                    and_(
                        WatchlistItem.watchlist_id == watchlist_id,
                        WatchlistItem.symbol == item_data.symbol.upper(),
                    )
                )
                .first()
            )

            if existing_item:
                raise ValueError(
                    f"Symbol {item_data.symbol} already exists in this watchlist"
                )

            # Get current max sort order
            max_sort = (
                self.db.query(func.max(WatchlistItem.sort_order))
                .filter(WatchlistItem.watchlist_id == watchlist_id)
                .scalar()
                or 0
            )

            # Try to get current market price
            current_price = None
            try:
                price_info = await self.market_data_service.get_current_price(
                    symbol=item_data.symbol.upper()
                )
                if price_info:
                    current_price = Decimal(str(price_info))
            except Exception as e:
                logger.warning(
                    f"Failed to get initial price for {item_data.symbol}: {e}"
                )

            # Create watchlist item
            item = WatchlistItem(
                watchlist_id=watchlist_id,
                symbol=item_data.symbol.upper(),
                company_name=item_data.company_name,
                notes=item_data.notes,
                personal_rating=item_data.personal_rating,
                investment_thesis=item_data.investment_thesis,
                tags=item_data.tags or [],
                added_price=current_price,
                current_price=current_price,
                sort_order=max_sort + 1,
            )

            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)

            # Create initial performance record
            if current_price:
                self._create_performance_record(item.id, current_price)

            logger.info(
                f"Added {item.symbol} to watchlist '{watchlist.name}' for user {user_id}"
            )
            return item

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add item to watchlist {watchlist_id}: {e}")
            raise

    def update_watchlist_item(
        self, item_id: int, user_id: int, update_data: WatchlistItemUpdate
    ) -> Optional[WatchlistItem]:
        """Update a watchlist item."""
        try:
            # Get item and verify ownership through watchlist
            item = (
                self.db.query(WatchlistItem)
                .join(Watchlist)
                .filter(and_(WatchlistItem.id == item_id, Watchlist.user_id == user_id))
                .first()
            )

            if not item:
                return None

            # Update fields
            for field, value in update_data.dict(exclude_unset=True).items():
                setattr(item, field, value)

            item.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(item)

            logger.info(f"Updated watchlist item {item.symbol} for user {user_id}")
            return item

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update watchlist item {item_id}: {e}")
            raise

    def remove_item_from_watchlist(self, item_id: int, user_id: int) -> bool:
        """Remove a stock symbol from a watchlist."""
        try:
            # Get item and verify ownership through watchlist
            item = (
                self.db.query(WatchlistItem)
                .join(Watchlist)
                .filter(and_(WatchlistItem.id == item_id, Watchlist.user_id == user_id))
                .first()
            )

            if not item:
                return False

            symbol = item.symbol
            watchlist_name = item.watchlist.name

            self.db.delete(item)
            self.db.commit()

            logger.info(
                f"Removed {symbol} from watchlist '{watchlist_name}' for user {user_id}"
            )
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove watchlist item {item_id}: {e}")
            raise

    def reorder_watchlist_items(
        self, watchlist_id: int, user_id: int, item_ids: List[int]
    ) -> bool:
        """Reorder items in a watchlist."""
        try:
            # Verify watchlist ownership
            watchlist = self.get_watchlist(watchlist_id, user_id)
            if not watchlist:
                return False

            # Verify all items belong to this watchlist
            items = (
                self.db.query(WatchlistItem)
                .filter(
                    and_(
                        WatchlistItem.id.in_(item_ids),
                        WatchlistItem.watchlist_id == watchlist_id,
                    )
                )
                .all()
            )

            if len(items) != len(item_ids):
                raise ValueError("Some items do not belong to this watchlist")

            # Update sort order
            for index, item_id in enumerate(item_ids):
                item = next((i for i in items if i.id == item_id), None)
                if item:
                    item.sort_order = index + 1

            self.db.commit()

            logger.info(
                f"Reordered items in watchlist '{watchlist.name}' for user {user_id}"
            )
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reorder watchlist items: {e}")
            raise

    async def update_watchlist_item_prices(self, symbol: str) -> bool:
        """Update current prices for all watchlist items with a given symbol."""
        try:
            # Get all watchlist items with this symbol
            items = (
                self.db.query(WatchlistItem)
                .filter(WatchlistItem.symbol == symbol.upper())
                .all()
            )

            if not items:
                return False

            # Get current market price
            try:
                price = await self.market_data_service.get_current_price(
                    symbol=symbol.upper()
                )
                if not price:
                    return False

                current_price = Decimal(str(price))

                # Update all items with this symbol
                for item in items:
                    if item.current_price != current_price:
                        old_price = item.current_price
                        item.current_price = current_price

                        # Calculate performance metrics
                        if item.added_price:
                            item.price_change_since_added = (
                                current_price - item.added_price
                            )
                            item.price_change_percent_since_added = (
                                item.price_change_since_added / item.added_price
                            ) * 100

                        # Create performance record
                        self._create_performance_record(item.id, current_price)

                        # Check alerts
                        self._check_price_alerts(item, old_price, current_price)

                self.db.commit()
                logger.info(
                    f"Updated prices for {len(items)} watchlist items with symbol {symbol}"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to get market data for {symbol}: {e}")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update prices for symbol {symbol}: {e}")
            raise

    def _create_performance_record(self, item_id: int, price: Decimal) -> None:
        """Create a performance record for a watchlist item."""
        try:
            performance = WatchlistPerformance(
                watchlist_item_id=item_id, date=datetime.now(timezone.utc), price=price
            )
            self.db.add(performance)
        except Exception as e:
            logger.error(f"Failed to create performance record: {e}")

    def _check_price_alerts(
        self, item: WatchlistItem, old_price: Optional[Decimal], new_price: Decimal
    ) -> None:
        """Check if any price alerts should be triggered."""
        try:
            if not item.alerts_enabled:
                return

            # Get active alerts for this item
            alerts = (
                self.db.query(WatchlistAlert)
                .filter(
                    and_(
                        WatchlistAlert.watchlist_item_id == item.id,
                        WatchlistAlert.is_active == True,
                        WatchlistAlert.is_triggered == False,
                    )
                )
                .all()
            )

            for alert in alerts:
                should_trigger = False

                if alert.alert_type == "price_high" and alert.condition == "above":
                    should_trigger = new_price > alert.threshold_value
                elif alert.alert_type == "price_low" and alert.condition == "below":
                    should_trigger = new_price < alert.threshold_value
                elif alert.alert_type == "percent_change" and item.added_price:
                    change_percent = (
                        (new_price - item.added_price) / item.added_price
                    ) * 100
                    if alert.condition == "above":
                        should_trigger = change_percent > alert.threshold_value
                    elif alert.condition == "below":
                        should_trigger = change_percent < alert.threshold_value

                if should_trigger:
                    # Trigger the alert
                    alert.is_triggered = True
                    alert.triggered_at = datetime.now(timezone.utc)
                    alert.triggered_value = new_price

                    # Log the alert (in production, this would send notifications)
                    logger.info(
                        f"Price alert triggered for {item.symbol}: "
                        f"{alert.alert_type} {alert.condition} {alert.threshold_value}"
                    )

        except Exception as e:
            logger.error(f"Failed to check price alerts: {e}")

    def create_price_alert(
        self, item_id: int, user_id: int, alert_data: WatchlistAlertCreate
    ) -> Optional[WatchlistAlert]:
        """Create a price alert for a watchlist item."""
        try:
            # Verify item ownership through watchlist
            item = (
                self.db.query(WatchlistItem)
                .join(Watchlist)
                .filter(and_(WatchlistItem.id == item_id, Watchlist.user_id == user_id))
                .first()
            )

            if not item:
                return None

            # Create alert
            alert = WatchlistAlert(
                watchlist_item_id=item_id,
                user_id=user_id,
                alert_type=alert_data.alert_type,
                threshold_value=alert_data.threshold_value,
                condition=alert_data.condition,
                notify_email=alert_data.notify_email,
                notify_push=alert_data.notify_push,
                notify_sms=alert_data.notify_sms,
            )

            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)

            logger.info(f"Created {alert.alert_type} alert for {item.symbol}")
            return alert

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create price alert: {e}")
            raise

    def get_watchlist_performance_summary(
        self, watchlist_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get performance summary for a watchlist."""
        try:
            watchlist = self.get_watchlist(watchlist_id, user_id)
            if not watchlist:
                return None

            items = watchlist.items

            if not items:
                return {
                    "total_items": 0,
                    "items_with_gains": 0,
                    "items_with_losses": 0,
                    "total_gain_loss": Decimal("0"),
                    "total_gain_loss_percent": Decimal("0"),
                    "average_gain_loss": Decimal("0"),
                }

            # Calculate performance metrics
            total_gain_loss = Decimal("0")
            items_with_gains = 0
            items_with_losses = 0
            valid_items = 0

            for item in items:
                if item.added_price and item.current_price:
                    gain_loss = item.current_price - item.added_price
                    total_gain_loss += gain_loss
                    valid_items += 1

                    if gain_loss > 0:
                        items_with_gains += 1
                    elif gain_loss < 0:
                        items_with_losses += 1

            # Calculate percentages
            total_gain_loss_percent = Decimal("0")
            average_gain_loss = Decimal("0")

            if valid_items > 0:
                # Calculate weighted average percentage
                total_percent = Decimal("0")
                for item in items:
                    if item.added_price and item.current_price:
                        percent = (
                            (item.current_price - item.added_price) / item.added_price
                        ) * 100
                        total_percent += percent

                total_gain_loss_percent = total_percent
                average_gain_loss = total_gain_loss / valid_items

            # Find best and worst performers
            best_performer = None
            worst_performer = None
            best_percent = Decimal("-999")
            worst_percent = Decimal("999")

            for item in items:
                if item.added_price and item.current_price:
                    percent = (
                        (item.current_price - item.added_price) / item.added_price
                    ) * 100
                    if percent > best_percent:
                        best_percent = percent
                        best_performer = item
                    if percent < worst_percent:
                        worst_percent = percent
                        worst_performer = item

            return {
                "total_items": len(items),
                "items_with_gains": items_with_gains,
                "items_with_losses": items_with_losses,
                "total_gain_loss": total_gain_loss,
                "total_gain_loss_percent": total_gain_loss_percent,
                "average_gain_loss": average_gain_loss,
                "best_performer": best_performer,
                "worst_performer": worst_performer,
            }

        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            raise

    async def get_watchlist_with_real_time_data(
        self, watchlist_id: int, user_id: int
    ) -> Optional[Watchlist]:
        """Get watchlist with real-time stock data and performance metrics."""
        try:
            # Get watchlist with items loaded
            watchlist = (
                self.db.query(Watchlist)
                .filter(
                    and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
                )
                .options(joinedload(Watchlist.items))
                .first()
            )

            if not watchlist:
                return None

            # Update prices for all symbols in the watchlist
            symbols = list(set([item.symbol for item in watchlist.items]))

            latest_data = await self.market_data_service.get_stock_latest_data(
                symbols=symbols
            )

            # Create a dictionary for faster lookup
            data_dict = {data["symbol"]: data for data in latest_data}

            for item in watchlist.items:
                data = data_dict.get(item.symbol)
                if data:
                    # Update only fields that exist in the database model
                    item.current_price = (
                        Decimal(str(data["current_price"]))
                        if data.get("current_price")
                        else None
                    )
                    if data.get("short_name", data.get("long_name")) and not item.company_name:
                        item.company_name = data.get("short_name", data.get("long_name"))

                    # Calculate price changes
                    if item.added_price and data.get("current_price"):
                        price_change = (
                            Decimal(str(data["current_price"])) - item.added_price
                        )
                        item.price_change_since_added = price_change
                        item.price_change_percent_since_added = (
                            (price_change / item.added_price) * 100
                            if item.added_price > 0
                            else Decimal("0")
                        )

                    item.updated_at = datetime.now(timezone.utc)
                    self.db.add(item)

                    logger.info(
                        f"Updated watchlist item {item.symbol} with real-time data"
                    )
            self.db.commit()

            # Refresh the watchlist to get updated data
            self.db.refresh(watchlist)

            # Calculate days since added for each item (this will be handled in the schema)
            # Note: days_since_added is a calculated field in the schema, not stored in DB

            return watchlist

        except Exception as e:
            logger.error(f"Failed to get watchlist with real-time data: {e}")
            raise

    def get_public_watchlists(self, limit: int = 20) -> List[Watchlist]:
        """Get public watchlists from all users."""
        try:
            watchlists = (
                self.db.query(Watchlist)
                .filter(Watchlist.is_public == True)
                .order_by(desc(Watchlist.updated_at))
                .limit(limit)
                .all()
            )

            # Add item count for each watchlist
            for watchlist in watchlists:
                watchlist.item_count = len(watchlist.items)

            return watchlists

        except Exception as e:
            logger.error(f"Failed to get public watchlists: {e}")
            raise

    def get_watchlist_statistics(self, user_id: int) -> dict:
        """Get watchlist statistics for a user."""
        try:
            # Total watchlists and items
            total_watchlists = (
                self.db.query(Watchlist).filter(Watchlist.user_id == user_id).count()
            )

            total_items = (
                self.db.query(WatchlistItem)
                .join(Watchlist)
                .filter(Watchlist.user_id == user_id)
                .count()
            )

            # Public watchlists
            public_watchlists = (
                self.db.query(Watchlist)
                .filter(and_(Watchlist.user_id == user_id, Watchlist.is_public == True))
                .count()
            )

            # Most watched symbols
            most_watched = (
                self.db.query(
                    WatchlistItem.symbol, func.count(WatchlistItem.id).label("count")
                )
                .join(Watchlist)
                .filter(Watchlist.user_id == user_id)
                .group_by(WatchlistItem.symbol)
                .order_by(desc("count"))
                .limit(5)
                .all()
            )

            # Recent additions
            recent_additions = (
                self.db.query(WatchlistItem)
                .join(Watchlist)
                .filter(Watchlist.user_id == user_id)
                .order_by(desc(WatchlistItem.added_date))
                .limit(10)
                .all()
            )

            return {
                "total_watchlists": total_watchlists,
                "total_items": total_items,
                "public_watchlists": public_watchlists,
                "most_watched_symbols": [
                    {"symbol": item.symbol, "count": item.count}
                    for item in most_watched
                ],
                "recent_additions": recent_additions,
            }

        except Exception as e:
            logger.error(f"Failed to get watchlist statistics for user {user_id}: {e}")
            raise
