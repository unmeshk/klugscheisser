## Prompt 1: Project Setup & Basic Slack Bot Integration
You are to set up the basic structure for the Slack Knowledge Bot project. Please generate code that:
1. Initializes a new Python project with a virtual environment and required dependencies (e.g., slack_sdk, Flask or FastAPI, a vector DB client library, and any LLM API client library).
2. Organizes the project directory with folders for source code (e.g., /src), tests, configuration, and logs.
3. Implements a basic Slack bot using the Slack SDK that connects to Slack, listens for @mentions, and responds with a simple "Hello, I am Klug-Bot" message.
Ensure that your code includes clear comments and is modular so that future components (like knowledge storage, retrieval, etc.) can be integrated. End your prompt with a note on how to “wire” this basic bot into a working Slack app (e.g., setting up environment variables for Slack credentials).

## Prompt 2: Data Model & Storage Integration
Now that we have a basic Slack bot set up, please generate code that:
1. Defines a data model for a knowledge entry. The model should include fields such as:
   - Unique identifier
   - Content (text)
   - Metadata (Slack username, timestamp, source URL)
   - Semantic embeddings (for vector search)
   - Tags (enforced in kebab-case, up to 3 tags)
2. Sets up integration with a relational database (PostgreSQL/MySQL) for storing these entries.
3. Prepares a connection and basic CRUD operations for this data model.
4. Briefly outline how the vector database (e.g., FAISS, Weaviate, Qdrant, or Chroma) will be integrated for semantic search (actual integration can be developed in a later prompt).
End your code with a function stub for “wire” connecting the data model with the Slack bot.

## Prompt 3: Implementing Knowledge Storage (Learning) via Slack Commands
Building on the previous prompts, please generate code that:
1. Extends the Slack bot’s message handler to parse incoming messages that include the command to "learn" new knowledge. For example, when a user writes: "@klug-bot learn the person in charge of SRE is Vlad."
2. Extracts the key parts of the message (the knowledge content and any metadata such as the username and timestamp).
3. Saves the extracted knowledge to the relational database using the data model from Prompt 2.
4. Prepares the knowledge for later insertion into the vector database by stubbing a function that will compute and store semantic embeddings.
Ensure that the code has proper error handling and logging. End by “wiring” this new functionality into the existing Slack message handler.

## Prompt 4: Knowledge Retrieval & Query Handling
Now, extend the Slack bot by implementing knowledge retrieval. Generate code that:
1. Adds a new command handler to process queries like "@klug-bot who handles SRE?".
2. Implements logic to:
   - Parse the query and determine the intent.
   - Query the vector database for semantic similarity (simulate this with a stub function if needed).
   - Retrieve relevant knowledge entries from the relational database.
3. Integrates an LLM (or stubs the LLM call) to generate a natural language response based on the retrieved knowledge.
4. Handles edge cases where multiple entries exist (list them) or no relevant knowledge is found (respond with "I don’t know.").
Ensure that this retrieval functionality is connected to the Slack message handler so that responses are posted in a thread. End with wiring this new query handler into the existing bot framework.

## Prompt 5: File Uploads & Bulk Knowledge Import
Next, add support for bulk knowledge import via file uploads. Generate code that:
1. Implements an endpoint or Slack event handler to accept file uploads (supporting CSV, JSON, TXT, Markdown, and PDF).
2. Parses the uploaded file and extracts individual knowledge entries.
3. Validates and saves these entries into the relational database and prepares them for vector embedding insertion.
4. Includes error handling for unsupported file formats and parsing issues.
Wire this file upload functionality with the existing Slack bot so that admin users can trigger bulk imports. Ensure the code is modular and integrates with the data storage logic from previous prompts.
5. Also write a standalone script that takes in a directory and file formats and recursively uploads the contents of every relevant file into the postgres and chroma databases. Allow for metadata augmentation where a url prefix can be provided which is added to the relative paths of the files in the directories.

## Prompt 6: Conflict Handling, Editing, and Admin Workflows
Now, extend the functionality to handle conflicts and edits. Generate code that:
1. Detects when a new knowledge entry conflicts with an existing entry.
2. Implements a flow to ask the latest contributor for clarification with options: Replace, Merge, Cancel, or Manual Edit.
3. Provides commands to allow users to edit existing entries, such as "@klug-bot edit 'The SRE lead is Vlad' to 'The SRE lead is Alice'".
4. Restricts deletion functionality to admin users and logs all deletion events in a dedicated bot-log channel.
5. Also adds functionality to flag outdated knowledge (entries older than six months) and trigger a review request.
Wire these conflict resolution and admin workflow functionalities into the Slack bot so that all operations (learning, editing, deleting) are connected and logged appropriately.

## Prompt 7: Final Integration, Testing, and Deployment Wiring
For the final integration, generate code that:
1. Wires together all the components: Slack bot integration, data model CRUD operations, knowledge storage, retrieval, file uploads, and admin workflows.
2. Implements a main application entry point that initializes the Slack bot, connects to the relational and vector databases, and sets up required endpoints or event handlers.
3. Adds basic unit tests and integration tests for each component (e.g., using pytest) to ensure end-to-end functionality.
4. Provides instructions for deploying the Slack app (using environment variables for credentials, and scripts for starting the application).
Ensure that the final code is modular, well-documented, and ready for deployment in a controlled Slack workspace. Wire all components together, ensuring no orphaned code remains.
