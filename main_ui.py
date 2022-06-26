import asyncio

import nest_asyncio
import wxasync

from ui.main_frame import MainFrame
from ble_assistant import __version__


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    nest_asyncio.apply(loop)
    app = wxasync.WxAsyncApp()
    title = f'Ble({__version__})'
    frame = MainFrame(title=title)
    frame.Show()
    app.SetTopWindow(frame)
    loop.run_until_complete(app.MainLoop())
    loop.close()
