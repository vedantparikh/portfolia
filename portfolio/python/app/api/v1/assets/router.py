"""
Assets management router with authentication.
"""

import time
from typing import List, Literal, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from core.auth.dependencies import (
    get_current_active_user,
    get_current_verified_user,
)
from core.database.connection import get_db
from core.database.models import Asset as AssetModel
from core.database.models import User
from core.database.models.asset import AssetType
from core.logging_config import get_logger, log_api_request, log_api_response
from core.schemas.portfolio import (
    Asset as AssetSchema,
)
from core.schemas.portfolio import (
    AssetBulkCreateRequest,
    AssetBulkCreateResponse,
    AssetCreate,
    AssetHighlights,
    AssetPrice,
    AssetUpdate,
)
from core.schemas.portfolio import (
    AssetDetail as AssetDetailSchema,
)
from core.services.asset_factory import asset_from_ticker_info
from core.services.market_data_service import market_data_service
from modules.assets.quotes import Change, QuoteFilter, highlights
from modules.assets.repository import SORT_COLUMNS, AssetRepository

AssetSort = Literal[
    "symbol",
    "name",
    "created_at",
    "current_price",
    "market_cap",
    "volume_24h",
    "price_change_percentage_24h",
]

logger = get_logger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/", response_model=AssetSchema, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Create a new financial asset for the authenticated user."""
    log_api_request(
        logger,
        "POST",
        "/assets",
        current_user.id,
        f"Creating asset: {asset_data.symbol}",
    )
    start_time = time.time()

    assets = AssetRepository(db)
    existing_asset = assets.find_by_symbol(current_user.id, asset_data.symbol.upper())

    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset with this symbol already exists for your account",
        )

    ticker_data = await market_data_service.get_ticker_info(asset_data.symbol.upper())

    new_asset = asset_from_ticker_info(
        asset_data.symbol.upper(), ticker_data, current_user.id
    )

    assets.add(new_asset)

    response_time = time.time() - start_time
    log_api_response(logger, "POST", "/assets", 200, response_time)
    return new_asset


@router.post(
    "/bulk-create",
    response_model=AssetBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assets_bulk(
    asset_data: AssetBulkCreateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Create multiple financial assets in bulk for the authenticated user."""
    log_api_request(
        logger,
        "POST",
        "/assets/bulk-create",
        current_user.id,
        f"Bulk creating assets for symbols: {asset_data.symbols}",
    )
    start_time = time.time()

    unique_symbols = sorted(list(set([s.upper() for s in asset_data.symbols])))

    # Get existing assets for the user to prevent duplicates
    assets = AssetRepository(db)
    existing_symbols = assets.symbols_for_user(current_user.id, unique_symbols)

    created_assets = []
    failed_assets = []
    assets_to_create = []

    for symbol in unique_symbols:
        if symbol in existing_symbols:
            failed_assets.append({"symbol": symbol, "reason": "Asset already exists."})
            continue

        try:
            ticker_data = await market_data_service.get_ticker_info(symbol)
            if not ticker_data or not (
                ticker_data.get("long_name") or ticker_data.get("short_name")
            ):
                raise ValueError("Invalid or incomplete market data received.")

            new_asset = asset_from_ticker_info(symbol, ticker_data, current_user.id)
            assets_to_create.append(new_asset)
        except Exception as e:
            logger.warning(
                "Failed to process symbol %s for bulk creation: %s", symbol, e
            )
            if asset_data.allow_minimal_on_market_data_failure:
                etf_symbols = {"SPY", "IVV", "VOO", "QQQ", "DIA", "IWM"}
                atype = AssetType.ETF if symbol in etf_symbols else AssetType.EQUITY
                logger.info(
                    "Bulk-create fallback: minimal asset for %s (yfinance unavailable, type=%s)",
                    symbol,
                    atype,
                )
                assets_to_create.append(
                    AssetModel(
                        symbol=symbol,
                        name=symbol,
                        asset_type=atype,
                        currency="USD",
                        user_id=current_user.id,
                        is_active=True,
                    )
                )
            else:
                failed_assets.append(
                    {
                        "symbol": symbol,
                        "reason": "Failed to fetch market data or symbol not found.",
                    }
                )

    if assets_to_create:
        created_assets.extend(assets.add_all(assets_to_create))

    response_time = time.time() - start_time
    log_api_response(logger, "POST", "/assets/bulk-create", 201, response_time)

    return AssetBulkCreateResponse(created=created_assets, failed=failed_assets)


@router.get("/", response_model=List[AssetSchema])
async def get_assets(
    response: Response,
    skip: int = Query(0, ge=0, description="Number of assets to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of assets to return"
    ),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    price_min: Optional[float] = Query(None, ge=0, description="Price at least"),
    price_max: Optional[float] = Query(None, gt=0, description="Price below"),
    market_cap_min: Optional[float] = Query(
        None, ge=0, description="Market cap at least"
    ),
    market_cap_max: Optional[float] = Query(None, gt=0, description="Market cap below"),
    change: Optional[Change] = Query(
        None, description="24h change: up or down by at least 0.5%, or flat within it"
    ),
    sort_by: AssetSort = Query("symbol", description="Sort field"),
    sort_order: Literal["asc", "desc"] = Query("asc", description="Sort order"),
    include_detail: bool = Query(
        default=False, description="Include asset detail in response"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List the user's assets; the total before paging is in `X-Total-Count`."""
    repository = AssetRepository(db)
    descending = sort_order == "desc"
    quote_filter = QuoteFilter(
        price_min=price_min,
        price_max=price_max,
        market_cap_min=market_cap_min,
        market_cap_max=market_cap_max,
        change=change,
    )
    by_market_data = sort_by not in SORT_COLUMNS or quote_filter.active
    assets = repository.list_active(
        current_user.id,
        symbol=symbol,
        asset_type=asset_type,
        order_by=sort_by if sort_by in SORT_COLUMNS else "symbol",
        skip=0 if by_market_data else skip,
        limit=None if by_market_data else limit,
        descending=descending and sort_by in SORT_COLUMNS,
    )
    if not (include_detail or by_market_data):
        response.headers["X-Total-Count"] = str(
            repository.count_active(
                current_user.id, symbol=symbol, asset_type=asset_type
            )
        )
        return assets

    quotes = await _quotes(assets)
    if quote_filter.active:
        assets = [a for a in assets if quote_filter.matches(quotes.get(a.symbol))]
    asset_details = []
    for asset in assets:
        asset_detail = AssetSchema.model_validate(asset)
        info = quotes.get(asset.symbol)
        asset_detail.detail = AssetDetailSchema(**info) if info else {}
        asset_details.append(asset_detail)

    if by_market_data:
        response.headers["X-Total-Count"] = str(len(asset_details))
        if sort_by not in SORT_COLUMNS:
            asset_details = _sorted_by_detail(asset_details, sort_by, descending)
        asset_details = asset_details[skip : skip + limit]
        if not include_detail:
            for asset_detail in asset_details:
                asset_detail.detail = None
    else:
        response.headers["X-Total-Count"] = str(
            repository.count_active(
                current_user.id, symbol=symbol, asset_type=asset_type
            )
        )
    return asset_details


@router.get("/highlights", response_model=AssetHighlights)
async def get_asset_highlights(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Top gainer, loser, yield, P/E, volume, beta, growth and 52-week-high proximity over all the user's assets."""
    assets = AssetRepository(db).list_active(
        current_user.id, symbol=None, asset_type=None
    )
    quotes = await _quotes(assets)
    return highlights([(a.symbol, a.name, quotes.get(a.symbol)) for a in assets])


async def _quotes(assets) -> dict:
    found = await market_data_service.get_symbols_info([a.symbol for a in assets])
    return {item["symbol"]: item for item in found}


def _sorted_by_detail(
    assets: List[AssetSchema], field: str, descending: bool
) -> List[AssetSchema]:
    """Sort by a quote field; assets without that value go last either way."""

    def value(asset: AssetSchema):
        detail = asset.detail
        return getattr(detail, field, None) if detail else None

    known = [a for a in assets if value(a) is not None]
    unknown = [a for a in assets if value(a) is None]
    known.sort(key=value, reverse=descending)
    return known + unknown


@router.get("/{asset_id}", response_model=AssetSchema)
def get_asset(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific financial asset by ID for the authenticated user."""
    asset = AssetRepository(db).get_active(current_user.id, asset_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    return asset


@router.put("/{asset_id}", response_model=AssetSchema)
def update_asset(
    asset_id: int,
    asset_update: AssetUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Update a financial asset for the authenticated user."""
    assets = AssetRepository(db)
    asset = assets.get_active(current_user.id, asset_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    update_data = asset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    return assets.save(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Delete a financial asset for the authenticated user."""
    assets = AssetRepository(db)
    asset = assets.get_active(current_user.id, asset_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    asset.is_active = False
    assets.save(asset)

    return None


@router.get("/{asset_id}/prices", response_model=AssetPrice)
async def get_asset_prices(
    asset_id: int,
    period: str = Query("max", description="Data period"),
    interval: str = Query("1d", description="Data interval"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get price data for a specific asset for the authenticated user."""
    asset = AssetRepository(db).get_active(current_user.id, asset_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    data = await market_data_service.fetch_ticker_data(
        symbol=asset.symbol, period=period, interval=interval
    )
    if not data.empty:
        df = data[
            [
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Dividends",
                "Stock Splits",
            ]
        ].copy()
        df["adj_close"] = data.get("Adj Close", data["Close"])
        df.columns = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "dividends",
            "stock_splits",
        ]
        convert_dict = {
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "adj_close": float,
            "volume": int,
            "dividends": float,
            "stock_splits": float,
        }
        df = df.astype(convert_dict)
        df["date"] = pd.to_datetime(df["date"]).apply(pd.Timestamp.isoformat)

    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data available for {asset.symbol}",
        )

    return {
        "asset_id": asset_id,
        "symbol": asset.symbol,
        "period": period,
        "interval": interval,
        "data_points": len(df),
        "data": df.to_dict(orient="records"),
    }
