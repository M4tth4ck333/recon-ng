#!/usr/bin/env python3
"""
recon-ng/recon/core/banner.py
ANSI-Banner-Manager für Recon-ng
m4tth4ck & Enhanced Dev Team
"""

import random

class BannerColors:
    RESET      = "\033[0m"
    BOLD       = "\033[1m"
    DIM        = "\033[2m"
    UNDERLINE  = "\033[4m"
    BLINK      = "\033[5m"
    REVERSE    = "\033[7m"
    HIDDEN     = "\033[8m"
    BLACK      = "\033[30m"
    RED        = "\033[31m"
    GREEN      = "\033[32m"
    YELLOW     = "\033[33m"
    BLUE       = "\033[34m"
    MAGENTA    = "\033[35m"
    CYAN       = "\033[36m"
    WHITE      = "\033[37m"
    DEFAULT    = "\033[39m"
    BRIGHT_BLACK   = "\033[90m"
    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN    = "\033[96m"
    BRIGHT_WHITE   = "\033[97m"


class BannerWrapper:
    BANNERS = {
        'default': ('BANNER', BannerColors.BRIGHT_CYAN),
        'debug': ('BANNER_DEBUG', BannerColors.YELLOW),
        'small': ('BANNER_SMALL', BannerColors.BRIGHT_GREEN),
        'web': ('BANNER_WEB', BannerColors.CYAN),
    }

    BANNER_DEBUG = r'''
  _____                         _   _             
 |  __ \                       | | (_)            
 | |__) | ___  ___ ___  _ __   | |_ _  ___  _ __  
 |  _  // _ \/ __/ _ \| '_ \  | __| |/ _ \| '_ \ 
 | | \ \  __/ (_| (_) | | | | | |_| | (_) | | | |
 |_|  \_\___|\___\___/|_| |_|  \__|_|\___/|_| |_| 
  :: Powered by Recon-ng (Debug Mode) ::
'''

    BANNER = r'''
    _/_/_/    _/_/_/_/    _/_/_/    _/_/_/    _/      _/            _/      _/    _/_/_/
   _/    _/  _/        _/        _/      _/  _/_/    _/            _/_/    _/  _/       
  _/_/_/    _/_/_/    _/        _/      _/  _/  _/  _/  _/_/_/_/  _/  _/  _/  _/  _/_/_/
 _/    _/  _/        _/        _/      _/  _/    _/_/            _/    _/_/  _/      _/ 
_/    _/  _/_/_/_/    _/_/_/    _/_/_/    _/      _/            _/      _/    _/_/_/    

                                          /\
                                         / \\ /\
    Sponsored by...               /\  /\/  \\V  \/\
                                 / \\/ // \\\\\ \\ \/\
                                // // BLACK HILLS \/ \\
                               www.blackhillsinfosec.com

                  ____   ____   ____   ____ _____ _  ____   ____  ____
                 |____] | ___/ |____| |       |   | |____  |____ |
                 |      |   \_ |    | |____   |   |  ____| |____ |____
                                   www.practisec.com
'''

    BANNER_SMALL = r'''
RECON-NG

Sponsored by...
- BLACK HILLS INFORMATION SECURITY at www.blackhillsinfosec.com
- PRACTISEC at www.practisec.com
'''

    BANNER_WEB = r'''
                     __                                                     __      __                             
                    |  \                                                   |  \    |  \                            
  ______    ______   \$$ _______    _______   ______   _______    ______  _| $$_    \$$         _______    ______  
 /      \  /      \ |  \|       \  /       \ /      \ |       \  |      \|   $$ \  |  \ ______ |       \  /      \ 
|  $$$$$$\|  $$$$$$\| $$| $$$$$$$\|  $$$$$$$|  $$$$$$\| $$$$$$$\  \$$$$$$\\$$$$$$  | $$|      \| $$$$$$$\|  $$$$$$\
| $$   \$$| $$    $$| $$| $$  | $$| $$      | $$  | $$| $$  | $$ /      $$ | $$ __ | $$ \$$$$$$| $$  | $$| $$  | $$
| $$      | $$$$$$$$| $$| $$  | $$| $$_____ | $$__/ $$| $$  | $$|  $$$$$$$ | $$|  \| $$        | $$  | $$| $$__| $$
| $$       \$$     \| $$| $$  | $$ \$$     \ \$$    $$| $$  | $$ \$$    $$  \$$  $$| $$        | $$  | $$ \$$    $$
 \$$        \$$$$$$$ \$$ \$$   \$$  \$$$$$$$  \$$$$$$  \$$   \$$  \$$$$$$$   \$$$$  \$$         \$$   \$$ _\$$$$$$$
                                                                                                         |  \__| $$
                                                                                                          \$$    $$
                                                                                                           \$$$$$$ 
'''

    @classmethod
    def get(cls, mode='default', colorize=True):
        banner_name, color = cls.BANNERS.get(mode, cls.BANNERS['default'])
        banner_content = getattr(cls, banner_name)
        return f"{color}{banner_content}{BannerColors.RESET}" if colorize else banner_content


# Optional helper for HTML
def random_html_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))
