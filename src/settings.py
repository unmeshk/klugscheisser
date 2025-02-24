# Query handler settings
SIMILARITY_THRESHOLD = 0.8
MAX_RESULTS = 5
MAX_OUTPUT_TOKENS = 2048
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
2. If the information isn't in the knowledge entries, respond with "I don't know"
3. Don't make up or infer information that isn't explicitly stated
4. If multiple relevant pieces of information exist, combine them the best you can to provide a coherent answer to the question. 

Answer:"""