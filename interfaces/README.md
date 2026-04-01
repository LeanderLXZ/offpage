# Interfaces

This directory is for terminal adapters and service entry points.

Planned layout:

```text
interfaces/
  agent/
  app/
  mcp/
```

All terminals should use the same underlying character service and data model.

Terminal adapters should not bypass the core package model by writing directly
into character canon files.
