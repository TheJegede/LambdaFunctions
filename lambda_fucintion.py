import json
from mangum import Mangum
from main import app

# Create handler
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """AWS Lambda entry point with robust event handling"""
    try:
        # Print the event for debugging
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Ensure required fields exist for Mangum
        if 'requestContext' not in event: 
            event['requestContext'] = {}
        
        if 'http' not in event. get('requestContext', {}):
            event['requestContext']['http'] = {}
        
        # Add missing sourceIp if not present
        if 'sourceIp' not in event['requestContext']['http']:
            event['requestContext']['http']['sourceIp'] = '127.0.0.1'
        
        # Add missing userAgent if not present
        if 'userAgent' not in event['requestContext']['http']:
            event['requestContext']['http']['userAgent'] = 'api-gateway'
        
        # Ensure headers exist
        if 'headers' not in event:
            event['headers'] = {}
        
        # Call Mangum handler
        response = handler(event, context)
        print(f"Success response: {response}")
        return response
        
    except Exception as e:
        print(f"Lambda error: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error':  str(e),
                'message': 'Internal server error'
            })
        }
