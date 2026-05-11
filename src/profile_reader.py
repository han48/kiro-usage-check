"""Profile Reader module for reading Chrome profile paths from a text file."""

import os


class ProfileReader:
    """Reads Chrome profile paths from a configuration file."""

    def __init__(self, file_path: str):
        """Initialize with path to profile list file.

        Args:
            file_path: Path to the text file containing profile paths.
        """
        self.file_path = file_path

    def read_profiles(self) -> list[str]:
        """Read and return valid profile paths from file.

        Skips empty lines and lines starting with '#'.
        Raises FileNotFoundError if file doesn't exist.
        Returns empty list if no valid entries found.

        Returns:
            List of valid profile path strings.

        Raises:
            FileNotFoundError: If the profile list file does not exist.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(
                f"Profile list file not found: {self.file_path}"
            )

        profiles = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped == "" or stripped.startswith("#"):
                    continue
                profiles.append(stripped)

        return profiles
