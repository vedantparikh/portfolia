"""
Assets management router with authentication.
"""

import time
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from core.schemas.market_data import AssetSearchResponse
from core.schemas.portfolio import (
    Asset as AssetSchema,
)
from core.schemas.portfolio import (
    AssetCreate,
    AssetPrice,
    AssetUpdate,
)
from core.schemas.portfolio import (
    AssetDetail as AssetDetailSchema,
)
from core.services.market_data_service import market_data_service

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

    # Check if asset already exists for this user
    existing_asset = (
        db.query(AssetModel)
        .filter(
            AssetModel.symbol == asset_data.symbol.upper(),
            AssetModel.user_id == current_user.id,
        )
        .first()
    )

    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset with this symbol already exists for your account",
        )

    try:
        ticker_data = await market_data_service.get_ticker_info(
            asset_data.symbol.upper()
        )
    except Exception as e:
        logger.error(
            "Failed to fetch ticker data for %s: %s", asset_data.symbol, str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch market data for symbol {asset_data.symbol}",
        ) from e

    new_asset = AssetModel(
        symbol=asset_data.symbol.upper(),
        name=ticker_data.get("long_name")
             or ticker_data.get("short_name")
             or asset_data.symbol.upper(),
        asset_type=(
            AssetType[ticker_data.get("quote_type").upper()]
            if ticker_data.get("quote_type")
            else AssetType.OTHER
        ),
        currency=ticker_data.get("currency", "USD"),
        exchange=ticker_data.get("exchange"),
        isin=ticker_data.get("isin"),
        cusip=ticker_data.get("cusip"),
        sector=ticker_data.get("sector"),
        industry=ticker_data.get("industry"),
        country=ticker_data.get("country"),
        description=ticker_data.get("long_business_summary"),
        user_id=current_user.id,
        is_active=True,
    )

    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    response_time = time.time() - start_time
    log_api_response(logger, "POST", "/assets", 200, response_time)
    return new_asset


@router.get("/", response_model=List[AssetSchema])
async def get_assets(
        skip: int = Query(0, ge=0, description="Number of assets to skip"),
        limit: int = Query(
            100, ge=1, le=1000, description="Maximum number of assets to return"
        ),
        symbol: Optional[str] = Query(None, description="Filter by symbol"),
        asset_type: Optional[str] = Query(None, description="Filter by asset type"),
        include_detail: bool = Query(
            default=False, description="Include asset detail in response"
        ),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get list of financial assets for the authenticated user with optional filtering."""
    query = db.query(AssetModel).filter(
        AssetModel.is_active == True, AssetModel.user_id == current_user.id
    )

    if symbol:
        query = query.filter(AssetModel.symbol.ilike(f"%{symbol.upper()}%"))

    if asset_type:
        query = query.filter(AssetModel.asset_type == asset_type)

    assets = query.offset(skip).limit(limit).all()

    if include_detail:
        asset_details = []
        symbols = [asset.symbol for asset in assets]
        ticker_detail_map = await market_data_service.get_symbols_info(symbols)
        for asset in assets:
            asset_detail = AssetSchema(
                id=asset.id,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
                symbol=asset.symbol,
                name=asset.name,
                asset_type=asset.asset_type,
                exchange=asset.exchange,
                isin=asset.isin,
                cusip=asset.cusip,
                sector=asset.sector,
                industry=asset.industry,
                country=asset.country,
                description=asset.description,
                is_active=asset.is_active,
            )
            if ticker_detail_map.get(asset.symbol):
                asset_detail.detail = AssetDetailSchema(**ticker_detail_map[asset.symbol])
            else:
                asset_detail.detail = {}
            asset_details.append(asset_detail)
        return asset_details
    return assets


@router.get("/{asset_id}", response_model=AssetSchema)
async def get_asset(
        asset_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get a specific financial asset by ID for the authenticated user."""
    asset = (
        db.query(AssetModel)
        .filter(
            AssetModel.id == asset_id,
            AssetModel.is_active == True,
            AssetModel.user_id == current_user.id,
        )
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    return asset


@router.put("/{asset_id}", response_model=AssetSchema)
async def update_asset(
        asset_id: int,
        asset_update: AssetUpdate,
        current_user: User = Depends(get_current_verified_user),
        db: Session = Depends(get_db),
):
    """Update a financial asset for the authenticated user."""
    asset = (
        db.query(AssetModel)
        .filter(
            AssetModel.id == asset_id,
            AssetModel.is_active == True,
            AssetModel.user_id == current_user.id,
        )
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    # Update only provided fields
    update_data = asset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)

    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
        asset_id: int,
        current_user: User = Depends(get_current_verified_user),
        db: Session = Depends(get_db),
):
    """Delete a financial asset for the authenticated user."""
    asset = (
        db.query(AssetModel)
        .filter(
            AssetModel.id == asset_id,
            AssetModel.is_active == True,
            AssetModel.user_id == current_user.id,
        )
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    # Soft delete by marking as inactive
    asset.is_active = False
    db.commit()

    return None


@router.get("/search/{query}", response_model=AssetSearchResponse)
async def search_assets(
        query: str,
        limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Search for assets by symbol or name for the authenticated user."""
    assets = (
        db.query(AssetModel)
        .filter(
            AssetModel.is_active == True,
            AssetModel.user_id == current_user.id,
            (
                    AssetModel.symbol.ilike(f"%{query.upper()}%")
                    | AssetModel.name.ilike(f"%{query}%")
            ),
        )
        .limit(limit)
        .all()
    )

    return AssetSearchResponse(assets=assets, total_count=len(assets), query=query)


@router.get("/{asset_id}/prices", response_model=AssetPrice)
async def get_asset_prices(
        asset_id: int,
        period: str = Query("max", description="Data period"),
        interval: str = Query("1d", description="Data interval"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get price data for a specific asset for the authenticated user."""
    asset = (
        db.query(AssetModel)
        .filter(
            AssetModel.id == asset_id,
            AssetModel.is_active == True,
            AssetModel.user_id == current_user.id,
        )
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    try:
        # Use the market data service to get prices from yfinance
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

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving price data: {str(e)}",
        ) from e
