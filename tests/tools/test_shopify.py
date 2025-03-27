"""Tests for Shopify integration tool."""

from unittest.mock import MagicMock, patch

import pytest
import shopify

from src.core.exceptions import ShopifyError
from src.tools.shopify import ShopifyTool


@pytest.fixture
def shopify_tool():
    """Fixture to create a ShopifyTool instance."""
    return ShopifyTool()


@pytest.fixture
def mock_shopify_session():
    """Mock Shopify session."""
    return MagicMock(spec=shopify.Session)


@pytest.fixture
def mock_product():
    """Mock Shopify product."""
    product = MagicMock()
    variant = MagicMock()
    variant.inventory_item_id = "inventory_123"
    product.variants = [variant]
    product.title = "Test Product"
    return product


@pytest.fixture
def mock_location():
    """Mock Shopify location."""
    location = MagicMock()
    location.id = "location_123"
    return location


@pytest.mark.asyncio
async def test_initialize_success(shopify_tool):
    """Test successful Shopify client initialization."""
    with (
        patch("shopify.Session", return_value=MagicMock()) as mock_session,
        patch("shopify.ShopifyResource.activate_session") as mock_activate,
    ):
        await shopify_tool._initialize()

        mock_session.assert_called_once()
        mock_activate.assert_called_once()
        assert shopify_tool.session is not None


@pytest.mark.asyncio
async def test_initialize_failure(shopify_tool):
    """Test Shopify client initialization failure."""
    with patch("shopify.Session", side_effect=Exception("Connection error")):
        with pytest.raises(ShopifyError, match="Authentication failed"):
            await shopify_tool._initialize()


@pytest.mark.asyncio
async def test_close(shopify_tool):
    """Test closing the Shopify session."""
    with patch("shopify.ShopifyResource.clear_session") as mock_clear:
        shopify_tool.session = MagicMock()
        await shopify_tool.close()
        mock_clear.assert_called_once()


@pytest.mark.asyncio
async def test_get_products_success(shopify_tool):
    """Test successful product retrieval."""
    mock_products = [MagicMock(to_dict=lambda: {"id": "1", "title": "Test Product"})]

    with (
        patch.object(shopify_tool, "session", MagicMock()),
        patch("shopify.Product.find", return_value=mock_products),
    ):
        products = await shopify_tool.get_products()

        assert len(products) == 1
        assert products[0]["title"] == "Test Product"


@pytest.mark.asyncio
async def test_get_products_failure(shopify_tool):
    """Test product retrieval failure."""
    with (
        patch.object(shopify_tool, "session", MagicMock()),
        patch("shopify.Product.find", side_effect=Exception("API Error")),
    ):
        with pytest.raises(ShopifyError, match="Failed to retrieve products"):
            await shopify_tool.get_products()


@pytest.mark.asyncio
async def test_get_orders_success(shopify_tool):
    """Test successful order retrieval."""
    mock_orders = [MagicMock(to_dict=lambda: {"id": "1", "order_number": "1001"})]

    with (
        patch.object(shopify_tool, "session", MagicMock()),
        patch("shopify.Order.find", return_value=mock_orders),
    ):
        orders = await shopify_tool.get_orders()

        assert len(orders) == 1
        assert orders[0]["order_number"] == "1001"


@pytest.mark.asyncio
async def test_get_orders_failure(shopify_tool):
    """Test order retrieval failure."""
    with (
        patch.object(shopify_tool, "session", MagicMock()),
        patch("shopify.Order.find", side_effect=Exception("API Error")),
    ):
        with pytest.raises(ShopifyError, match="Failed to retrieve orders"):
            await shopify_tool.get_orders()


@pytest.mark.asyncio
async def test_update_inventory_success(shopify_tool, mock_product, mock_location):
    """Test successful inventory update."""
    with (
        patch.object(shopify_tool, "session", MagicMock()),
        patch("shopify.Product.find", return_value=mock_product),
        patch("shopify.Location.find", return_value=[mock_location]),
        patch("shopify.InventoryLevel.set") as mock_set,
    ):
        await shopify_tool.update_inventory("product_123", 10)

        mock_set.assert_called_once_with(
            location_id=mock_location.id,
            inventory_item_id=mock_product.variants[0].inventory_item_id,
            available=10,
        )


@pytest.mark.asyncio
async def test_update_inventory_failure(shopify_tool):
    """Test inventory update failure."""
    with (
        patch.object(shopify_tool, "session", MagicMock()),
        patch("shopify.Product.find", side_effect=Exception("API Error")),
    ):
        with pytest.raises(ShopifyError, match="Failed to update inventory"):
            await shopify_tool.update_inventory("invalid_id", 10)
