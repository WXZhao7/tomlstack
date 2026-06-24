class TomlStackError(Exception):
    """Base error for tomlstack."""


class DataPathError(TomlStackError):
    """Raised when path parsing or resolution fails."""


class ContentError(TomlStackError):
    """Raised when content validation fails."""


class IncludeError(TomlStackError):
    """Raised when include resolution fails."""


class TomlFormatError(TomlStackError):
    """Raised when TOML parsing fails."""


class IncludeCycleError(IncludeError):
    """Raised when include cycle is detected."""


class InterpolationError(TomlStackError):
    """Raised when interpolation fails."""


class InterpolationUndefinedError(InterpolationError):
    """Raised when interpolation path is undefined."""


class InterpolationCycleError(InterpolationError):
    """Raised when interpolation cycle is detected."""
