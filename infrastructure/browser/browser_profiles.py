BROWSER_REGISTRO = {
    "headless": False,
    "launch_args": [],
    "no_viewport": False,
    "ignore_https_errors": False,
}

BROWSER_ESCRITORIO_WEB = {
    "headless": False,
    "launch_args": ["--start-maximized"],
    "no_viewport": True,
    "ignore_https_errors": True,
}

BROWSER_ESCRITORIO_WEB_FULLSCREEN = {
    "headless": False,
    "launch_args": [],
    "no_viewport": True,
    "ignore_https_errors": True,
    "permissions": ["clipboard-read", "clipboard-write"],
    "fullscreen": True,
    
}

BROWSER_ESCRITORIO_WEB_KIOSK = {
    "headless": False,
    "launch_args": ["--kiosk"],
    "no_viewport": True,
    "ignore_https_errors": True,
}

BROWSER_BACKGROUND = {
    "headless": True,
    "launch_args": [],
    "no_viewport": False,
    "ignore_https_errors": False,
}