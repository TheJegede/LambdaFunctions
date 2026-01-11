# LambdaFunctions

An AWS Lambda-based AI chatbot service that provides intelligent conversational capabilities. 

## 📋 Overview

This repository contains the Lambda function implementation for an AI chatbot.  The service is designed to run on AWS Lambda, providing serverless AI-powered conversational capabilities with modular architecture for easy maintenance and extensibility.

## 🏗️ Architecture

The project is structured with a modular design pattern:

- **`lambda_fucintion.py`** - Main Lambda handler entry point
- **`main.py`** - Core application logic and orchestration
- **`ai_service.py`** - AI/ML service integration and model interactions
- **`logic.py`** - Business logic and conversation flow management
- **`prompts.py`** - Prompt templates and configuration for AI interactions

## 🚀 Features

- **Serverless Architecture** - Runs on AWS Lambda for scalability and cost-efficiency
- **Modular Design** - Separated concerns for easy maintenance
- **AI-Powered Conversations** - Intelligent chatbot capabilities
- **Extensible Structure** - Easy to add new features and integrations

## 📦 Installation

### Prerequisites

- Python 3.x
- AWS CLI configured with appropriate credentials
- AWS Lambda execution role with necessary permissions

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/TheJegede/LambdaFunctions. git
cd LambdaFunctions
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🔧 Configuration

### Environment Variables

Configure the following environment variables in your Lambda function:

```bash
# Add your specific environment variables here
# Example:
# AI_MODEL_ENDPOINT=your-endpoint
# API_KEY=your-api-key
```

## 📤 Deployment

### Deploy to AWS Lambda

1. **Package the function:**
```bash
zip -r function.zip *.py
```

2. **Deploy using AWS CLI:**
```bash
aws lambda create-function \
  --function-name ai-chatbot-function \
  --runtime python3.x \
  --role arn:aws:iam:: YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_fucintion.lambda_handler \
  --zip-file fileb://function.zip
```

3. **Update an existing function:**
```bash
aws lambda update-function-code \
  --function-name ai-chatbot-function \
  --zip-file fileb://function.zip
```

### Using AWS SAM (Recommended)

Create a `template.yaml` file and deploy using AWS SAM CLI:

```bash
sam build
sam deploy --guided
```

## 🎯 Usage

### Lambda Event Structure

The Lambda function expects events in the following format:

```json
{
  "message": "User input message",
  "sessionId": "unique-session-identifier",
  "context": {}
}
```

### Response Structure

```json
{
  "statusCode": 200,
  "body": {
    "response": "AI generated response",
    "sessionId": "unique-session-identifier"
  }
}
```

## 🧪 Testing

### Local Testing

```python
# Example test
from lambda_fucintion import lambda_handler

event = {
    "message": "Hello, chatbot!",
    "sessionId": "test-session"
}

response = lambda_handler(event, None)
print(response)
```

### Integration Testing

Test your Lambda function using the AWS Console or AWS CLI:

```bash
aws lambda invoke \
  --function-name ai-chatbot-function \
  --payload '{"message":  "Hello"}' \
  response.json
```

## 📁 Project Structure

```
LambdaFunctions/
├── lambda_fucintion.py    # Lambda handler entry point
├── main.py                # Main application logic
├── ai_service.py          # AI service integration (12. 3 KB)
├── logic.py               # Business logic (4.2 KB)
├── prompts.py             # Prompt templates (729 B)
└── README.md              # This file
```

## 🔐 Security Considerations

- Store sensitive credentials in AWS Secrets Manager or Parameter Store
- Use IAM roles with least privilege principle
- Enable CloudWatch Logs for monitoring
- Implement rate limiting to prevent abuse
- Validate and sanitize all user inputs

## 📊 Monitoring

Monitor your Lambda function using: 

- **CloudWatch Logs** - For detailed execution logs
- **CloudWatch Metrics** - For performance metrics
- **AWS X-Ray** - For distributed tracing (if enabled)

```bash
# View recent logs
aws logs tail /aws/lambda/ai-chatbot-function --follow
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is available for use.  Please add an appropriate license file if you plan to distribute this software.

## 👤 Author

**TheJegede**
- GitHub:  [@TheJegede](https://github.com/TheJegede)

## 🐛 Issues

Found a bug or have a feature request? Please open an issue on the [GitHub Issues](https://github.com/TheJegede/LambdaFunctions/issues) page.

## 📚 Additional Resources

- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [AWS Lambda Python Programming Model](https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model.html)
- [Best Practices for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## 🔄 Changelog

### [Unreleased]
- Initial release with core chatbot functionality

---

**Note:** This project was created on January 11, 2026. Make sure to keep dependencies updated and follow AWS best practices for production deployments. 
