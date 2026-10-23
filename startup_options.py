"""Per-launch startup override shared by the CLI and Lispy Machine."""
def extract_startup(argv):
    startup, remaining = None, []
    items = iter(argv)
    for item in items:
        if item == '--startup':
            value = next(items, None)
            if not value or value.startswith('--'):
                raise ValueError('--startup requires a file path')
            if startup is not None:
                raise ValueError('--startup may be specified only once')
            startup = value
        elif item.startswith('--startup='):
            if startup is not None:
                raise ValueError('--startup may be specified only once')
            startup = item.split('=', 1)[1]
            if not startup:
                raise ValueError('--startup requires a file path')
        else:
            remaining.append(item)
    return startup, remaining
