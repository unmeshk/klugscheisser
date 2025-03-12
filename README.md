# Klugscheisser

**(Ger.) Smartass (Lit. Knowledge Shi\*\*er)**

A Slack bot that learns and retrieves knowledge shared in your workspace channels. Klugscheisser stores information from conversations and allows users to query that knowledge later.

## Features

- Learns from Slack messages when mentioned with the `learn` command
- Answers questions based on stored knowledge when directly mentioned
- Handles file attachments and processes images for learning
- Uses vector embeddings and semantic search for accurate retrieval
- Runs as a standalone service with PostgreSQL for persistent storage

## Requirements

- Python 3.10+
- PostgreSQL database
- Slack app with appropriate permissions
- Google Gemini API key

## Deployment Options

### Local Development Setup

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/klugscheisser.git
   cd klugscheisser
   ```

2. Create a virtual environment and install dependencies
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up environment variables (create a `.env` file)
   ```
   DATABASE_URL=postgresql://klugbot:<password>@localhost:<port>/klugbot_kb
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_SIGNING_SECRET=your-slack-signing-secret
   GEMINI_API_KEY=your-gemini-api-key
   KLUGBOT_LOG_CHANNEL=klugbot-logs  # Optional, defaults to this value
   ```

4. Create and configure PostgreSQL database
   ```bash
   psql postgres
   CREATE DATABASE klugbot_kb;
   CREATE USER klugbot WITH PASSWORD '<password>';
   \c klugbot_kb
   GRANT USAGE ON SCHEMA public TO klugbot;
   GRANT CREATE ON SCHEMA public TO klugbot;
   GRANT ALL ON ALL TABLES IN SCHEMA public TO klugbot;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO klugbot;
   ```

5. Run the database initialization script
   ```bash
   psql -U klugbot -d klugbot_kb -a -f scripts/init-db.sql
   ```

6. Start the application
   ```bash
   python src/app.py
   ```

### Docker Deployment

1. Set environment variables
   ```bash
   export SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   export SLACK_SIGNING_SECRET=your-slack-signing-secret
   export GEMINI_API_KEY=your-gemini-api-key
   export KLUGBOT_LOG_CHANNEL=klugbot-logs  # Optional
   ```

2. Build and start with Docker Compose
   ```bash
   docker-compose up -d
   ```

3. Monitor logs
   ```bash
   docker-compose logs -f app
   ```

### Production Deployment

For production environments, consider:

1. Using a reverse proxy like Nginx
2. Adding HTTPS with Let's Encrypt
3. Implementing proper log rotation
4. Setting up monitoring and alerts
5. Using a process manager like Supervisor

## Slack App Configuration

1. Create a new Slack App at [api.slack.com/apps](https://api.slack.com/apps)

2. Configure required OAuth scopes:
   - `app_mentions:read` - View messages that directly mention @klug-bot
   - `channels:history` - View messages in public channels
   - `chat:write` - Send messages as @klug-bot
   - `groups:history` - View messages in private channels
   - `files:read` - View shared files

3. Set up Event Subscriptions:
   - Subscribe to bot events: `app_mention`, `message.channels`, `message.groups`
   - Set Request URL to `https://your-domain.com/slack/events`

4. Install the app to your workspace

5. Add the bot to relevant channels

## Usage

- **Learning**: `@klug-bot learn [information]`
- **Querying**: `@klug-bot [question]`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SLACK_BOT_TOKEN` | OAuth token starting with `xoxb-` | Yes |
| `SLACK_SIGNING_SECRET` | Signing secret for request verification | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `KLUGBOT_LOG_CHANNEL` | Channel name for bot logs | No (Default: klugbot-logs) |

## Development

### Running Tests
```bash
pytest
```

### Project Structure
- `src/` - Application source code
  - `app.py` - Main entry point and API server
  - `klugbot.py` - Bot core functionality
  - `filehandler.py` - File and image processing
  - `queryhandler.py` - Knowledge retrieval
  - `embeddingmanager.py` - Vector embeddings
  - `models.py` - Data models
  - `settings.py` - Configuration
- `scripts/` - Utility scripts
- `tests/` - Test suite

## Troubleshooting

- **Database Connection Issues**: Verify PostgreSQL is running and credentials are correct
- **Slack Connection Failures**: Check bot token and signing secret
- **API Errors**: Ensure Gemini API key is valid and has sufficient quota

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

See the LICENSE file for details.