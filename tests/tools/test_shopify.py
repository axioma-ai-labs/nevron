# """Tests for Shopify integration tool."""

# from unittest.mock import MagicMock, patch

# import pytest
# import shopify

# from src.core.exceptions import ShopifyError
# from src.tools.shopify import get_orders, get_products, initialize_shopify_client, update_inventory


# @pytest.fixture
# def mock_shopify_session():
#     """Mock Shopify session."""
#     return MagicMock(spec=shopify.Session)


# @pytest.fixture
# def mock_product():
#     """Mock Shopify product."""
#     product = MagicMock()
#     variant = MagicMock()
#     variant.inventory_item_id = "inventory_123"
#     product.variants = [variant]
#     product.title = "Test Product"
#     return product


# @pytest.fixture
# def mock_location():
#     """Mock Shopify location."""
#     location = MagicMock()
#     location.id = "location_123"
#     return location


# def test_initialize_shopify_client_success():
#     """Test successful Shopify client initialization."""
#     with (
#         patch("shopify.Session") as mock_session,
#         patch("shopify.ShopifyResource.activate_session") as mock_activate,
#     ):
#         # Arrange
#         api_key = ""
#         password = "shpat_test_token"
#         store_name = "test-store.myshopify.com"

#         # Act
#         session = initialize_shopify_client(api_key, password, store_name)

#         # Assert
#         mock_session.assert_called_once_with(f"https://{store_name}", "2024-01", password)
#         mock_activate.assert_called_once()
#         assert session == mock_session.return_value


# def test_initialize_shopify_client_failure():
#     """Test Shopify client initialization with invalid credentials."""
#     with patch("shopify.Session", side_effect=Exception("Invalid credentials")):
#         # Act & Assert
#         with pytest.raises(ShopifyError, match="Authentication failed"):
#             initialize_shopify_client("", "invalid_token", "test-store.myshopify.com")


# def test_get_products_success(mock_shopify_session):
#     """Test successful product retrieval."""
#     # Arrange
#     mock_products = [MagicMock(to_dict=lambda: {"id": "1", "title": "Test Product"})]

#     with patch("shopify.Product.find", return_value=mock_products):
#         # Act
#         products = get_products(mock_shopify_session)

#         # Assert
#         assert len(products) == 1
#         assert products[0]["title"] == "Test Product"


# def test_get_products_failure(mock_shopify_session):
#     """Test product retrieval failure."""
#     with patch("shopify.Product.find", side_effect=Exception("API Error")):
#         # Act & Assert
#         with pytest.raises(ShopifyError, match="Failed to retrieve products"):
#             get_products(mock_shopify_session)


# def test_get_orders_success(mock_shopify_session):
#     """Test successful order retrieval."""
#     # Arrange
#     mock_orders = [MagicMock(to_dict=lambda: {"id": "1", "order_number": "1001"})]

#     with patch("shopify.Order.find", return_value=mock_orders):
#         # Act
#         orders = get_orders(mock_shopify_session)

#         # Assert
#         assert len(orders) == 1
#         assert orders[0]["order_number"] == "1001"


# def test_get_orders_failure(mock_shopify_session):
#     """Test order retrieval failure."""
#     with patch("shopify.Order.find", side_effect=Exception("API Error")):
#         # Act & Assert
#         with pytest.raises(ShopifyError, match="Failed to retrieve orders"):
#             get_orders(mock_shopify_session)


# def test_update_inventory_success(mock_shopify_session, mock_product, mock_location):
#     """Test successful inventory update."""
#     # Arrange
#     with (
#         patch("shopify.Product.find", return_value=mock_product),
#         patch("shopify.Location.find", return_value=[mock_location]),
#         patch("shopify.InventoryLevel.set") as mock_set,
#     ):
#         # Act
#         update_inventory(mock_shopify_session, "product_123", 10)

#         # Assert
#         mock_set.assert_called_once_with(
#             location_id=mock_location.id,
#             inventory_item_id=mock_product.variants[0].inventory_item_id,
#             available=10,
#         )


# def test_update_inventory_failure(mock_shopify_session):
#     """Test inventory update failure."""
#     with patch("shopify.Product.find", side_effect=Exception("API Error")):
#         # Act & Assert
#         with pytest.raises(ShopifyError, match="Failed to update inventory"):
#             update_inventory(mock_shopify_session, "invalid_id", 10)
