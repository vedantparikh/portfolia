"""Aggregate the v1 routers. An import error fails startup instead of hiding a route."""

from fastapi import APIRouter

from api.v1.account_statements.router import router as account_statements_router
from api.v1.analytics.router import router as analytics_router
from api.v1.assets.router import router as assets_router
from api.v1.assets.search_router import router as asset_search_router
from api.v1.auth.router import router as auth_router
from api.v1.health_router import router as test_router
from api.v1.market.routers import router as market_router
from api.v1.portfolio.router import router as portfolio_router
from api.v1.portfolio_calculations.router import router as calculations_router
from api.v1.statistical_indicators.routers import router as indicators_router
from api.v1.transactions.pdf_export_router import router as transactions_pdf_router
from api.v1.transactions.router import router as transactions_router
from api.v1.watchlist.router import router as watchlist_router


def build_v1_router() -> APIRouter:
    """Mount every v1 router. Registration order is the match order."""
    router = APIRouter(prefix="/api/v1")
    router.include_router(test_router)
    router.include_router(auth_router)
    router.include_router(market_router)
    router.include_router(indicators_router)
    router.include_router(portfolio_router)
    router.include_router(assets_router)
    router.include_router(asset_search_router)
    router.include_router(transactions_router)
    router.include_router(transactions_pdf_router)
    router.include_router(analytics_router)
    router.include_router(watchlist_router)
    router.include_router(calculations_router)
    router.include_router(account_statements_router)
    return router
