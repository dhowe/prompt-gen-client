import json

CONFIG_FILE = "obs_config.json"

def get_config_value(key_name):
    """
    Takes the name of a key in the CONFIG_FILE and returns its value.
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config[key_name]
    except (FileNotFoundError, KeyError):
        return None

def write_config_value(key_name, value):
    """
    Writes a value to a key in the CONFIG_FILE.
    If the file or key doesn't exist, it will be created.
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    config[key_name] = value
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)