"""Makes the directory a package"""
def main():
    """Entry point for the WOL listener wheel"""
    from kodi_wol_listener.wol_listener_subproc import KodiManager
    KodiManager().run()

VERSION = '0.1.0'
