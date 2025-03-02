# Query handler settings
SIMILARITY_THRESHOLD = 0.8
MAX_RESULTS = 5
MAX_OUTPUT_TOKENS = 2048
MAX_FILE_SIZE = 5_000_000 # ~5 MB
LLM_MODEL = 'gemini-2.0-flash'

# Slack users who are able to teach the bot 
# (either via learn or bulk import)
KLUGBOT_TEACHERS = [
    "U020XTW7KHB"  # Replace with actual Slack user IDs
]


# Prompt templates
QUERY_PROMPT_TEMPLATE = """Based on the following knowledge entries, answer the question: "{query}"

Available knowledge:
{contexts}

Important instructions:
1. Only use information from the provided knowledge entries
2. If the information isn't in the knowledge entries, respond with "I don't have any knowledge about that."
3. Don't make up or infer information that isn't explicitly stated
4. If multiple relevant pieces of information exist, combine them the best you can to provide a coherent answer to the question. 

Answer:"""

# Template with thread context
QUERY_WITH_CONTEXT_TEMPLATE = """Based on the following knowledge entries and conversation history, answer the question: "{query}"

Available knowledge:
{contexts}

Conversation history: 
{thread_context}

Important instructions:
1. Consider both the conversation history and knowledge entries when formulating your response
2. If relevant information is in the conversation history, you can use it
3. If the information isn't in either the knowledge entries or conversation history, respond with "I don't have any knowledge about that."
4. Don't make up or infer information that isn't explicitly stated
5. If multiple relevant pieces of information exist, combine them the best you can to provide a coherent answer to the question.
6. If images are included, analyze them to provide additional insights.

Answer:"""

# Template with images but no thread context
QUERY_WITH_IMAGES_TEMPLATE = """Based on the following knowledge entries and images, answer the question: "{query}"

Available knowledge:
{contexts}

Important instructions:
1. Consider both the images and knowledge entries when formulating your response
2. Analyze the attached images to provide insights relevant to the question
3. If the information isn't available in the knowledge entries or images, respond with "I don't have any knowledge about that."
4. Don't make up or infer information that isn't explicitly stated
5. If multiple relevant pieces of information exist, combine them the best you can to provide a coherent answer to the question.

Answer:"""