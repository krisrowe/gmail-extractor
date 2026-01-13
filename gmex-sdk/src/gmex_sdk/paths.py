import os
import pathlib
import shlex

def resolve_data_dir() -> pathlib.Path:
    if env_path := os.environ.get("EMAIL_ARCHIVE_DATA_DIR"): return pathlib.Path(env_path)
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data: return pathlib.Path(xdg_data) / "email-archive"
    return pathlib.Path.home() / ".local" / "share" / "email-archive"

def resolve_token_path() -> pathlib.Path:
    if env_path := os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"): return pathlib.Path(env_path)
    return pathlib.Path.home() / ".config" / "gmail-extractor" / "token.json"

if __name__ == "__main__":
    print(f"EMAIL_ARCHIVE_DATA_DIR={shlex.quote(str(resolve_data_dir()))}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS={shlex.quote(str(resolve_token_path()))}")
