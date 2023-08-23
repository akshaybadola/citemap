from dataclasses import dataclass
from .util import PathLike

from . import actions

import yaml


@dataclass
class Binding:
    action: str
    key: str | list[str]


@dataclass
class Config:
    data_dir: PathLike
    keybindings: list[Binding]


def load_config(config_file: PathLike):
    with open(config_file) as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    keybindings = [Binding(**b) for b in config["keybindings"]]
    keys = []
    for binding in keybindings:
        if binding.action.replace(" ", "_").lower() not in actions.__dict__:
            raise AttributeError(f"Unknown action {binding.action.name}")
        if isinstance(binding.key, str):
            keys.append(binding.key)
        else:
            keys.extend(binding.key)
    if len(set(keys)) < len(keys):
        raise ValueError("There are duplicate key bindings in the config")
    return Config(data_dir=config["data_dir"], keybindings=keybindings)
