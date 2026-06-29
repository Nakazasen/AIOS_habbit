# AIOS RAG Failure Analysis

## Why AIOS still loses to NotebookLM
NotebookLM synthesizes unstructured, messy text far more fluidly, while AIOS currently relies on hardcoded templates that are misapplied across different types of query intents. AIOS treats all queries as table extraction or document retrieval without adapting to the specific format of the source.

## Examples of Current Failures
* **Q04/Q05 (Process boundaries)**: These are process boundary questions, but AIOS retrieves generic snippets from Excel and dumps them into a table-mapping template.
* **Q06/Q07 (Screenshot targets)**: AIOS retrieves HTML/ERD chunks because the word "error" matches the HTML tags, leading to hallucinated "visible" facts instead of using actual OCR/PNG data.
* **Q01/Q02/Q03**: Answers do not extract concrete fields or relationships, offering only vague summaries.
* **Q10/Q12**: The troubleshooting action plan is a generic "check logs" rather than evidence-specific steps.

## Status Flags
* **Current replacement claim**: NO.
* **Global parity**: NO.
* **P1.0 opened**: NO.
