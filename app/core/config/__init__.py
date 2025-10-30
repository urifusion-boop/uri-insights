from .browsercloud_platform_config import BrowsercloudPlatformConfig

# Import settings from the config.py file (sibling to this package directory)
# Use importlib to load the module file directly since both config.py and config/ exist
import importlib.util
import sys
from pathlib import Path

_config_py_path = Path(__file__).parent.parent / "config.py"
_spec = importlib.util.spec_from_file_location("app.core._config_module", _config_py_path)
_config_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_module)
settings = _config_module.settings

__all__ = ['BrowsercloudPlatformConfig', 'settings']