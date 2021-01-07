"""Make the directory a package"""

from kodi_wol_listener.wol_listener_subproc import KodiManager

def main():
    """Entry point for the WOL listener wheel"""
    KodiManager().run()

VERSION = '0.1.0'
