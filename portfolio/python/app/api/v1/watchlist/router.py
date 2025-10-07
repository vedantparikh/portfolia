import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_user
from core.database.connection import get_db
from core.database.models import User
from core.logging_config import get_logger, log_api_request, log_api_response
from core.schemas.portfolio_performance import (
    WatchlistBulkAddResponse,
    WatchlistDeleteResponse,
    WatchlistItemDeleteResponse,
    WatchlistReorderResponse,
)
from core.schemas.watchlist import (
    WatchlistBulkAddRequest,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistItemUpdate,
    WatchlistReorderRequest,
    WatchlistResponse,
    WatchlistStatsResponse,
    WatchlistUpdate,
    WatchlistWithItemsResponse,
)
from core.services.watchlist_service import WatchlistService

logger = get_logger(__name__)

router = APIRouter(tags=["watchlists"])


@router.post("/", response_model=WatchlistResponse)
async def create_watchlist(
    watchlist_data: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new watchlist."""
    log_api_request(
        logger,
        "POST",
        "/watchlists",
        current_user.id,
        f"Creating watchlist: {watchlist_data.name}",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        watchlist = service.create_watchlist(current_user.id, watchlist_data)

        response = WatchlistResponse(
            id=watchlist.id,
            user_id=watchlist.user_id,
            name=watchlist.name,
            description=watchlist.description,
            is_default=watchlist.is_default,
            is_public=watchlist.is_public,
            color=watchlist.color,
            sort_order=watchlist.sort_order,
            item_count=0,
            created_at=watchlist.created_at,
            updated_at=watchlist.updated_at,
        )

        response_time = time.time() - start_time
        log_api_response(logger, "POST", "/watchlists", 200, response_time)
        return response

    except Exception as e:
        logger.error(f"Failed to create watchlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create watchlist",
        )


@router.get("/", response_model=List[WatchlistResponse])
async def get_user_watchlists(
    include_items: bool = Query(False, description="Include watchlist items"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all watchlists for the current user."""
    log_api_request(
        logger,
        "GET",
        "/watchlists",
        current_user.id,
        f"Getting watchlists (include_items: {include_items})",
    )
    start_time = time.time()

    try:
        service = WatchlistService(db)
        watchlists = service.get_user_watchlists(current_user.id, include_items)

        response_time = time.time() - start_time
        log_api_response(
            logger, "GET", "/watchlists", 200, response_time, data_size=len(watchlists)
        )
        return watchlists

    except Exception as e:
        logger.error(f"Failed to get watchlists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve watchlists",
        )


@router.get("/{watchlist_id}", response_model=WatchlistWithItemsResponse)
async def get_watchlist(
    watchlist_id: int,
    include_real_time_data: bool = Query(
        False, description="Include real-time stock data"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific watchlist with its items."""
    log_api_request(
        logger,
        "GET",
        f"/watchlists/{watchlist_id}",
        current_user.id,
        f"Getting watchlist (real-time: {include_real_time_data})",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)

        if include_real_time_data:
            watchlist = await service.get_watchlist_with_real_time_data(
                watchlist_id, current_user.id
            )
        else:
            watchlist = service.get_watchlist(watchlist_id, current_user.id)

        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found"
            )

        response_time = time.time() - start_time
        log_api_response(
            logger, "GET", f"/watchlists/{watchlist_id}", 200, response_time
        )
        return watchlist

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get watchlist {watchlist_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve watchlist",
        )


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: int,
    update_data: WatchlistUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a watchlist."""
    log_api_request(
        logger,
        "PUT",
        f"/watchlists/{watchlist_id}",
        current_user.id,
        f"Updating watchlist: {update_data.dict(exclude_unset=True)}",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        watchlist = service.update_watchlist(watchlist_id, current_user.id, update_data)

        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found"
            )

        response = WatchlistResponse(
            id=watchlist.id,
            user_id=watchlist.user_id,
            name=watchlist.name,
            description=watchlist.description,
            is_default=watchlist.is_default,
            is_public=watchlist.is_public,
            color=watchlist.color,
            sort_order=watchlist.sort_order,
            item_count=len(watchlist.items),
            created_at=watchlist.created_at,
            updated_at=watchlist.updated_at,
        )
        response_time = time.time() - start_time
        log_api_response(
            logger, "PUT", f"/watchlists/{watchlist_id}", 200, response_time
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update watchlist {watchlist_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update watchlist",
        )


@router.delete("/{watchlist_id}", response_model=WatchlistDeleteResponse)
async def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a watchlist."""
    log_api_request(
        logger,
        "DELETE",
        f"/watchlists/{watchlist_id}",
        current_user.id,
        "Deleting watchlist",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        success = service.delete_watchlist(watchlist_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found"
            )
        response_time = time.time() - start_time

        log_api_response(
            logger, "DELETE", f"/watchlists/{watchlist_id}", 200, response_time
        )
        return WatchlistDeleteResponse(message="Watchlist deleted successfully")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete watchlist {watchlist_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete watchlist",
        )


@router.post("/{watchlist_id}/items", response_model=WatchlistItemResponse)
async def add_item_to_watchlist(
    watchlist_id: int,
    item_data: WatchlistItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a stock symbol to a watchlist."""
    log_api_request(
        logger,
        "POST",
        f"/watchlists/{watchlist_id}/items",
        current_user.id,
        f"Adding symbol: {item_data.symbol}",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        item = await service.add_item_to_watchlist(
            watchlist_id, current_user.id, item_data
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found"
            )

        response = WatchlistItemResponse(
            id=item.id,
            watchlist_id=item.watchlist_id,
            sort_order=item.sort_order,
            added_date=item.added_date,
            updated_at=item.updated_at,
            added_price=item.added_price,
            current_price=item.current_price,
            price_change_since_added=item.price_change_since_added,
            price_change_percent_since_added=item.price_change_percent_since_added,
            symbol=item.symbol,
            company_name=item.company_name,
            notes=item.notes,
            personal_rating=item.personal_rating,
            investment_thesis=item.investment_thesis,
            tags=item.tags,
            alerts_enabled=item.alerts_enabled,
            alert_price_high=item.alert_price_high,
            alert_price_low=item.alert_price_low,
            alert_price_change_percent=item.alert_price_change_percent,
        )

        response_time = time.time() - start_time
        log_api_response(
            logger,
            "POST",
            f"/watchlists/{watchlist_id}/items",
            200,
            response_time,
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add item to watchlist {watchlist_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to watchlist",
        )


@router.post("/{watchlist_id}/items/bulk", response_model=WatchlistBulkAddResponse)
async def bulk_add_items_to_watchlist(
    watchlist_id: int,
    bulk_data: WatchlistBulkAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add multiple stock symbols to a watchlist."""
    log_api_request(
        logger,
        "POST",
        f"/watchlists/{watchlist_id}/items/bulk",
        current_user.id,
        f"Adding {len(bulk_data.symbols)} symbols",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        added_items = []
        failed_symbols = []

        for symbol in bulk_data.symbols:
            try:
                item_data = WatchlistItemCreate(symbol=symbol)
                item = service.add_item_to_watchlist(
                    watchlist_id, current_user.id, item_data
                )
                if item:
                    added_items.append(item.symbol)
            except Exception as e:
                failed_symbols.append({"symbol": symbol, "error": str(e)})

        result = WatchlistBulkAddResponse(
            added_items=added_items,
            failed_symbols=failed_symbols,
            total_requested=len(bulk_data.symbols),
            successfully_added=len(added_items),
            failed=len(failed_symbols),
        )

        response_time = time.time() - start_time
        log_api_response(
            logger,
            "POST",
            f"/watchlists/{watchlist_id}/items/bulk",
            200,
            response_time,
        )
        return result

    except Exception as e:
        logger.error(f"Failed to bulk add items to watchlist {watchlist_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add items to watchlist",
        )


@router.put("/{watchlist_id}/items/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    watchlist_id: int,
    item_id: int,
    update_data: WatchlistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a watchlist item."""
    log_api_request(
        logger,
        "PUT",
        f"/watchlists/{watchlist_id}/items/{item_id}",
        current_user.id,
        f"Updating item: {update_data.dict(exclude_unset=True)}",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        item = service.update_watchlist_item(item_id, current_user.id, update_data)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found"
            )

        response = WatchlistItemResponse(
            id=item.id,
            watchlist_id=item.watchlist_id,
            symbol=item.symbol,
            company_name=item.company_name,
            notes=item.notes,
            personal_rating=item.personal_rating,
            investment_thesis=item.investment_thesis,
            tags=item.tags,
            alerts_enabled=item.alerts_enabled,
            alert_price_high=item.alert_price_high,
            alert_price_low=item.alert_price_low,
            alert_price_change_percent=item.alert_price_change_percent,
            sort_order=item.sort_order,
            added_date=item.added_date,
            updated_at=item.updated_at,
            added_price=item.added_price,
            current_price=item.current_price,
            price_change_since_added=item.price_change_since_added,
            price_change_percent_since_added=item.price_change_percent_since_added,
        )

        response_time = time.time() - start_time
        log_api_response(
            logger,
            "PUT",
            f"/watchlists/{watchlist_id}/items/{item_id}",
            200,
            response_time,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update watchlist item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update watchlist item",
        )


@router.delete(
    "/{watchlist_id}/items/{item_id}", response_model=WatchlistItemDeleteResponse
)
async def remove_item_from_watchlist(
    watchlist_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a stock symbol from a watchlist."""
    log_api_request(
        logger,
        "DELETE",
        f"/watchlists/{watchlist_id}/items/{item_id}",
        current_user.id,
        "Removing item from watchlist",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        success = service.remove_item_from_watchlist(item_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found"
            )

        response_time = time.time() - start_time
        log_api_response(
            logger,
            "DELETE",
            f"/watchlists/{watchlist_id}/items/{item_id}",
            200,
            response_time,
        )
        return WatchlistItemDeleteResponse(
            message="Item removed from watchlist successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to remove item {item_id} from watchlist {watchlist_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove item from watchlist",
        )


@router.post("/{watchlist_id}/reorder", response_model=WatchlistReorderResponse)
async def reorder_watchlist_items(
    watchlist_id: int,
    reorder_data: WatchlistReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reorder items in a watchlist."""
    log_api_request(
        logger,
        "POST",
        f"/watchlists/{watchlist_id}/reorder",
        current_user.id,
        f"Reordering {len(reorder_data.item_ids)} items",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        success = service.reorder_watchlist_items(
            watchlist_id, current_user.id, reorder_data.item_ids
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found"
            )

        response_time = time.time() - start_time
        log_api_response(
            logger,
            "POST",
            f"/watchlists/{watchlist_id}/reorder",
            200,
            response_time,
        )
        return WatchlistReorderResponse(
            message="Watchlist items reordered successfully"
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reorder watchlist items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder watchlist items",
        )


@router.get("/public", response_model=List[WatchlistResponse])
async def get_public_watchlists(
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of watchlists to return"
    ),
    db: Session = Depends(get_db),
):
    """Get public watchlists from all users."""
    log_api_request(
        logger,
        "GET",
        "/watchlists/public",
        None,
        f"Getting public watchlists (limit: {limit})",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        watchlists = service.get_public_watchlists(limit)

        response_time = time.time() - start_time
        log_api_response(logger, "GET", "/watchlists/public", 200, response_time)
        return watchlists

    except Exception as e:
        logger.error(f"Failed to get public watchlists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve public watchlists",
        )


@router.get("/stats", response_model=WatchlistStatsResponse)
async def get_watchlist_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get watchlist statistics for the current user."""
    log_api_request(
        logger,
        "GET",
        "/watchlists/stats",
        current_user.id,
        "Getting watchlist statistics",
    )
    start_time = time.time()
    try:
        service = WatchlistService(db)
        stats = service.get_watchlist_statistics(current_user.id)

        response_time = time.time() - start_time
        log_api_response(logger, "GET", "/watchlists/stats", 200, response_time)
        return stats

    except Exception as e:
        logger.error(f"Failed to get watchlist statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve watchlist statistics",
        )
