# WhatsApp Integration

## Setup

1. Create WhatsApp API Account
   - Go to [Green API](https://green-api.com/)
   - Register and create an account
   - Create an instance
   - Get your Instance ID and API Token

2. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   WHATSAPP_ID_INSTANCE=your_instance_id_here
   WHATSAPP_API_TOKEN=your_api_token_here
   ```

3. Phone Number Setup
   - Install WhatsApp on your phone
   - Scan QR code from Green API dashboard
   - Verify your phone number is connected

### Basic Setup
```python
from src.tools.whatsapp import WhatsAppClient

# Initialize WhatsApp client
whatsapp = WhatsAppClient()
await whatsapp.initialize()

# Define message handler
async def handle_message(message_data):
    if message_data['content'].lower() == 'hello':
        await whatsapp.send_message(
            recipient_id=message_data['phone'],
            content="Hello! How can I help you?"
        )

# Start listening for messages
await whatsapp.listen_to_messages(callback=handle_message)
```

## Example Usage
A WhatsApp bot that handles incoming messages:

```python
# Send a message
message_id = await whatsapp.send_message(
    recipient_id="1234567890",
    content="Hello from Nevron!"
)

# Format phone numbers
formatted_number = format_phone_number("+1-234-567-890")  # Returns "1234567890@c.us"
```

This example demonstrates:
- Message sending
- Message listening
- Phone number formatting
- Basic interaction flow

## Features
- Send messages to WhatsApp users
- Listen for incoming messages
- Format incorrect phone numbers for API automatically
- Handle message notifications
- Automatic notification cleanup from the queue
- Error handling and logging
- SSL verification management (currently disabled)

## TODOs for Future Enhancements:
- Add support for media messages
- Implement group chat functionality
- Enable message reactions and interactive message components.
- Add message status tracking
- Support for business features
- Add contact management
- Implement message templates
- Add support for voice messages
- Enable message scheduling

## Reference
For implementation details, see: tools/whatsapp.py
