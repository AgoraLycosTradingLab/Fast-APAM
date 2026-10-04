"""Source-checkout launcher. Uses its own folder, venv and argument lists."""
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def choose_universe():
    value = input('Ticker CSV path, or press Enter to browse: ').strip().strip('"')
    if value:
        return value
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print('File picker unavailable. Paste your CSV path instead.')
        return input('Ticker CSV path: ').strip().strip('"')
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        return filedialog.askopenfilename(parent=root, title='Select your stock universe CSV',
            initialdir=str(ROOT), filetypes=[('Ticker CSV', '*.csv')])
    except tk.TclError:
        print('File picker unavailable. Paste your CSV path instead.')
        return input('Ticker CSV path: ').strip().strip('"')
    finally:
        if root is not None:
            root.destroy()


def main():
    if sys.version_info < (3, 11):
        print('Fast APAM requires Python 3.11 or newer.')
        return 1
    os.chdir(ROOT)
    environment = ROOT / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('Creating a Python environment for this copy of Fast APAM...', flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    # Avoid reinstalling on every launch. --setup explicitly repairs the installation.
    installed = subprocess.run([str(python), '-c',
        'import fast_apam, lxml, tzdata, pathlib, sys; '
        'sys.exit(pathlib.Path(fast_apam.__file__).resolve().parent != pathlib.Path(sys.argv[1]).resolve())',
        str(ROOT / 'src' / 'fast_apam')], capture_output=True).returncode == 0
    if not installed or sys.argv[1:] == ['--setup']:
        print('Installing Fast APAM and its required packages...', flush=True)
        result = subprocess.run([str(python), '-m', 'pip', 'install', '-e', str(ROOT)])
        if result.returncode:
            return result.returncode
    if sys.argv[1:]:
        if sys.argv[1:] == ['--setup']:
            print('Setup complete. Open Fast APAM.cmd to continue.')
            return 0
        return subprocess.run([str(python), '-m', 'fast_apam', *sys.argv[1:]]).returncode
    print('\nFast APAM research pilot\n'
          '1. Check my ticker file (offline)\n'
          '2. Download SEC financial candidates (internet required)\n'
          '3. Run my stock list against a prepared scoring snapshot\n'
          '\nOption 2 does not yet produce scores. Context verification and peer coverage remain required.')
    choice = input('Choose 1, 2 or 3: ').strip()
    if choice not in {'1', '2', '3'}:
        print('No action selected.')
        return 1
    day = input('Model date (YYYY-MM-DD or latest) [latest]: ').strip() or 'latest'
    universe = choose_universe()
    if not universe:
        print('No stock list selected. Cancelled.')
        return 1
    if choice == '3':
        source = input('Prepared snapshot folder [Enter to use the local database]: ').strip().strip('"')
        output = input('New results folder: ').strip().strip('"')
        if not output:
            print('A new results folder is required.')
            return 1
        arguments = ['run', '--date', day, '--universe', universe, '--output', output]
        if source:
            arguments.extend(['--source', source])
    else:
        arguments = ['check-setup' if choice == '1' else 'prepare-data', '--date', day, '--universe', universe]
        if choice == '2':
            output = input('New preparation folder [data/preparation-' + day + ']: ').strip().strip('"')
            arguments.extend(['--output', output or 'data/preparation-' + day])
    return subprocess.run([str(python), '-m', 'fast_apam', *arguments]).returncode


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled.')
        raise SystemExit(1)
