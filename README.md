# rpi_vdr_kodi
Integrate RPI based KODI with my living room

## Why

My Kodi setup is based on a Raspberry PI. On the backend, a vdr server is running for receiving TV and making recordings. In order to preserve energy the server is configured to go to sleep when nobody uses it and no recording is requested.

The vnsi interface of kodi (connection between kodi and vdr) keeps vdr always woken up. There is no option to disconnect in case of inactivity. So the idea is to stop kodi when it is unused, letting the vdr server enter power saving state.

But how to get kodi back after it has been stopped? Before this can be answered, the next question is on how to control kodi? First I went into using the wonderful lirc. But having a dedicated commander starts messing up the living room with these controllers. Using another level of the television shipped one is too hard to handle and you always give the commands to the wrong device.

Today, there is kore, the wonderful Android app that gives control to kodi from your smartphone. Ok, now we are close the orignial question: How to get kodi started? kore supports the generation of a WOL packet used by PC firmware to wakeup PCs from suspend. This is a UDP/IP packet and can also be received from a userspace application. So this is the trick to be done. As the WOL packet is seen on the network, kodi is started.
