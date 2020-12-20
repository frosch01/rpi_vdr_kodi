def main():
    """Entry point for the WOL listener"""
    import asyncio
    from kodi_wol_listener.wol_listener_subproc import KodiManager
    kodi = KodiManager()
    asyncio.run(kodi.main())
