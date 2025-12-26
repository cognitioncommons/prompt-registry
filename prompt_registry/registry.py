"""PromptRegistry class for managing version-controlled prompt templates."""

import os
from pathlib import Path
from typing import Any

import yaml

from .template import PromptTemplate


class PromptRegistry:
    """Registry for managing prompt templates stored in YAML files."""

    def __init__(self, prompts_dir: str | Path | None = None):
        """
        Initialize the registry.

        Args:
            prompts_dir: Directory containing prompt YAML files.
                        Defaults to './prompts' if not specified.
        """
        if prompts_dir is None:
            prompts_dir = Path.cwd() / "prompts"
        self.prompts_dir = Path(prompts_dir)
        self._templates: dict[str, dict[int, PromptTemplate]] = {}
        self._loaded = False

    def load(self) -> None:
        """
        Load all prompt templates from the prompts directory.

        Templates are organized by name and version.
        """
        self._templates = {}

        if not self.prompts_dir.exists():
            self._loaded = True
            return

        # Load all YAML files in the prompts directory
        for yaml_file in self.prompts_dir.glob("**/*.yaml"):
            self._load_file(yaml_file)

        for yml_file in self.prompts_dir.glob("**/*.yml"):
            self._load_file(yml_file)

        self._loaded = True

    def _load_file(self, filepath: Path) -> None:
        """Load a single YAML file containing a prompt template."""
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)

            if data is None:
                return

            template = PromptTemplate.from_dict(data)

            # Use filename as name if not specified
            if template.name == "unnamed":
                template.name = filepath.stem

            # Store by name and version
            if template.name not in self._templates:
                self._templates[template.name] = {}

            self._templates[template.name][template.version] = template

        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML in {filepath}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading template from {filepath}: {e}")

    def reload(self) -> None:
        """Reload all templates from disk."""
        self._loaded = False
        self.load()

    def _ensure_loaded(self) -> None:
        """Ensure templates are loaded."""
        if not self._loaded:
            self.load()

    def get(
        self, name: str, version: int | None = None
    ) -> PromptTemplate | None:
        """
        Get a prompt template by name and optionally version.

        Args:
            name: Name of the prompt template.
            version: Specific version to retrieve. If None, returns latest.

        Returns:
            The PromptTemplate if found, None otherwise.
        """
        self._ensure_loaded()

        if name not in self._templates:
            return None

        versions = self._templates[name]

        if version is not None:
            return versions.get(version)

        # Return the latest version
        if versions:
            latest_version = max(versions.keys())
            return versions[latest_version]

        return None

    def list_prompts(self) -> list[str]:
        """Get list of all prompt names."""
        self._ensure_loaded()
        return sorted(self._templates.keys())

    def list_versions(self, name: str) -> list[int]:
        """Get list of all versions for a prompt."""
        self._ensure_loaded()
        if name not in self._templates:
            return []
        return sorted(self._templates[name].keys())

    def get_all(self) -> dict[str, list[PromptTemplate]]:
        """Get all templates organized by name."""
        self._ensure_loaded()
        result = {}
        for name, versions in self._templates.items():
            result[name] = [versions[v] for v in sorted(versions.keys())]
        return result

    def validate_all(self) -> dict[str, list[str]]:
        """
        Validate all loaded templates.

        Returns:
            Dictionary mapping template names to lists of error messages.
            Only templates with errors are included.
        """
        self._ensure_loaded()
        errors = {}

        for name, versions in self._templates.items():
            for version, template in versions.items():
                template_errors = template.validate()
                if template_errors:
                    key = f"{name}:v{version}"
                    errors[key] = template_errors

        return errors

    def create_prompt(
        self,
        name: str,
        template: str,
        description: str = "",
        variables: dict[str, dict[str, Any]] | None = None,
        version: int = 1,
    ) -> Path:
        """
        Create a new prompt template file.

        Args:
            name: Name of the prompt.
            template: Template string with Jinja2 variables.
            description: Description of the prompt.
            variables: Variable specifications.
            version: Version number.

        Returns:
            Path to the created file.
        """
        # Ensure prompts directory exists
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # Build the template data
        data: dict[str, Any] = {
            "name": name,
            "version": version,
            "description": description,
            "variables": variables or {},
            "template": template,
        }

        # Determine filename
        if version == 1:
            filename = f"{name}.yaml"
        else:
            filename = f"{name}_v{version}.yaml"

        filepath = self.prompts_dir / filename

        with open(filepath, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Reload to include the new template
        self.reload()

        return filepath

    def init_prompts_dir(self) -> Path:
        """
        Initialize the prompts directory with an example template.

        Returns:
            Path to the prompts directory.
        """
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # Create an example template
        example_path = self.prompts_dir / "example.yaml"
        if not example_path.exists():
            example_data = {
                "name": "example",
                "version": 1,
                "description": "An example prompt template",
                "variables": {
                    "topic": {
                        "required": True,
                        "description": "The topic to explain",
                    },
                    "audience": {
                        "required": False,
                        "default": "general audience",
                        "description": "Target audience for the explanation",
                    },
                },
                "template": "Explain {{ topic }} in simple terms for a {{ audience }}.\n",
            }

            with open(example_path, "w") as f:
                yaml.dump(
                    example_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
                )

        return self.prompts_dir

    def render(
        self, name: str, version: int | None = None, **kwargs: Any
    ) -> str:
        """
        Render a prompt template with the given variables.

        Args:
            name: Name of the prompt template.
            version: Specific version to use. If None, uses latest.
            **kwargs: Variable values to substitute.

        Returns:
            The rendered prompt string.

        Raises:
            ValueError: If template not found or rendering fails.
        """
        template = self.get(name, version)
        if template is None:
            raise ValueError(f"Template '{name}' not found")

        return template.render(**kwargs)

    def __len__(self) -> int:
        """Return the number of unique prompts (not counting versions)."""
        self._ensure_loaded()
        return len(self._templates)

    def __contains__(self, name: str) -> bool:
        """Check if a prompt with the given name exists."""
        self._ensure_loaded()
        return name in self._templates

    def __iter__(self):
        """Iterate over prompt names."""
        self._ensure_loaded()
        return iter(sorted(self._templates.keys()))
