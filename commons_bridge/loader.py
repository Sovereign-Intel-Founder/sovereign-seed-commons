import importlib
import yaml
from typing import List
from commons_bridge.adapters.base import BaseStreamAdapter

def load_adapters_from_config(config_path: str = "commons_bridge/config.yaml") -> List[BaseStreamAdapter]:
    """Dynamically load and initialize stream adapters defined in configuration."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    loaded_adapters = []
    for entry in config.get("adapters", []):
        module_name = entry.get("module")
        class_name = entry.get("class")
        adapter_config = entry
        
        # Dynamically import module and retrieve class
        module = importlib.import_module(module_name)
        adapter_class = getattr(module, class_name)
        
        # Instantiate adapter
        adapter = adapter_class(adapter_config)
        loaded_adapters.append(adapter)
        
    return loaded_adapters
