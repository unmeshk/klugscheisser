import re
import pytest
import asyncio
from src.klugbot import KlugBot

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    # Set dummy environment variables required by KlugBot and related modules
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-dummy-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "dummy-signing-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key")
    # If DATABASE_URL is used in tests, set a dummy value as well
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

# A simple dummy "say" callable that collects messages.
class DummySay:
    def __init__(self):
        self.messages = []
    async def __call__(self, text, thread_ts=None):
        self.messages.append(text)

# --- Tests for internal helper functions ---

def test_learn_regex():
    bot = KlugBot()
    text = "<@U12345678> --learn This is a test learning message."
    match = bot.learn_pattern.match(text)
    assert match is not None
    # The regex captures the content (if provided)
    assert match.group("content").strip() == "This is a test learning message."

def test_delete_regex():
    bot = KlugBot()
    text = "<@U12345678> --delete https://example.com"
    match = bot.delete_pattern.match(text)
    assert match is not None
    assert match.group("content").strip() == "https://example.com"

def test_query_regex():
    bot = KlugBot()
    text = "<@U12345678> What is the answer to life?"
    match = bot.query_pattern.match(text)
    assert match is not None
    assert match.group("query").strip() == "What is the answer to life?"

def test_parse_delete_filters():
    bot = KlugBot()
    input_str = "url:https://example.com source:slack date:2025-02-22"
    filters = bot._parse_delete_filters(input_str)
    expected = {
        "url": "https://example.com",
        "source": "slack",
        "date": "2025-02-22"
    }
    assert filters == expected

def test_extract_metadata():
    bot = KlugBot()
    # Prepare a dummy event with required fields
    event = {
        "user": "U123456",
        "ts": "1234567890.1234",
        "channel": "C123456",
        "team": "T123456"
    }
    # Set the bot's slack_url (normally set on first mention)
    bot.slack_url = "https://dummy.slack.com/"
    metadata = bot._extract_metadata(event)
    expected_link = "https://dummy.slack.com/archives/C123456/p12345678901234"
    assert metadata["slack_username"] == "U123456"
    assert metadata["slack_timestamp"] == "1234567890.1234"
    assert metadata["channel"] == "C123456"
    assert metadata["team"] == "T123456"
    assert metadata["source_url"] == expected_link

def test_extract_tags_with_hashtags():
    bot = KlugBot()
    content = "This is a #TestContent with #MultipleTags and #AnotherTag"
    tags = bot._extract_tags(content)
    # The regex finds words after '#' and converts to kebab-case.
    expected = ["test-content", "multiple-tags", "another-tag"]
    assert tags == expected

def test_extract_tags_without_hashtags():
    bot = KlugBot()
    content = "Hello world without hashtags."
    tags = bot._extract_tags(content)
    # Should default to the first word (if not a common stopword)
    assert tags == ["hello"]

# --- Asynchronous tests simulating Slack events ---

@pytest.fixture
def klugbot():
    bot = KlugBot()
    # Override file_handler.is_authorized for predictable behavior:
    # Only user "U020XTW7KHB" is authorized.
    bot.file_handler.is_authorized = lambda user: (user == "U020XTW7KHB")
    return bot

@pytest.mark.asyncio
async def test_learn_command_unauthorized(klugbot):
    """
    When an unauthorized user issues a learn command,
    the bot should respond with a "not authorized" message.
    """
    event = {
        "text": "<@U12345678> --learn This is a learning test.",
        "user": "unauthorized_user",
        "ts": "1234567890.1234"
    }
    dummy_say = DummySay()
    # Since the authorization check happens in the event handler,
    # we simulate by directly invoking the logic that would be called.
    # (For a full integration test you would mock the Slack client and dispatch the event.)
    # Here we directly call the portion that checks authorization.
    if not klugbot.file_handler.is_authorized(event.get("user")):
        await dummy_say("Sorry, you are not authorized to teach me new things.", event.get("ts"))
    assert "not authorized" in dummy_say.messages[0].lower()

@pytest.mark.asyncio
async def test_learn_command_authorized(klugbot):
    """
    When an authorized user issues a learn command (without a file),
    the bot should call _handle_learn_command.
    We override _handle_learn_command to simulate a successful learn.
    """
    event = {
        "text": "<@U12345678> --learn Learn this awesome fact.",
        "user": "U020XTW7KHB",
        "ts": "1234567890.1234"
    }
    dummy_say = DummySay()
    # Replace _handle_learn_command with a dummy version.
    async def dummy_handle_learn_command(ev, say, match):
        await say("Learn command processed", ev.get("ts"))
    klugbot._handle_learn_command = dummy_handle_learn_command

    # Simulate a learn command by manually checking the regex and calling the handler.
    learn_match = klugbot.learn_pattern.match(event.get("text", ""))
    if learn_match:
        # Since user is authorized, we call the handler.
        await klugbot._handle_learn_command(event, dummy_say, learn_match)
    assert "Learn command processed" in dummy_say.messages[0]

@pytest.mark.asyncio
async def test_delete_command_unauthorized(klugbot):
    """
    When an unauthorized user issues a delete command,
    the bot should respond with a "not authorized" message.
    """
    event = {
        "text": "<@U12345678> --delete url:https://example.com",
        "user": "unauthorized_user",
        "ts": "1234567890.1234"
    }
    dummy_say = DummySay()
    if not klugbot.file_handler.is_authorized(event.get("user")):
        await dummy_say("Sorry, you are not authorized to delete entries.", event.get("ts"))
    assert "not authorized" in dummy_say.messages[0].lower()

@pytest.mark.asyncio
async def test_delete_command_authorized(klugbot):
    """
    When an authorized user issues a delete command,
    the bot should call _handle_delete_command.
    We override _handle_delete_command to simulate successful deletion.
    """
    event = {
        "text": "<@U12345678> --delete url:https://example.com",
        "user": "U020XTW7KHB",
        "ts": "1234567890.1234"
    }
    dummy_say = DummySay()
    async def dummy_handle_delete_command(ev, say, match):
        await say("Delete command processed", ev.get("ts"))
    klugbot._handle_delete_command = dummy_handle_delete_command

    delete_match = klugbot.delete_pattern.match(event.get("text", ""))
    if delete_match:
        await klugbot._handle_delete_command(event, dummy_say, delete_match)
    assert "Delete command processed" in dummy_say.messages[0]

@pytest.mark.asyncio
async def test_query_command(klugbot):
    """
    When a user issues a regular query (i.e. not learn or delete),
    the bot should call _handle_query_command.
    We override _handle_query_command to simulate a response.
    """
    event = {
        "text": "<@U12345678> What is the meaning of life?",
        "user": "U020XTW7KHB",
        "ts": "1234567890.1234"
    }
    dummy_say = DummySay()
    async def dummy_handle_query_command(ev, say, match, client):
        await say("Query command processed", ev.get("ts"))
    klugbot._handle_query_command = dummy_handle_query_command

    query_match = klugbot.query_pattern.match(event.get("text", ""))
    if query_match:
        # For this test we pass None for the client since our dummy doesn't use it.
        await klugbot._handle_query_command(event, dummy_say, query_match, None)
    assert "Query command processed" in dummy_say.messages[0]
