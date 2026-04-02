class TomlStackError(Exception):
    """Base error for tomlconf."""


class DataPathError(TomlStackError):
    """Raised when path parsing or resolution fails."""


class ContentError(TomlStackError):
    """Raised when content validation fails."""


class MetaError(TomlStackError):
    """Base error for meta errors."""


class IncludeError(TomlStackError):
    """Raised when include resolution fails."""


class TomlFormatError(TomlStackError):
    """Raised when TOML parsing fails."""


class VersionError(MetaError):
    """Raised when version requirement is not met."""


class IncludeInvalidError(IncludeError):
    """Raised when include specification is invalid."""


class IncludeCycleError(IncludeError):
    """Raised when include cycle is detected."""


class MergeError(TomlStackError):
    """Raised when merge process fails."""


class InterpolationError(TomlStackError):
    """Raised when interpolation fails."""


class InterpolationUndefinedError(InterpolationError):
    """Raised when interpolation path is undefined."""


class InterpolationCycleError(InterpolationError):
    """Raised when interpolation cycle is detected."""
