import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import ShopifyError
from src.execution.ecommerce_executors import (
    GetShopifyOrdersExecutor,
    GetShopifyProductExecutor,
    UpdateShopifyProductExecutor,
)


class TestGetShopifyProductExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Shopify client
        self.patcher = patch("src.execution.ecommerce_executors.ShopifyTool")
        self.mock_shopify_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_shopify_tool.return_value = self.mock_client
        self.executor = GetShopifyProductExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, [])  # No required context for this executor

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Shopify product retrieval."""
        # Mock the get_products method to return a list of products
        mock_products: List[Dict[str, str]] = [
            {"id": "123", "title": "Test Product 1"},
            {"id": "456", "title": "Test Product 2"},
        ]
        self.mock_client.get_products = AsyncMock(return_value=mock_products)

        # Execute with empty context (no requirements)
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully retrieved products")
        self.mock_client.get_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_empty_products(self):
        """Test when no products are returned."""
        # Mock the get_products method to return an empty list
        empty_products: List[Dict[str, str]] = []
        self.mock_client.get_products = AsyncMock(return_value=empty_products)

        # Execute with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Failed to retrieve Shopify products")
        self.mock_client.get_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_shopify_error(self):
        """Test handling of Shopify errors."""
        # Mock the get_products method to raise a ShopifyError
        error_message: str = "API rate limit exceeded"
        self.mock_client.get_products = AsyncMock(side_effect=ShopifyError(error_message))

        # Execute with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to retrieve Shopify products", str(message))
        self.assertIn("API rate limit exceeded", str(message))
        self.mock_client.get_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Mock the get_products method to raise a generic exception
        error_message: str = "Unexpected error"
        self.mock_client.get_products = AsyncMock(side_effect=Exception(error_message))

        # Execute with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while retrieving Shopify products", str(message))
        self.assertIn("Unexpected error", str(message))
        self.mock_client.get_products.assert_called_once()


class TestGetShopifyOrdersExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Shopify client
        self.patcher = patch("src.execution.ecommerce_executors.ShopifyTool")
        self.mock_shopify_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_shopify_tool.return_value = self.mock_client
        self.executor = GetShopifyOrdersExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, [])  # No required context for this executor

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Shopify order retrieval."""
        # Mock the get_orders method to return a list of orders
        mock_orders: List[Dict[str, str]] = [
            {"id": "789", "order_number": "1001"},
            {"id": "012", "order_number": "1002"},
        ]
        self.mock_client.get_orders = AsyncMock(return_value=mock_orders)

        # Execute with empty context (no requirements)
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully retrieved 2 orders")
        self.mock_client.get_orders.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_orders(self):
        """Test when no orders are returned."""
        # Mock the get_orders method to return an empty list
        empty_orders: List[Dict[str, str]] = []
        self.mock_client.get_orders = AsyncMock(return_value=empty_orders)

        # Execute with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No orders found")
        self.mock_client.get_orders.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_shopify_error(self):
        """Test handling of Shopify errors."""
        # Mock the get_orders method to raise a ShopifyError
        error_message: str = "Authentication failed"
        self.mock_client.get_orders = AsyncMock(side_effect=ShopifyError(error_message))

        # Execute with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to retrieve Shopify orders", str(message))
        self.assertIn("Authentication failed", str(message))
        self.mock_client.get_orders.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Mock the get_orders method to raise a generic exception
        error_message: str = "Connection timeout"
        self.mock_client.get_orders = AsyncMock(side_effect=Exception(error_message))

        # Execute with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while retrieving Shopify orders", str(message))
        self.assertIn("Connection timeout", str(message))
        self.mock_client.get_orders.assert_called_once()


class TestUpdateShopifyProductExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Shopify client
        self.patcher = patch("src.execution.ecommerce_executors.ShopifyTool")
        self.mock_shopify_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_shopify_tool.return_value = self.mock_client
        self.executor = UpdateShopifyProductExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["product_id", "inventory_level"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Shopify product inventory update."""
        # Mock the update_inventory method which doesn't return anything on success
        self.mock_client.update_inventory = AsyncMock()

        # Execute with required context
        context: Dict[str, Any] = {"product_id": "123", "inventory_level": 50}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully updated inventory for product 123")
        self.mock_client.update_inventory.assert_called_once_with("123", 50)

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Execute with incomplete context
        context: Dict[str, str] = {
            "product_id": "123"
            # Missing 'inventory_level'
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.update_inventory.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_shopify_error(self):
        """Test handling of Shopify errors."""
        # Mock the update_inventory method to raise a ShopifyError
        error_message: str = "Product not found"
        self.mock_client.update_inventory = AsyncMock(side_effect=ShopifyError(error_message))

        # Execute with required context
        context: Dict[str, Any] = {
            "product_id": "999",  # Non-existent product
            "inventory_level": 50,
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to update Shopify product", str(message))
        self.assertIn("Product not found", str(message))
        self.mock_client.update_inventory.assert_called_once_with("999", 50)

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Mock the update_inventory method to raise a generic exception
        error_message: str = "Database connection error"
        self.mock_client.update_inventory = AsyncMock(side_effect=Exception(error_message))

        # Execute with required context
        context: Dict[str, Any] = {"product_id": "123", "inventory_level": 50}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while updating Shopify product", str(message))
        self.assertIn("Database connection error", str(message))
        self.mock_client.update_inventory.assert_called_once_with("123", 50)


if __name__ == "__main__":
    unittest.main()
