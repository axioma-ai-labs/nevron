"""Shopify integration tool."""

import ssl
from typing import Dict, List

import shopify
import urllib3
from loguru import logger

from src.core.config import settings
from src.core.exceptions import ShopifyError


class ShopifyTool:
    """Tool for interacting with the Shopify API."""

    def __init__(self):
        """Initialize the Shopify tool with API configuration."""
        self.api_version = "2024-01"
        self.session = None
        # Disable SSL verification warnings and disable SSL globally during development
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ssl._create_default_https_context = ssl._create_unverified_context

    async def _initialize(self) -> None:
        """Initialize and authenticate the Shopify session."""
        try:
            shop_url = f"https://{settings.SHOPIFY_STORE_NAME}"
            self.session = shopify.Session(shop_url, self.api_version, settings.SHOPIFY_PASSWORD)
            shopify.ShopifyResource.activate_session(self.session)
            logger.info("Shopify client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Shopify client: {e}")
            raise ShopifyError(f"Authentication failed: {e}")

    async def close(self) -> None:
        """Close the Shopify session."""
        if self.session:
            shopify.ShopifyResource.clear_session()
            logger.info("Shopify session closed")

    async def get_products(self) -> List[Dict]:
        """
        Retrieve a list of products from the Shopify store.

        Returns:
            List[Dict]: List of product details.

        Raises:
            ShopifyError: If product retrieval fails
        """
        try:
            products = shopify.Product.find()
            return [product.to_dict() for product in products]
        except Exception as e:
            logger.error(f"Error retrieving products: {e}")
            await self.close()
            raise ShopifyError(f"Failed to retrieve products: {e}")

    async def get_orders(self) -> List[Dict]:
        """
        Retrieve a list of orders from the Shopify store.

        Returns:
            List[Dict]: List of order details.

        Raises:
            ShopifyError: If order retrieval fails
        """
        try:
            orders = shopify.Order.find()
            return [order.to_dict() for order in orders]
        except Exception as e:
            logger.error(f"Error retrieving orders: {e}")
            await self.close()
            raise ShopifyError(f"Failed to retrieve orders: {e}")

    async def update_inventory(self, product_id: str, inventory_level: int) -> None:
        """
        Update inventory for a specified product.

        Args:
            product_id (str): The ID of the product to update
            inventory_level (int): New inventory level

        Raises:
            ShopifyError: If inventory update fails
        """
        try:
            # Get the product and its first variant
            product = shopify.Product.find(product_id)
            variant = product.variants[0]

            # Get the inventory item ID
            inventory_item_id = variant.inventory_item_id

            # Get the location ID (usually the first/default location)
            locations = shopify.Location.find()
            location_id = locations[0].id

            # Update the inventory level
            shopify.InventoryLevel.set(
                location_id=location_id,
                inventory_item_id=inventory_item_id,
                available=inventory_level,
            )

            logger.info(
                f"Updated inventory for product {product_id} to {inventory_level} at location {location_id}"
            )
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")
            await self.close()
            raise ShopifyError(f"Failed to update inventory: {e}")
