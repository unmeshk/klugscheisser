# Klugscheisser
- *(Ger.) Smartass (Lit. Knowledge Shi**er)* 
A slack bot that learns and spits out knowledge

## Slack bot scopes needed

### Oauth & Permissions
Scope Description
app_mentions:read
View messages that directly mention @test-agent-support-bot in conversations that the app is in

channels:history
View messages and other content in public channels that test-agent-support-bot has been added to

chat:write
Send messages as @test-agent-support-bot

groups:history
View messages and other content in private channels that test-agent-support-bot has been added to

files:read
View files shared in channels and conversations that klug-bot has been added to

### Event Subscriptions

Event Name	Description	Required Scope
app_mention
Subscribe to only the message events that mention your app or bot

app_mentions:read

message.channels
A message was posted to a channel

channels:history

message.groups
A message was posted to a private channel

groups:history

## Create Postgres DB 
Create a postgres db called klugbot_kb and add a user called klugbot. 
Add that info to your env file
DATABASE_URL=postgresql://klugbot:<password>>@localhost:<port>/klugbot_kb

Garnt schema privileges to the klugbot user. 
psql postgres -- connect to the postgres server
\c KLUGBOT_KB  -- Connect to your database
GRANT USAGE ON SCHEMA public TO klugbot;
GRANT CREATE ON SCHEMA public TO klugbot;
GRANT ALL ON ALL TABLES IN SCHEMA public TO klugbot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO klugbot;
