"""PromptTemplate class for version-controlled prompt templates with variables."""

from dataclasses import dataclass, field
from typing import Any

from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError


@dataclass
class VariableSpec:
    """Specification for a template variable."""

    name: str
    required: bool = True
    default: Any = None
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "VariableSpec":
        """Create a VariableSpec from a dictionary."""
        return cls(
            name=name,
            required=data.get("required", True),
            default=data.get("default"),
            description=data.get("description", ""),
        )


@dataclass
class PromptTemplate:
    """A prompt template with Jinja2-style variable substitution."""

    name: str
    template: str
    version: int = 1
    description: str = ""
    variables: dict[str, VariableSpec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize Jinja2 environment."""
        self._env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            keep_trailing_newline=True,
        )
        self._compiled_template = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptTemplate":
        """Create a PromptTemplate from a dictionary (e.g., parsed YAML)."""
        variables = {}
        if "variables" in data:
            for var_name, var_spec in data["variables"].items():
                if isinstance(var_spec, dict):
                    variables[var_name] = VariableSpec.from_dict(var_name, var_spec)
                else:
                    # Simple variable without spec
                    variables[var_name] = VariableSpec(name=var_name, required=True)

        return cls(
            name=data.get("name", "unnamed"),
            template=data.get("template", ""),
            version=data.get("version", 1),
            description=data.get("description", ""),
            variables=variables,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert template to dictionary for serialization."""
        result = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "variables": {},
            "template": self.template,
        }

        for var_name, var_spec in self.variables.items():
            var_dict: dict[str, Any] = {
                "required": var_spec.required,
                "description": var_spec.description,
            }
            if not var_spec.required and var_spec.default is not None:
                var_dict["default"] = var_spec.default
            result["variables"][var_name] = var_dict

        return result

    def validate(self) -> list[str]:
        """
        Validate the template.

        Returns a list of error messages. Empty list means valid.
        """
        errors = []

        # Check template syntax
        try:
            self._env.from_string(self.template)
        except TemplateSyntaxError as e:
            errors.append(f"Template syntax error: {e}")

        # Check that all template variables are defined
        try:
            template_vars = self._get_template_variables()
            for var in template_vars:
                if var not in self.variables:
                    errors.append(f"Variable '{var}' used in template but not defined in variables")
        except Exception as e:
            errors.append(f"Error parsing template variables: {e}")

        # Check version
        if not isinstance(self.version, int) or self.version < 1:
            errors.append(f"Version must be a positive integer, got: {self.version}")

        return errors

    def _get_template_variables(self) -> set[str]:
        """Extract variable names used in the template."""
        from jinja2 import meta

        ast = self._env.parse(self.template)
        return meta.find_undeclared_variables(ast)

    def validate_inputs(self, inputs: dict[str, Any]) -> list[str]:
        """
        Validate input values against variable specifications.

        Returns a list of error messages. Empty list means valid.
        """
        errors = []

        # Check required variables
        for var_name, var_spec in self.variables.items():
            if var_spec.required and var_name not in inputs:
                errors.append(f"Required variable '{var_name}' is missing")

        # Check for unknown variables
        for var_name in inputs:
            if var_name not in self.variables:
                errors.append(f"Unknown variable '{var_name}' provided")

        return errors

    def render(self, **kwargs: Any) -> str:
        """
        Render the template with the given variables.

        Args:
            **kwargs: Variable values to substitute.

        Returns:
            The rendered template string.

        Raises:
            ValueError: If required variables are missing or validation fails.
        """
        # Apply defaults for optional variables
        context = {}
        for var_name, var_spec in self.variables.items():
            if var_name in kwargs:
                context[var_name] = kwargs[var_name]
            elif not var_spec.required and var_spec.default is not None:
                context[var_name] = var_spec.default

        # Add any extra kwargs (for flexibility)
        for key, value in kwargs.items():
            if key not in context:
                context[key] = value

        # Validate inputs
        validation_errors = self.validate_inputs(context)
        if validation_errors:
            raise ValueError(f"Input validation failed: {'; '.join(validation_errors)}")

        # Render template
        try:
            template = self._env.from_string(self.template)
            return template.render(**context)
        except UndefinedError as e:
            raise ValueError(f"Template rendering failed: {e}")

    def get_required_variables(self) -> list[str]:
        """Get list of required variable names."""
        return [name for name, spec in self.variables.items() if spec.required]

    def get_optional_variables(self) -> list[str]:
        """Get list of optional variable names."""
        return [name for name, spec in self.variables.items() if not spec.required]

    def __str__(self) -> str:
        """String representation."""
        return f"PromptTemplate(name={self.name}, version={self.version})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"PromptTemplate(name={self.name!r}, version={self.version}, "
            f"variables={list(self.variables.keys())!r})"
        )
