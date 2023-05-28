import json

CONFIG_FILE = "config.json"

def get_float(key_name, default_value=0.0):
    """
    Takes the name of a key in the CONFIG_FILE and returns its value as a float.
    Usage:
        import config
        config.get_float("google_sheet_show_id")
    """
    return float(get_value(key_name, default_value))
    # return ("%.4f" % val).replace("-0", "-").lstrip("0")

def get_value(key_name, default_value=None):
    """
    Takes the name of a key in the CONFIG_FILE and returns its value.
    Usage: 
        import config
        config.get_value("google_sheet_show_id")
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config[key_name]
    except (FileNotFoundError, KeyError):
        return default_value

def write_value(key_name, value):
    """
    Writes a value to a key in the CONFIG_FILE.
    If the file or key doesn't exist, it will be created.
    Usage: 
        import config
        config.write_value("google_sheet_show_id", "abc123")
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    config[key_name] = value
    
    with open(CONFIG_FILE, "w") as f:
        # json.dump(config, f)
        json.dump(config, f, indent=4, sort_keys=True)