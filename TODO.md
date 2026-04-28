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

- [ ] The "test" function of a connector in admin does not check if the model is listed.
Example with URL: http://ollama:11434/v1  ·  Model: qwen3.6-27b:q4km
Last test: Connected. 2 model(s) available (flux-klein:9b-q4km, glm47-flash:q4_0).
=> model not listed, which gives a 404 if we try to use it later in the front.

- [ ] hability to add parameters on model. Example with qwen that can expect an extra_body:
"chat_template_kwargs": {"enable_thinking": False},

- [ ] make sure connectors can accept temperature/top_p/presence_penalty/frequency_penalty parameters in the body of the request, and pass them to the model if supported. Add this to the "test" function in admin as well.

Front
-----

- [x] if a chat failed, and we click on "retry", the original message is added again to the chat history, invisible first, but if we refresh the page, we can see that the message is duplicated.


Bug fixes
---------
- [x] remove any french in comments / source code and replace with english. DO NOT TOUCH aubergeRP/examples/
  (No French developer comments found; French strings in `_NSFW_PATTERNS` are intentional multilingual detection patterns, added English comment to clarify.)

- [x] OpenAITextConfig `supports_tool_calling` defaulted to `False` but OpenAI natively supports tool-calling; changed default to `True`. (Was causing a failing test.)

- [x] if a chat failed, and we click on "retry", the original message is added again to the chat history, invisible first, but if we refresh the page, we can see that the message is duplicated.
  (Fixed in `stream_chat()`: before appending the user message, check if the last message in the conversation is already this user message. If so, skip re-appending — this is a retry of a failed request.)


Future
------
- [ ] Manage multiple connectors of the same type, and be able to connect the connectors by character, or let the LLM choose based on keywords? Carefully prepare the spec for this...

- [ ] For image generation, it would be necessary to first generate a prompt with the LLM based on the scene description, then send this prompt to the image connector. This would allow for better coherence between images and text, and also enable "prompt engineering" to improve the quality of generated images.
Look at what exists today but remains very light.
For example, in my last image, the keywords are "Steampunk Marianne, intense gaze, soot-covered face, mechanical arm, workshop background" which does not describe at all
