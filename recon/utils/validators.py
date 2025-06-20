import re
import ipaddress
from typing import Union, Optional, List, Pattern
from urllib.parse import urlparse


class ValidationException(Exception):
    """Exception raised when validation fails."""

    def __init__(self, input_value: str, validator: str, details: Optional[str] = None):
        self.input_value = input_value
        self.validator = validator
        self.details = details

        message = f"Input failed {validator} validation: {input_value}"
        if details:
            message += f" ({details})"

        super().__init__(message)


class BaseValidator:
    """Base class for all input validators."""

    def __init__(self, regex: Union[str, Pattern], validator: Optional[str] = None, flags: int = 0):
        """
        Initialize the validator.

        Args:
            regex: Regular expression pattern (string or compiled)
            validator: Name of the validator for error messages
            flags: Regex compilation flags
        """
        if isinstance(regex, str):
            self.match_object = re.compile(regex, flags)
        else:
            self.match_object = regex
        self.validator = validator or self.__class__.__name__.replace('Validator', '').lower()

    def validate(self, value: str) -> None:
        """
        Validate the input value.

        Args:
            value: Input string to validate

        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationException(str(value), self.validator, "Input must be a string")

        if not value.strip():
            raise ValidationException(value, self.validator, "Input cannot be empty")

        if self.match_object.match(value.strip()) is None:
            raise ValidationException(value, self.validator)

    def is_valid(self, value: str) -> bool:
        """
        Check if value is valid without raising exceptions.

        Args:
            value: Input string to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            self.validate(value)
            return True
        except ValidationException:
            return False

    def filter_valid(self, values: List[str]) -> List[str]:
        """
        Filter a list to return only valid values.

        Args:
            values: List of strings to filter

        Returns:
            List[str]: List containing only valid values
        """
        return [value for value in values if self.is_valid(value)]


class DomainValidator(BaseValidator):
    """Validator for domain names."""

    def __init__(self):
        # Enhanced domain regex with better subdomain support
        regex = (
            r"^(?=.{1,253}\.?$)"  # Total length check
            r"(?!"  # Negative lookahead for invalid patterns
            r".*\.\d+$|"  # Not ending with .<number>
            r".*\.$\."  # Not ending with multiple dots
            r")"
            r"(?:"
            r"[a-zA-Z0-9]"  # First character must be alphanumeric
            r"[a-zA-Z0-9\-]{0,61}"  # Middle characters (max 63 per label)
            r"[a-zA-Z0-9]"  # Last character must be alphanumeric
            r"\."  # Dot separator
            r")+"
            r"[a-zA-Z]{2,63}\.?$"  # TLD (2-63 characters, optional trailing dot)
        )
        super().__init__(regex, 'domain')

    def validate(self, value: str) -> None:
        """Enhanced domain validation with additional checks."""
        super().validate(value)

        # Additional checks
        domain = value.strip().rstrip('.')
        labels = domain.split('.')

        # Check individual label constraints
        for label in labels:
            if len(label) > 63:
                raise ValidationException(value, self.validator,
                                          f"Label '{label}' exceeds 63 characters")
            if label.startswith('-') or label.endswith('-'):
                raise ValidationException(value, self.validator,
                                          f"Label '{label}' cannot start or end with hyphen")


class UrlValidator(BaseValidator):
    """Validator for URLs with enhanced security checks."""

    def __init__(self, schemes: Optional[List[str]] = None):
        """
        Initialize URL validator.

        Args:
            schemes: List of allowed schemes (default: http, https, ftp, ftps)
        """
        self.allowed_schemes = schemes or ['http', 'https', 'ftp', 'ftps']

        # Comprehensive URL regex
        regex = (
            r"^(?:(?P<scheme>https?|ftps?)://)?"  # Optional scheme
            r"(?:"
            # Domain name or IP
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
            r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # Domain
            r"localhost|"  # Localhost
            r"\[[0-9a-f:]+\]|"  # IPv6
            r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?))"  # IPv4
            r"(?::\d+)?"  # Optional port
            r"(?:/?|[/?]\S+)$"  # Path
        )
        super().__init__(regex, 'url', re.IGNORECASE)

    def validate(self, value: str) -> None:
        """Enhanced URL validation with security checks."""
        super().validate(value)

        url = value.strip()

        # Parse URL for additional validation
        try:
            parsed = urlparse(url if '://' in url else f'http://{url}')
        except Exception:
            raise ValidationException(value, self.validator, "Unable to parse URL")

        # Scheme validation
        if parsed.scheme and parsed.scheme.lower() not in self.allowed_schemes:
            raise ValidationException(value, self.validator,
                                      f"Scheme '{parsed.scheme}' not allowed")

        # Security checks
        if parsed.hostname:
            # Check for suspicious patterns
            suspicious_patterns = [
                r'xn--',  # Punycode (potential IDN homograph attack)
                r'[^\x00-\x7F]',  # Non-ASCII characters
            ]

            for pattern in suspicious_patterns:
                if re.search(pattern, parsed.hostname):
                    raise ValidationException(value, self.validator,
                                              "Potentially malicious hostname detected")


class EmailValidator(BaseValidator):
    """Enhanced email validator with domain verification."""

    def __init__(self, allow_smtputf8: bool = False):
        """
        Initialize email validator.

        Args:
            allow_smtputf8: Allow international characters (SMTPUTF8)
        """
        self.allow_smtputf8 = allow_smtputf8

        if allow_smtputf8:
            # More permissive regex for international emails
            regex = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        else:
            # Standard ASCII-only email regex
            regex = (
                r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
                r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
                r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
            )

        super().__init__(regex, 'email')

    def validate(self, value: str) -> None:
        """Enhanced email validation with length and format checks."""
        super().validate(value)

        email = value.strip().lower()

        # Check total length (RFC 5321 limit)
        if len(email) > 254:
            raise ValidationException(value, self.validator,
                                      "Email address too long (max 254 characters)")

        # Split and validate parts
        try:
            local, domain = email.rsplit('@', 1)
        except ValueError:
            raise ValidationException(value, self.validator, "Invalid email format")

        # Local part validation
        if len(local) > 64:
            raise ValidationException(value, self.validator,
                                      "Local part too long (max 64 characters)")

        # Domain part validation using DomainValidator
        domain_validator = DomainValidator()
        try:
            domain_validator.validate(domain)
        except ValidationException:
            raise ValidationException(value, self.validator, "Invalid domain part")


class IPValidator(BaseValidator):
    """Validator for IP addresses (IPv4 and IPv6)."""

    def __init__(self, allow_ipv4: bool = True, allow_ipv6: bool = True,
                 allow_private: bool = True, allow_loopback: bool = True):
        """
        Initialize IP validator.

        Args:
            allow_ipv4: Allow IPv4 addresses
            allow_ipv6: Allow IPv6 addresses
            allow_private: Allow private IP ranges
            allow_loopback: Allow loopback addresses
        """
        self.allow_ipv4 = allow_ipv4
        self.allow_ipv6 = allow_ipv6
        self.allow_private = allow_private
        self.allow_loopback = allow_loopback

        # Combine IPv4 and IPv6 patterns
        patterns = []
        if allow_ipv4:
            patterns.append(r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)")
        if allow_ipv6:
            patterns.append(r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::1|::")

        regex = f"^(?:{'|'.join(patterns)})$" if patterns else "^$"
        super().__init__(regex, 'ip')

    def validate(self, value: str) -> None:
        """Validate IP address with additional security checks."""
        if not self.allow_ipv4 and not self.allow_ipv6:
            raise ValidationException(value, self.validator, "No IP versions allowed")

        try:
            ip_obj = ipaddress.ip_address(value.strip())
        except ValueError:
            raise ValidationException(value, self.validator, "Invalid IP address format")

        # Version checks
        if isinstance(ip_obj, ipaddress.IPv4Address) and not self.allow_ipv4:
            raise ValidationException(value, self.validator, "IPv4 addresses not allowed")

        if isinstance(ip_obj, ipaddress.IPv6Address) and not self.allow_ipv6:
            raise ValidationException(value, self.validator, "IPv6 addresses not allowed")

        # Private address checks
        if ip_obj.is_private and not self.allow_private:
            raise ValidationException(value, self.validator, "Private IP addresses not allowed")

        # Loopback checks
        if ip_obj.is_loopback and not self.allow_loopback:
            raise ValidationException(value, self.validator, "Loopback addresses not allowed")


class PortValidator(BaseValidator):
    """Validator for network ports."""

    def __init__(self, min_port: int = 1, max_port: int = 65535,
                 allow_well_known: bool = True):
        """
        Initialize port validator.

        Args:
            min_port: Minimum allowed port number
            max_port: Maximum allowed port number
            allow_well_known: Allow well-known ports (1-1023)
        """
        self.min_port = min_port
        self.max_port = max_port
        self.allow_well_known = allow_well_known

        regex = r"^\d+$"
        super().__init__(regex, 'port')

    def validate(self, value: str) -> None:
        """Validate port number with range checks."""
        super().validate(value)

        try:
            port = int(value.strip())
        except ValueError:
            raise ValidationException(value, self.validator, "Port must be a number")

        if port < self.min_port or port > self.max_port:
            raise ValidationException(value, self.validator,
                                      f"Port must be between {self.min_port} and {self.max_port}")

        if not self.allow_well_known and 1 <= port <= 1023:
            raise ValidationException(value, self.validator,
                                      "Well-known ports (1-1023) not allowed")


class HashValidator(BaseValidator):
    """Validator for various hash formats."""

    HASH_PATTERNS = {
        'md5': r'^[a-fA-F0-9]{32}$',
        'sha1': r'^[a-fA-F0-9]{40}$',
        'sha256': r'^[a-fA-F0-9]{64}$',
        'sha512': r'^[a-fA-F0-9]{128}$',
    }

    def __init__(self, hash_types: Optional[List[str]] = None):
        """
        Initialize hash validator.

        Args:
            hash_types: List of allowed hash types (default: all)
        """
        self.hash_types = hash_types or list(self.HASH_PATTERNS.keys())

        # Create combined regex pattern
        patterns = [self.HASH_PATTERNS[ht] for ht in self.hash_types
                    if ht in self.HASH_PATTERNS]
        regex = f"^(?:{'|'.join(patterns)})$" if patterns else "^$"

        super().__init__(regex, 'hash')

    def get_hash_type(self, value: str) -> Optional[str]:
        """
        Determine the hash type of a given value.

        Args:
            value: Hash string to analyze

        Returns:
            str: Hash type name or None if not recognized
        """
        value = value.strip()
        for hash_type, pattern in self.HASH_PATTERNS.items():
            if re.match(pattern, value) and hash_type in self.hash_types:
                return hash_type
        return None


# Convenience factory functions
def create_domain_validator() -> DomainValidator:
    """Create a standard domain validator."""
    return DomainValidator()


def create_url_validator(secure_only: bool = False) -> UrlValidator:
    """Create a URL validator with optional security restrictions."""
    schemes = ['https'] if secure_only else ['http', 'https', 'ftp', 'ftps']
    return UrlValidator(schemes=schemes)


def create_email_validator(international: bool = False) -> EmailValidator:
    """Create an email validator with optional international support."""
    return EmailValidator(allow_smtputf8=international)


def create_public_ip_validator() -> IPValidator:
    """Create an IP validator that only allows public addresses."""
    return IPValidator(allow_private=False, allow_loopback=False)


# Validation helper functions
def validate_multiple(validators: List[BaseValidator], value: str) -> bool:
    """
    Validate a value against multiple validators (OR logic).

    Args:
        validators: List of validators to check against
        value: Value to validate

    Returns:
        bool: True if any validator passes, False otherwise
    """
    return any(validator.is_valid(value) for validator in validators)


def validate_all(validators: List[BaseValidator], value: str) -> bool:
    """
    Validate a value against all validators (AND logic).

    Args:
        validators: List of validators to check against
        value: Value to validate

    Returns:
        bool: True if all validators pass, False otherwise
    """
    return all(validator.is_valid(value) for validator in validators)