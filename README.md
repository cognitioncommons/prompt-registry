# prompt-registry

Version-controlled prompt templates with variables for LLM applications.

## Features

- **Jinja2 Templates**: Use familiar Jinja2 syntax for variable substitution
- **Version Control**: Support multiple versions of the same prompt
- **Validation**: Validate templates and inputs before rendering
- **YAML Storage**: Human-readable YAML files for prompt storage
- **CLI Tools**: Manage prompts from the command line
- **Type Safety**: Full type hints for IDE support

## Installation

```bash
pip install prompt-registry
```

Or install from source:

```bash
pip install -e .
```

## Quick Start

### Initialize a prompts directory

```bash
prompt-registry init
```

This creates a `prompts/` directory with an example template.

### Create a prompt template

Create `prompts/summarize.yaml`:

```yaml
name: summarize
version: 1
description: Summarize text content
variables:
  text:
    required: true
    description: Text to summarize
  max_length:
    required: false
    default: 100
    description: Maximum length in words
template: |
  Summarize the following text in {{ max_length }} words or less:

  {{ text }}
```

### Use the CLI

```bash
# List all prompts
prompt-registry list

# Show prompt details
prompt-registry show summarize

# Render a prompt with variables
prompt-registry render summarize --var text="This is some long text..." --var max_length=50

# Validate all prompts
prompt-registry validate

# Create a new prompt
prompt-registry new my-prompt -d "My prompt description" --var input!:required --var context?:optional
```

### Use in Python

```python
from prompt_registry import PromptRegistry, PromptTemplate

# Load prompts from directory
registry = PromptRegistry("./prompts")
registry.load()

# Get and render a template
template = registry.get("summarize")
rendered = template.render(text="Long text here...", max_length=50)
print(rendered)

# Or render directly from registry
rendered = registry.render("summarize", text="Long text here...")

# Get a specific version
template_v1 = registry.get("summarize", version=1)

# List all prompts
for name in registry.list_prompts():
    print(name, registry.list_versions(name))
```

## Prompt File Format

Prompts are stored as YAML files with the following structure:

```yaml
name: prompt-name
version: 1
description: Description of what the prompt does
variables:
  variable_name:
    required: true  # or false
    default: "default value"  # optional, for non-required variables
    description: Description of this variable
template: |
  Your prompt template with {{ variable_name }} placeholders.
```

### Variable Specification

Variables can be:

- **Required**: Must be provided when rendering
- **Optional**: Can have a default value

```yaml
variables:
  input_text:
    required: true
    description: The main input text
  tone:
    required: false
    default: professional
    description: The tone of the output
```

### Versioning

To create multiple versions, use different files or include the version in the filename:

```
prompts/
  summarize.yaml      # version 1
  summarize_v2.yaml   # version 2
```

Each file should have the correct `version` field.

## CLI Reference

### `prompt-registry init`

Initialize the prompts directory with an example template.

```bash
prompt-registry init
prompt-registry init -d /path/to/prompts
```

### `prompt-registry list`

List all available prompt templates.

```bash
prompt-registry list
```

### `prompt-registry show <name>`

Show details of a specific prompt.

```bash
prompt-registry show summarize
prompt-registry show summarize --version 2
```

### `prompt-registry render <name>`

Render a prompt with variables.

```bash
prompt-registry render summarize --var text="Hello world" --var max_length=50
prompt-registry render summarize -V text="Hello world" -v 2
```

### `prompt-registry validate`

Validate all prompt templates in the directory.

```bash
prompt-registry validate
```

### `prompt-registry new <name>`

Create a new prompt template.

```bash
prompt-registry new my-prompt
prompt-registry new my-prompt -d "Description" --var input!:required --var context?:optional
```

Variable format: `name[!|?]:description`
- `!` suffix marks required (default)
- `?` suffix marks optional

## Python API Reference

### PromptTemplate

```python
from prompt_registry import PromptTemplate

# Create from dict
template = PromptTemplate.from_dict({
    "name": "example",
    "version": 1,
    "description": "Example prompt",
    "variables": {
        "input": {"required": True, "description": "Input text"}
    },
    "template": "Process this: {{ input }}"
})

# Render
result = template.render(input="Hello")

# Validate template
errors = template.validate()

# Validate inputs
errors = template.validate_inputs({"input": "Hello"})

# Get variable info
required = template.get_required_variables()
optional = template.get_optional_variables()
```

### PromptRegistry

```python
from prompt_registry import PromptRegistry

# Initialize
registry = PromptRegistry("./prompts")
registry.load()

# Get templates
template = registry.get("name")
template = registry.get("name", version=2)

# List prompts
names = registry.list_prompts()
versions = registry.list_versions("name")

# Render directly
result = registry.render("name", variable="value")

# Validate all
errors = registry.validate_all()

# Create new prompt
path = registry.create_prompt(
    name="new-prompt",
    template="Hello {{ name }}",
    description="A greeting prompt",
    variables={"name": {"required": True}}
)
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black prompt_registry/
ruff check prompt_registry/

# Type check
mypy prompt_registry/
```

## License

MIT
