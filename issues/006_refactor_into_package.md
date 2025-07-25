# Issue: Refactor repository into package structure

## Problem

The project currently consists of a single monolithic script in the repository root. This makes it difficult to extend, test, and distribute the code.

## Proposed Solution

Organize the code into a Python package under `src/gmail_automation/` with separate modules for configuration, Gmail API interactions, and the command-line entry point. Update imports accordingly and adjust the README with the new usage instructions.
