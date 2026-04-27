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
- [ ] Add basic auth to admin with a single password.
Print it in the logs on startup (generated randomly if not set in env) and protect all admin API routes and the admin GUI.

- [ ] Ability to change text display speed (+ preview of what it looks like).

Front
-----


Bug fixes
---------
- [ ] remove any french in comments / source code and replace with english. DO NOT TOUCH aubergeRP/examples/


Future
------
- [ ] Manage multiple connectors of the same type, and be able to connect the connectors by character, or let the LLM choose based on keywords? Carefully prepare the spec for this...

- [ ] For image generation, it would be necessary to first generate a prompt with the LLM based on the scene description, then send this prompt to the image connector. This would allow for better coherence between images and text, and also enable "prompt engineering" to improve the quality of generated images.
Look at what exists today but remains very light.
For example, in my last image, the keywords are "Steampunk Marianne, intense gaze, soot-covered face, mechanical arm, workshop background" which does not describe at all
