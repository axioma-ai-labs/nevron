from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.core.exceptions import ShopifyError
from src.execution.base import ActionExecutor
from src.tools.shopify import ShopifyTool


class GetShopifyProductExecutor(ActionExecutor):
    """Executor for creating Shopify products."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> ShopifyTool:
        """Initialize Shopify tool client."""
        return ShopifyTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return []

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Shopify product creation."""
        try:
            logger.info("Getting Shopify product")
            products = await self.client.get_products()

            if products:
                return True, "Successfully retrieved products"
            return False, "Failed to retrieve Shopify products"

        except ShopifyError as e:
            error_msg = f"Failed to retrieve Shopify products: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while retrieving Shopify products: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class GetShopifyOrdersExecutor(ActionExecutor):
    """Executor for retrieving Shopify orders."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> ShopifyTool:
        """Initialize Shopify tool client."""
        return ShopifyTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return []  # No specific context required for order retrieval

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Shopify order retrieval."""
        try:
            logger.info("Retrieving Shopify orders")
            orders = await self.client.get_orders()

            if orders:
                return True, f"Successfully retrieved {len(orders)} orders"
            return False, "No orders found"

        except ShopifyError as e:
            error_msg = f"Failed to retrieve Shopify orders: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while retrieving Shopify orders: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class UpdateShopifyProductExecutor(ActionExecutor):
    """Executor for updating Shopify products."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> ShopifyTool:
        """Initialize Shopify tool client."""
        return ShopifyTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["product_id", "inventory_level"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Shopify product update."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            product_id = context.get("product_id")
            inventory_level = context.get("inventory_level")

            logger.info(f"Updating Shopify product {product_id} inventory")
            await self.client.update_inventory(product_id, inventory_level)

            return True, f"Successfully updated inventory for product {product_id}"

        except ShopifyError as e:
            error_msg = f"Failed to update Shopify product: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while updating Shopify product: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
