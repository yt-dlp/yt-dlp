import { app, Menu, shell, type BrowserWindow, type MenuItemConstructorOptions } from 'electron';

export function buildMenu(win: () => BrowserWindow | null, dev: boolean): Menu {
  const mac = process.platform === 'darwin';
  const send = (cmd: string) => () => win()?.webContents.send('command', cmd);
  const settings: MenuItemConstructorOptions = { label: mac ? 'Settings…' : 'Settings', accelerator: 'CmdOrCtrl+,', click: send('view:settings') };

  const template: MenuItemConstructorOptions[] = [
    ...(mac ? [{
      label: app.name,
      submenu: [
        { role: 'about' }, { label: 'Check for Updates…', click: send('check-updates') }, { type: 'separator' },
        settings, { type: 'separator' }, { role: 'services' }, { type: 'separator' },
        { role: 'hide' }, { role: 'hideOthers' }, { role: 'unhide' }, { type: 'separator' }, { role: 'quit' },
      ],
    } as MenuItemConstructorOptions] : []),
    {
      label: '&File',
      submenu: [
        { label: 'New Download', accelerator: 'CmdOrCtrl+N', click: send('new') },
        { label: 'Paste Links and Add', accelerator: 'CmdOrCtrl+Shift+V', click: send('paste') },
        { type: 'separator' },
        { label: 'Import Config File…', click: send('import-config') },
        { label: 'Open Download Folder', accelerator: 'CmdOrCtrl+Shift+O', click: send('open-folder') },
        ...(mac ? [] : [{ type: 'separator' } as MenuItemConstructorOptions, settings, { type: 'separator' } as MenuItemConstructorOptions, { role: 'quit' } as MenuItemConstructorOptions]),
      ],
    },
    { label: '&Edit', submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' }, { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' }] },
    {
      label: '&View',
      submenu: [
        { label: 'Downloads', accelerator: 'CmdOrCtrl+1', click: send('view:queue') },
        { label: 'History', accelerator: 'CmdOrCtrl+2', click: send('view:history') },
        { label: 'Presets', accelerator: 'CmdOrCtrl+3', click: send('view:presets') },
        { label: 'Logs', accelerator: 'CmdOrCtrl+4', click: send('view:logs') },
        { label: 'Engine', accelerator: 'CmdOrCtrl+5', click: send('view:engine') },
        { type: 'separator' },
        { label: 'Find', accelerator: 'CmdOrCtrl+F', click: send('find') },
        { type: 'separator' },
        { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' }, { role: 'togglefullscreen' },
        ...(dev ? [{ type: 'separator' } as MenuItemConstructorOptions, { role: 'reload' } as MenuItemConstructorOptions, { role: 'toggleDevTools' } as MenuItemConstructorOptions] : []),
      ],
    },
    {
      label: '&Downloads',
      submenu: [
        { label: 'Pause All', accelerator: 'CmdOrCtrl+Shift+P', click: send('pause-all') },
        { label: 'Resume All', accelerator: 'CmdOrCtrl+Shift+R', click: send('resume-all') },
        { type: 'separator' },
        { label: 'Retry Failed', click: send('retry-failed') },
        { label: 'Clear Finished', accelerator: 'CmdOrCtrl+Shift+Backspace', click: send('clear-finished') },
      ],
    },
    ...(mac ? [{ role: 'windowMenu' } as MenuItemConstructorOptions] : []),
    {
      label: '&Help',
      role: 'help',
      submenu: [
        { label: 'Dubdeck Help', accelerator: mac ? 'Cmd+?' : 'F1', click: send('view:help') },
        { label: 'Show Welcome Guide', click: send('welcome') },
        { type: 'separator' },
        { label: 'Supported Sites', click: () => shell.openExternal('https://github.com/Nardi05/yt-dlp/blob/master/supportedsites.md') },
        { label: 'Report a Problem', click: () => shell.openExternal('https://github.com/Nardi05/yt-dlp/issues') },
        ...(mac ? [] : [{ type: 'separator' } as MenuItemConstructorOptions, { label: 'Check for Updates…', click: send('check-updates') } as MenuItemConstructorOptions, { role: 'about' } as MenuItemConstructorOptions]),
      ],
    },
  ];
  return Menu.buildFromTemplate(template);
}
