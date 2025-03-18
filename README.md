# Klugscheisser

**Klugscheißer (German for “smartass”; literally, “knowledge-shitter”)**

A Slack bot that learns knowledge shared with it and retrieves it when asked. Klugscheisser stores information (when instructed) from conversations and allows users to query that knowledge later.

## Features

- Learns from Slack messages when mentioned with the `--learn` command
- Answers questions based on stored knowledge when directly mentioned
- Parses and learns from file attachments (including `.md/.json/.csv/.rtf/.txt/.pdf`)
- Allows offline uploading of docs
- Allows deletion of learned information via the `--delete` command
- Uses vector embeddings and semantic search for accurate retrieval
- logs learning and deletion actions to a separate channel
- Runs as a standalone service with PostgreSQL and Chroma for persistent storage

## TODO
- Summarize conversations in thread into a knowledge unit and store
- handle images for learning. 

## Requirements

- Python 3.10+
- Docker and Docker Compose
- PostgreSQL database
- Chroma DB
- Slack app with appropriate permissions
- Google Gemini API key

## Deployment Options

### Local Development Setup

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/klugscheisser.git
   cd klugscheisser
   ```

2. Create and configure PostgreSQL database
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

3. Set up environment variables (create a `.env` file)
   ```bash
   DATABASE_URL=postgresql://klugbot:<password>@localhost:<port>/klugbot_kb
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_SIGNING_SECRET=your-slack-signing-secret
   GEMINI_API_KEY=your-gemini-api-key
   KLUGBOT_LOG_CHANNEL=klugbot-logs  # Optional, defaults to this value
   ```

4. Make sure you are exposing port 3000 (or whichever port you chose) using a service like ngrok for example.

4. Run Docker Compose
   ```bash
   docker compose up --build
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

- **Learning**: 
   - `@klug-bot --learn [information]`
   - `@klug-bot --learn` \<attachment>
   - [Offline import tool](Readme-Upload.md)
- **Querying**: 
   - `@klug-bot [question]` 
- **Deleting**:
   - `@klug-bot --delete url:<url>`
   - `@klug-bot --delete source:<slack|offline>`
   - `@klug-bot --delete date:<date>`
   - `@klug-bot --delete source:offline date:2025-02-22`"

## Examples
- **Learning**: 
   - `@klug-bot --learn John Smith leads Backend/SRE.`
   - `@klug-bot --learn` (a file `filename.pdf` is attached to the slack message)
   - [Offline import tool](Readme-Upload.md)
- **Querying**: 
   - `@klug-bot [question] Who leads Backend?` 
- **Deleting**:
   - `@klug-bot --delete url:https://<workspace>.slack.com/archives/C08ELTWE126/p1741003081522749` - deletes any knowledge entry that has the url metadata set to `https://<workspace>.slack.com/archives/C08ELTWE126/p1741003081522749`. Usually this url will be a corresponding `@klug-bot --learn` command from which the info was learned. 
   - `@klug-bot --delete source:offline` - deletes everything that was learned using the `add_to_db.py` tool (which automatically adds the `offline` tag).
   - `@klug-bot --delete date:2025-02-22` - deletes everything with the date metadata set to `2025-02-22`. Ideally this means everything learned on that day either via the `@klug-bot --learn` command or via the offline import tool.
   - `@klug-bot --delete source:slack date:2025-02-22` -  deletes everything learned on `2025-02-22` using the `@klug-bot --learn`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SLACK_BOT_TOKEN` | OAuth token starting with `xoxb-` | Yes |
| `SLACK_SIGNING_SECRET` | Signing secret for request verification | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `KLUGBOT_LOG_CHANNEL` | Channel name for bot logs | Yes (Default: klugbot-logs) |


### Running Tests
Make sure that an enviornment is set up and the requirements are installed.
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
  - `add_to_db.py` - script to recursively import multiple files into Klug-bot's KB.
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

MIT license. See the LICENSE file for details. 