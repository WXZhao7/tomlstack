class TomlConfError(Exception):
    """Base error for tomlconf."""


class ContentError(TomlConfError):
    """Raised when content validation fails."""


class MetaError(TomlConfError):
    """Base error for meta errors."""


class IncludeError(TomlConfError):
    """Raised when include resolution fails."""


class TomlFormatError(TomlConfError):
    """Raised when TOML parsing fails."""


class VersionError(MetaError):
    """Raised when version requirement is not met."""


class IncludeInvalidError(IncludeError):
    """Raised when include specification is invalid."""


class IncludeCycleError(IncludeError):
    """Raised when include cycle is detected."""


class MergeError(TomlConfError):
    """Raised when merge process fails."""


class InterpolationError(TomlConfError):
    """Raised when interpolation fails."""


class InterpolationUndefinedError(InterpolationError):
    """Raised when interpolation path is undefined."""


class InterpolationCycleError(InterpolationError):
    """Raised when interpolation cycle is detected."""
