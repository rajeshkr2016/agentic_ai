Issues/ Friction logs:
  - For testing in playground for tool use, there was no way to store raw log - with suggestions and in google/ claude to store in fixtures for reference input log contents for hallucination checks
  - The eval dataset and the fixture dataset are two separate things, being setup that way to avoid scoring of raw logs
  - Built-in evaluators like conciseness and correctness silently fail if input and reference keys are missing from the run outputs. No error, just "All Failed" in the UI.
  - Hallucinations is present/ true showing in green, not sure if we infer good for project evaluation and red for not present.
  - Auto evaluators - Its in tutorial, but current UI is different.