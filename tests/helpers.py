import selectors
import asyncio


# Inherited from https://github.com/Martiusweb/asynctest/, credits of
# respective authors.
# Please see https://github.com/Martiusweb/asynctest/blob/master/LICENSE for
# the license.
def set_read_ready(fileobj):
    def _set_event_ready(fileobj, loop, event):
        selector = loop._selector
        fd = selector._fileobj_lookup(fileobj)

        if fd in selector._fd_to_key:
            loop._process_events([(selector._fd_to_key[fd], event)])

    loop = asyncio.get_running_loop()
    loop.call_soon_threadsafe(
        _set_event_ready, fileobj, loop,
        selectors.EVENT_READ
    )
