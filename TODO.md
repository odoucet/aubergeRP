Doc
---
- [ ] Document in README + /docs/ the Docker implementation with GPU cards pre-configured with optimal model to run (see /docker/)


Examples to write
--------
- How to use a local LLM with the OpenAI-compatible connector interface
- How to use the ComfyUI connector for image generation
- How to import characters from SillyTavern into aubergeRP

Admin
----


Front
-----


Bug fixes
---------


Future
------
- [ ] Manage multiple connectors of the same type, handle a "default" connector (there can be only one for the same type at a given moment) ; be able to connect the connectors by character, or let the LLM choose based on keywords? Carefully prepare the spec for this...


- [ ] Isolate all prompts used in the sourcecode into separate files in aubergeRP/prompts/ to allow users to easily customize them. This includes the prompt for generating image descriptions from scene text, the prompt for summarizing conversations, and any other prompt currently hardcoded in the source. Add a page on admin UI to edit these prompts.

- [ ] Ability to change text display speed (+ preview of what it looks like).
