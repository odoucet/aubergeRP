<!-- Instructions: When filling this template, DELETE any checkbox line that does not apply to this PR. Do not leave irrelevant checkboxes unchecked. -->

## Summary

<!-- One or two sentences describing what this PR does and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature / enhancement
- [ ] Connector (new backend)
- [ ] Refactor / cleanup
- [ ] Documentation
- [ ] CI / tooling

## Related issues

<!-- Closes #NNN -->

## Changes

<!-- Bullet list of the main changes made. -->

-

## Testing

<!-- Describe how you tested your changes. -->

- [ ] `make test` passes locally
- [ ] `make lint` passes locally
- [ ] I tested the UI manually (if the change affects the frontend)

## Migration notes

<!-- If this PR adds or modifies a DB schema, describe the migration. Leave blank if N/A. -->

## Checklist
- [ ] This code respects the philosophy of "keep it as simple and maintainable as possible for the long term".
- [ ] This code respects the philosophy of "Hide complexity, expose simplicity".
- [ ] My code follows the architecture rules in `AGENTS.md` (routers stay thin, services own logic, connectors are isolated).
- [ ] I added or updated tests for new/changed behaviour.
- [ ] I added or updated docstrings / comments where appropriate.
- [ ] If I added a new connector backend, I followed the steps in `AGENTS.md § Adding a new connector backend`.
- [ ] If I changed the DB schema, I added a migration in `aubergeRP/migrations/`.
