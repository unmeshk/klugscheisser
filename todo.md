# Slack Knowledge Bot - TODO Checklist

This checklist outlines all the steps necessary to build the Slack Knowledge Bot from initial setup through to full integration and deployment. Use this as a guide to track your progress.

---

## 1. Project Setup & Environment
- [ ] **Initialize Repository & Environment**
  - [X] Create a new Git repository.
  - [X] Set up a Python virtual environment.
  - [ ] Create a `requirements.txt` or `setup.py` file including dependencies:
    - slack_sdk
    - Flask or FastAPI
    - LLM API client library
    - Vector DB client library (e.g., FAISS, Weaviate, Qdrant, or Chroma)
    - Database driver (PostgreSQL/MySQL)
    - File parsing libraries (for CSV, JSON, TXT, Markdown, PDF)
- [X] **Organize Directory Structure**
  - [X] Create folders for:
    - `/src` (source code)
    - `/tests` (unit and integration tests)
    - `/config` (configuration files)
    - `/logs` (log files)

---

## 2. Slack Bot Integration
- [X] **Slack App Setup**
  - [X] Create a new Slack App in the Slack Developer Dashboard.
  - [X] Configure necessary OAuth scopes, event subscriptions, and bot tokens.
- [X] **Basic Bot Functionality**
  - [X] Implement code to connect to Slack using the Slack SDK.
  - [X] Set up a basic event listener for @mentions.
  - [X] Respond with a message like "Hello, I am Klug-Bot" to confirm connectivity.
  - [X] Document environment variable setup (e.g., Slack credentials).

---

## 3. Data Model & Storage
- [X] **Define Data Model**
  - [X] Create a model for a knowledge entry including:
    - Unique identifier
    - Content (text)
    - Metadata (Slack username, timestamp, source URL)
    - Semantic embeddings (for vector search)
    - Tags (up to 3, enforced in kebab-case)
- [X] **Database Setup**
  - [X] Set up a relational database (PostgreSQL/MySQL).
  - [X] Create tables for storing knowledge entries.
  - [X] Implement CRUD operations for the data model.
- [ ] **Vector Database Integration (Stub)**
  - [X] Outline and stub functions for integrating with a vector database for semantic search.

---

## 4. Knowledge Storage Functionality
- [X] **Direct Learning via Slack Commands**
  - [X] Extend the Slack bot’s message handler to capture "learn" commands.
  - [X] Parse incoming messages (e.g., "@klug-bot learn the person in charge of SRE is Vlad").
  - [x] Extract and validate the knowledge content along with metadata (user, timestamp).
  - [X] Save the extracted knowledge to the relational database.
  - [X] Stub a function for computing and storing semantic embeddings in the vector DB.

---

## 4.5. Create Embeddings
- [X] **Use a vector store to save info as embeddings**
  - [X] Use all-minilm-v2 as embedding and auto convert all info into embeddings
  - [X] Store in chroma

## 5. Knowledge Retrieval & Query Handling
- [X] **Query Processing**
  - [X] Add a command handler for queries (e.g., "@klug-bot who handles SRE?").
  - [X] Parse queries to determine user intent.
  - [X] Query the vector database (using a stub if needed) to retrieve relevant entries.
  - [X] Retrieve corresponding entries from the relational database.
- [X] **Response Generation**
  - [X] Integrate (or stub) an LLM call to generate a natural language response.
  - [X] Handle multiple results (list them) and cases where no entry is found (respond with "I don’t know.").
  - [X] Ensure responses are posted in Slack threads.

---

## 6. File Uploads & Bulk Knowledge Import
- [X] **File Upload Endpoint/Handler**
  - [X] Implement an endpoint or Slack event handler for file uploads.
  - [X] Support various file formats: CSV, JSON, TXT, Markdown, PDF.
  - [ ] Support rst, mdx files
- [X] **File Parsing & Import**
  - [X] Parse uploaded files to extract individual knowledge entries.
  - [X] Validate and store each entry in the relational database.
  - [X] Prepare entries for later vector embedding insertion.
  - [X] Handle errors for unsupported formats or parsing failures.
- [X] **Scripts for bulk uploads**
  - [X] Script to allow offline uploading of data by recursively going through a directory.
- [X] **Admin Trigger**
  - [X] Ensure that bulk imports are restricted to admin users.
- [X] **Bulk delete**
  - [X] Allow users to delete everything from a specific source using `@klug-bot delete`
  - [X] Add source and date specification to metadata during import. e.g., 'source':'offline' 'date':'2025-02-24' or 'source':'slack' 'date':'2025-02-23'. This gives ability to delete based on source as well as date. 


---

## 6.5 Improved context for conversations
- [X] **Add message thread as context**
  - [X] Copy over everything in previous messages in thread as context if app in mentioned in a thread/

---

## 7. Conflict Handling, Editing, & Admin Workflows
- [ ] **Conflict Detection & Resolution**
  - [ ] Implement logic to detect conflicting knowledge entries.
  - [ ] Create a flow to ask the latest contributor for clarification with options:
    - Replace
    - Merge
    - Cancel
    - Manual Edit
- [ ] **Editing & Deletion**
  - [ ] Add command handling for editing entries (e.g., "@klug-bot edit 'The SRE lead is Vlad' to 'The SRE lead is Alice'").
  - [ ] Restrict deletion functionality to admin users.
  - [ ] Log all edits and deletions in a dedicated bot-log channel.
- [ ] **Outdated Knowledge Handling**
  - [ ] Flag entries older than six months as possibly outdated.
  - [ ] Implement a review request process that notifies admins.

---

## 8. Slack Communication & Formatting
- [ ] **Rich Message Formatting**
  - [ ] Format responses using Slack’s rich formatting (bold, bullet lists, inline links, code blocks).
  - [ ] Ensure responses are always posted in a thread.
- [ ] **Rate Limits & Permissions**
  - [ ] Enforce that all users can query, but only admins can perform sensitive actions (file uploads, deletion, conflict resolutions).

---

## 9. Testing & Deployment
- [ ] **Unit Testing**
  - [ ] Write tests for:
    - Data model CRUD operations.
    - Knowledge storage and retrieval functions.
    - Slack event handlers.
- [ ] **Integration Testing**
  - [ ] Create tests for:
    - End-to-end Slack interactions.
    - Vector database search functionality.
    - Admin workflows (edits, deletions, conflict handling).
- [ ] **Continuous Integration**
  - [ ] (Optional) Set up CI/CD pipeline for automated testing.
- [ ] **Deployment**
  - [ ] Deploy the bot in a controlled Slack workspace.
  - [ ] Set up environment variables for credentials.
  - [ ] Prepare deployment scripts.
- [ ] **Monitoring & Maintenance**
  - [ ] Monitor flagged responses and bot-log entries.
  - [ ] Collect user feedback and adjust accordingly.

---

## 10. Final Integration & Documentation
- [ ] **Wiring All Components Together**
  - [ ] Integrate Slack bot, data model, file upload, and admin workflows into a unified application.
  - [ ] Create a main entry point to initialize the bot, connect to databases, and set up endpoints/event handlers.
- [ ] **Documentation**
  - [ ] Write comprehensive documentation (README.md) covering:
    - Setup instructions
    - Usage guidelines
    - Troubleshooting tips
- 
