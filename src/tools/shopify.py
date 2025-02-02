"""Shopify integration tool."""

import ssl
from typing import Dict, List

import shopify
import urllib3
from loguru import logger

from src.core.config import settings
from src.core.exceptions import ShopifyError


# Disable SSL verification warnings and disable SSL globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


def initialize_shopify_client(
    api_key: str = settings.SHOPIFY_API_KEY,
    password: str = settings.SHOPIFY_PASSWORD,
    store_name: str = settings.SHOPIFY_STORE_NAME,
) -> shopify.Session:
    """
    Authenticate and return a Shopify client instance.

    Args:
        api_key (str): API key for the Shopify store.
        password (str): API password for the Shopify store.
        store_name (str): The Shopify store name.

    Returns:
        shopify.Session: Authenticated Shopify session.
    """
    try:
        api_version = "2024-01"
        shop_url = f"https://{store_name}"

        # Initialize and activate session
        session = shopify.Session(shop_url, api_version, password)
        shopify.ShopifyResource.activate_session(session)

        return session
    except Exception as e:
        logger.error(f"Failed to initialize Shopify client: {e}")
        raise ShopifyError(f"Authentication failed: {e}")


def get_products(client: shopify.Session) -> List[Dict]:
    """
    Retrieve a list of products from the Shopify store.

    Args:
        client (shopify.Session): Authenticated Shopify session.

    Returns:
        List[Dict]: List of product details.
    """
    try:
        products = shopify.Product.find()
        return [product.to_dict() for product in products]
    except Exception as e:
        logger.error(f"Error retrieving products: {e}")
        shopify.ShopifyResource.clear_session()
        raise ShopifyError(f"Failed to retrieve products: {e}")


def get_orders(client: shopify.Session) -> List[Dict]:
    """
    Retrieve a list of orders from the Shopify store.

    Args:
        client (shopify.Session): Authenticated Shopify session.

    Returns:
        List[Dict]: List of order details.
    """
    try:
        orders = shopify.Order.find()
        return [order.to_dict() for order in orders]
    except Exception as e:
        logger.error(f"Error retrieving orders: {e}")
        shopify.ShopifyResource.clear_session()
        raise ShopifyError(f"Failed to retrieve orders: {e}")


def update_inventory(client: shopify.Session, product_id: str, inventory_level: int) -> None:
    """
    Update inventory for a specified product.

    Args:
        client (shopify.Session): Authenticated Shopify session.
        product_id (str): The ID of the product to update.
        inventory_level (int): New inventory level.
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
            location_id=location_id, inventory_item_id=inventory_item_id, available=inventory_level
        )

        logger.info(
            f"Updated inventory for product {product_id} to {inventory_level} at location {location_id}"
        )
    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        shopify.ShopifyResource.clear_session()
        raise ShopifyError(f"Failed to update inventory: {e}")
