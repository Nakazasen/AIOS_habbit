# RAG Quality Roadmap After E1

## Purpose

Improve the completeness and usefulness of answers without confusing a longer
answer with a better-supported answer. This is separate from E1--E4: E1 first
determines whether chunking is a real bottleneck. No item below changes the
production path until it has its own measured baseline and audit.

## What BGE-M3 does, and does not do

BGE-M3 turns a user question and document chunks into search signals. It helps
find semantically related evidence, but it does not independently reason that a
multi-part question must be decomposed into several research questions. The LLM
receives the original question and the evidence selected by retrieval, not
BGE-M3's vectors or token weights. If retrieval misses a topic, the answer can
be narrow even when the LLM is capable.

## Decision sequence

### R0 -- Complete E1 first

Use real, local, approved question-evidence cases to determine whether chunks
are the cause of missing evidence. If E1 identifies a chunking defect, follow
E2--E4 before adding any wider retrieval behaviour.

### R1 -- Query coverage baseline

If E1 shows chunks are adequate but answers still miss parts of multi-part
questions, create a separate local evaluation set. Each case records the
subtopics a complete answer must cover and the source identities expected for
each subtopic. Measure subtopic recall and grounded citation support; do not
use answer length as a success metric.

### R2 -- Query planning and multi-query retrieval pilot

For questions with several independent asks, test a bounded planner that:

1. identifies the individual asks;
2. creates one controlled search query per ask;
3. retrieves evidence separately; and
4. deduplicates and reranks the combined evidence pack.

It must show the owner which subqueries ran and which source supports each.
It must fail closed when a required subtopic has no evidence, rather than
silently filling the gap with general knowledge.

### R3 -- Evidence assembly and reranking

Compare bounded top-k, parent/neighbor expansion, and local reranking using the
same R1 cases. Preserve a detailed passage for every precise claim; summaries
may help navigation but cannot become sole factual proof. Enforce a CPU latency
budget and a maximum evidence-pack size.

### R4 -- Answer quality and expert feedback

Show the answer together with its supporting passages. Let experts mark a
subtopic as supported, unsupported, incomplete, or incorrect. Store that review
as local evaluation cases first; do not silently train the model or mutate the
vector database from a click. Approved feedback can later expand the test set
and trigger a reviewed knowledge-ingestion workflow.

## Success criteria

- More expected source evidence is retrieved per subtopic than the R1 baseline.
- Every material answer claim has a detailed supporting passage or is explicitly
  marked unavailable.
- Improvements stay inside agreed CPU latency and index-size budgets.
- No raw internal text leaves the local evaluation workspace.

## Relationship to NotebookLM

NotebookLM may appear broader because it can use more cloud computation and
possibly several retrieval passes. AIOS should not attempt to imitate an
undocumented provider internals. Instead it should measure where it misses
evidence, then add the smallest observable and auditable improvement.
