import PyInstaller.__main__

PyInstaller.__main__.run([
    'code/clientapp.py',
    '--onefile',
    '--windowed',
    '--noconsole',
    '--name=ChatClient',
    '--icon=input.png',
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.simpledialog',
])