# Shopify Integration

## Setup

1. Create a Shopify Private App
   - Go to your Shopify admin panel
   - Navigate to Apps > Develop apps
   - Click "Create an app"
   - Configure the app permissions (products, orders, inventory)
   - Generate API credentials

2. Get API Credentials
   - Note down the API key
   - Note down the API password (access token)
   - Note your store name 
   - Or: create a test store beforehead, Go To Apps & sales channels > install your app > give neccessary permisions > Go To API Credentials and note down API key/password/store name

3. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   SHOPIFY_API_KEY=your_api_key_here
   SHOPIFY_PASSWORD=your_password_here
   SHOPIFY_STORE_NAME=your-store-name
   ```

### Basic Setup
```python
from src.tools.shopify import initialize_shopify_client, get_products, get_orders, update_inventory

# Initialize Shopify client
client = initialize_shopify_client()

# Get all products
products = get_products(client)

# Get all orders
orders = get_orders(client)

# Update inventory for a product
update_inventory(
    client=client,
    product_id="product_id_here",
    inventory_level=100
)
```

## Features
- Secure authentication with Shopify API
- Retrieve product listings and details
- Access order information
- Manage inventory levels
- Error handling and logging
- SSL verification handling
- Session management

## TODOs for Future Enhancements:
- Add support for creating and updating products
- Implement customer management
- Add support for discount codes
- Add support for handling Shopify webhooks for real-time updates
- Enable advanced features like creating new products or orders
- Enhance error handling and retry mechanisms for API interactions
- Add support for fulfillment operations
- Implement multi-location inventory management
- Add support for collection management
- Implement order processing workflows

## Reference
For implementation details, see: `src/tools/shopify.py`

The implementation uses the official Shopify Python API. For more information, refer to:
- [Shopify Admin API Documentation](https://shopify.dev/api/admin-rest)
- [Shopify Python API Library](https://github.com/Shopify/shopify_python_api)
