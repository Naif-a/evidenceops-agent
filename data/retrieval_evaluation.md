# Retrieval Evaluation

## Retrieval Hit Rate

Retrieval Hit Rate at K measures how often the expected source appears among the top K retrieved results.

## Context Relevance

Context relevance measures how much retrieved text directly helps answer the question. Irrelevant context can reduce answer quality even when the correct source is present.

## Chunking

Smaller chunks may improve precision but lose surrounding context. Larger chunks provide more context but can introduce irrelevant information. Chunk size and overlap must be evaluated using representative questions.

## Source Inspection

Generated answers should not be evaluated alone. Reviewers must inspect retrieved source nodes, similarity scores, metadata, and source filenames.
