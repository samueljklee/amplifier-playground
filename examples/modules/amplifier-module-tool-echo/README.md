# Echo Tool Module

A simple example tool module for demonstrating local module development with Amplifier Playground.

## Tools Provided

### `echo`
Echo back messages with optional transformations.

**Parameters:**
- `message` (required): The message to echo back
- `transform` (optional): One of `none`, `upper`, `lower`, `reverse`

### `current_time`
Get the current date and time.

**Parameters:**
- `format` (optional): One of `iso`, `human`, `unix`

## Configuration

```json
{
  "module": "tool-echo",
  "config": {
    "prefix": "[Echo] ",
    "timezone": "UTC"
  }
}
```

## Usage

This module can be loaded from a local workspace directory:

```bash
amplay session test ./mount-plan.json -p "Echo hello world" -m ./examples/modules
```

Or referenced in a mount plan:

```json
{
  "tools": [
    {
      "module": "tool-echo",
      "source": "./examples/modules/amplifier-module-tool-echo"
    }
  ]
}
```
