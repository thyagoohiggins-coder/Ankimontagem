const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1300,
    height: 860,
    minWidth: 760,
    minHeight: 520,
    title: 'Montador de Flashcards',
    icon: path.join(__dirname, 'build', 'icon.png'),
    backgroundColor: '#f4f6f8',
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true }
  });
  win.loadFile(path.join(__dirname, 'index.html'));
  // Links externos abrem no navegador padrão
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
}

Menu.setApplicationMenu(Menu.buildFromTemplate([
  { label: 'Arquivo', submenu: [{ role: 'quit', label: 'Sair' }] },
  { label: 'Editar', submenu: [
    { role: 'undo', label: 'Desfazer' }, { role: 'redo', label: 'Refazer' }, { type: 'separator' },
    { role: 'cut', label: 'Recortar' }, { role: 'copy', label: 'Copiar' }, { role: 'paste', label: 'Colar' },
    { role: 'selectAll', label: 'Selecionar tudo' }
  ] },
  { label: 'Exibir', submenu: [
    { role: 'zoomIn', label: 'Aumentar zoom' }, { role: 'zoomOut', label: 'Diminuir zoom' },
    { role: 'resetZoom', label: 'Zoom normal' }, { type: 'separator' },
    { role: 'togglefullscreen', label: 'Tela cheia' }, { role: 'reload', label: 'Recarregar' }
  ] }
]));

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
