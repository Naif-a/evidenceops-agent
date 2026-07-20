# Agent Engineering Controls

## Least Privilege

Agents should only receive tools required for the current task. Tools capable of writing files, sending messages, or changing external systems should remain unavailable until authorization is confirmed.

## Bounded Execution

Agent execution must have a maximum number of tool calls. Repeated calls with identical inputs should be detected and stopped.

## Tool Design

Each tool should have one clear responsibility, typed inputs, validated parameters, a precise description, and a structured result.

## Prompt Injection

Retrieved documents must be treated as untrusted data, not system instructions. Instructions found inside retrieved content must not override application policy.
