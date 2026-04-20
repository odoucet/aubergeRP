# 06 — ComfyUI Integration

## 1. Overview

AubergeLLM uses ComfyUI as an **image generation engine**. The integration is designed with a clear abstraction layer so that:

- The frontend and chat system never interact with ComfyUI directly.
- ComfyUI workflow complexity is hidden behind a simple interface.
- Workflows can be swapped, updated, or added without changing application code.

## 2. Architecture

```
┌─────────────────────────────────────────────────┐
│            AubergeLLM Backend                   │
│                                                 │
│  ┌──────────────┐     ┌───────────────────┐     │
│  │ ComfyUI      │     │ ComfyUI Client    │     │
│  │ Service      │────▶│ (HTTP + WS)       │     │
│  │ (Abstraction)│     │                   │     │
│  └──────┬───────┘     └───────┬───────────┘     │
│         │                     │                 │
└─────────┼─────────────────────┼─────────────────┘
          │                     │
    Workflow                    │
    Templates                   ▼
    (JSON files)         ┌──────────────┐
                         │   ComfyUI    │
                         │   Instance   │
                         └──────────────┘
```

### Components

| Component | File | Responsibility |
|---|---|---|
| **ComfyUI Service** | `services/comfyui_service.py` | Workflow abstraction, template loading, input injection, result extraction |
| **ComfyUI Client** | `services/comfyui_client.py` | Low-level HTTP and WebSocket communication with ComfyUI |
| **Workflow Templates** | `data/workflows/*.json` | ComfyUI workflow files with injectable placeholders |
| **Workflow Definitions** | `data/workflows/*.yaml` | Metadata files describing inputs/outputs for each workflow |

## 3. Workflow Abstraction

### 3.1 Concept

Each workflow available in AubergeLLM is defined by two files:

1. **Workflow template** (`{workflow_id}.json`) — The raw ComfyUI workflow (API format), exported from ComfyUI, with placeholder values in injectable fields.
2. **Workflow definition** (`{workflow_id}.yaml`) — A metadata file describing the workflow's inputs, outputs, and where to inject values in the JSON.

### 3.2 Workflow Definition Format

```yaml
id: default_t2i
name: "Default Text-to-Image"
description: "Generates an image from a text prompt using Stable Diffusion"
template: "default_t2i.json"

inputs:
  - name: prompt
    type: string
    required: true
    description: "The positive prompt for image generation"
    inject:
      node_id: "6"
      field: "inputs.text"
  - name: negative_prompt
    type: string
    required: false
    default: "blurry, low quality, deformed, ugly"
    description: "The negative prompt"
    inject:
      node_id: "7"
      field: "inputs.text"
  - name: seed
    type: integer
    required: false
    default: -1
    description: "Random seed (-1 for random)"
    inject:
      node_id: "3"
      field: "inputs.seed"

outputs:
  - name: image
    type: image
    description: "The generated image"
    extract:
      node_id: "9"
```

### 3.3 Injection Process

When executing a workflow:

1. Load the template JSON file.
2. For each input in the definition:
   a. Get the value from the request (or use the default).
   b. Navigate to `workflow[node_id][field]` in the JSON.
   c. Set the value.
3. If `seed` is `-1`, generate a random seed.
4. Submit the modified JSON to ComfyUI.

### 3.4 Output Extraction

When ComfyUI completes execution:

1. Query `/history/{prompt_id}` to get execution results.
2. For each output in the definition:
   a. Find the output node by `node_id`.
   b. Extract the filename from the node's outputs.
3. Download the image via `/view?filename=...`.
4. Save it locally to `data/images/{uuid}.png`.
5. Return the local image URL.

## 4. ComfyUI Client

### 4.1 API Endpoints Used

| Endpoint | Method | Purpose |
|---|---|---|
| `/prompt` | POST | Submit a workflow for execution |
| `/history/{prompt_id}` | GET | Get execution results |
| `/view?filename={name}&subfolder={sub}&type={type}` | GET | Download a generated image |
| `/ws?clientId={client_id}` | WebSocket | Monitor execution progress |

### 4.2 Submitting a Workflow

```http
POST http://{comfyui_url}/prompt
Content-Type: application/json

{
  "prompt": { ... },
  "client_id": "aubergellm-{uuid}"
}
```

**Response:**
```json
{
  "prompt_id": "abc123-...",
  "number": 42
}
```

### 4.3 Monitoring Execution via WebSocket

Connect to `ws://{comfyui_url}/ws?clientId=aubergellm-{uuid}`.

Messages received:

```json
{"type": "status", "data": {"status": {"exec_info": {"queue_remaining": 1}}}}
{"type": "execution_start", "data": {"prompt_id": "abc123-..."}}
{"type": "executing", "data": {"node": "3", "prompt_id": "abc123-..."}}
{"type": "progress", "data": {"value": 5, "max": 20, "prompt_id": "abc123-..."}}
{"type": "executing", "data": {"node": null, "prompt_id": "abc123-..."}}
```

- `executing` with `node: null` means execution is complete.
- `progress` events can be forwarded to the frontend for progress display.

### 4.4 Retrieving Results

After execution completes:

```http
GET http://{comfyui_url}/history/{prompt_id}
```

**Response (excerpt):**
```json
{
  "abc123-...": {
    "outputs": {
      "9": {
        "images": [
          {
            "filename": "ComfyUI_00042_.png",
            "subfolder": "",
            "type": "output"
          }
        ]
      }
    }
  }
}
```

Then download:
```http
GET http://{comfyui_url}/view?filename=ComfyUI_00042_.png&subfolder=&type=output
```

## 5. ComfyUI Service API

| Function | Description |
|---|---|
| `list_workflows()` | List all available workflow definitions |
| `get_workflow(workflow_id)` | Get a specific workflow definition |
| `execute_workflow(workflow_id, inputs)` | Execute a workflow with given inputs, return generation ID |
| `get_generation_status(generation_id)` | Get execution status and progress |
| `get_generation_result(generation_id)` | Get the result (image URL) of a completed generation |

### Internal State

The service maintains an in-memory dict of active generations:

```python
active_generations: dict[str, GenerationState] = {}

class GenerationState:
    generation_id: str
    prompt_id: str  # ComfyUI's prompt ID
    workflow_id: str
    status: str  # "queued", "running", "completed", "failed"
    progress: int  # 0-100
    image_url: str | None
    error: str | None
    created_at: datetime
```

## 6. ComfyUI Client API

| Function | Description |
|---|---|
| `submit_prompt(workflow_json, client_id)` | POST to /prompt, return prompt_id |
| `get_history(prompt_id)` | GET /history/{prompt_id} |
| `download_image(filename, subfolder, type)` | GET /view, return image bytes |
| `monitor_execution(prompt_id, client_id, on_progress)` | WebSocket monitoring with callback |
| `test_connection()` | Check if ComfyUI is reachable |

## 7. Default Workflow

The MVP ships with one workflow: `default_t2i` (default text-to-image).

This workflow should be a simple, widely compatible Stable Diffusion workflow:

- **Input:** positive prompt, negative prompt, seed.
- **Output:** one image.
- **Nodes:** KSampler, CLIP Text Encode (x2), Load Checkpoint, VAE Decode, Save Image.
- **Compatible with:** SD 1.5, SDXL (user configures the checkpoint in ComfyUI).

The workflow JSON is exported from ComfyUI's "Save (API Format)" feature and stored in `data/workflows/default_t2i.json`.

## 8. Configuration

```yaml
comfyui:
  base_url: "http://localhost:8188"
  timeout: 120         # Request timeout in seconds
  ws_timeout: 300      # WebSocket monitoring timeout
  max_retries: 3       # Retry count for failed connections
  client_id_prefix: "aubergellm"
```

## 9. Error Handling

| Scenario | Behavior |
|---|---|
| ComfyUI unreachable | Return 502 error; chat continues without image generation |
| Workflow template not found | Return 404 error |
| Missing required input | Return 400 error with field name |
| Execution fails in ComfyUI | Mark generation as `failed`, return error detail |
| WebSocket connection lost | Fall back to polling `/history/{prompt_id}` |
| Timeout during execution | Mark generation as `failed` with timeout error |
| Invalid workflow JSON | Return 500 error; log the parsing error |

## 10. Image Storage

- Generated images are saved to `data/images/{generation_uuid}.png`.
- Images are served via `GET /api/images/{image_id}`.
- No automatic cleanup in MVP. Users manage disk space manually.
- Image file names use the generation UUID, not the ComfyUI filename, to avoid conflicts.
