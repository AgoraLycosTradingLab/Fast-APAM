"""Source-checkout launcher. Uses its own folder, venv and argument lists."""
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def run_operation(python, arguments):
    result = subprocess.run([str(python), '-m', 'fast_apam', *arguments])
    if result.returncode:
        print('\nFast APAM did not complete. Read the error above.', flush=True)
        if arguments and arguments[0] == 'run':
            print('No new model results were published by this attempt.\n'
                  'Correct the reported error and run again.', flush=True)
    elif arguments and arguments[0] == 'run' and '--output' in arguments:
        output = Path(arguments[arguments.index('--output') + 1]).resolve()
        print('\nFast APAM run finished.\nResults: ' + str(output / 'results.csv') +
              '\nUnscored stocks and reasons: ' + str(output / 'exceptions.csv') +
              '\nRun details: ' + str(output / 'run.json'), flush=True)
    elif arguments and arguments[0] == 'prepare-data':
        print('\nPreparation finished. These are financial candidates, not scored model results.', flush=True)
    elif arguments and arguments[0] == 'verify-contexts':
        print('\nInline, quarter and TTM preparation finished. These remain candidate signals, not scored model results.', flush=True)
    elif arguments and arguments[0] == 'resolve-cohort':
        print('\nDated ETF peer candidates and audit are ready. These are not scored model results.', flush=True)
    return result.returncode


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
        return run_operation(python, sys.argv[1:])
    print('\nFast APAM research pilot\n'
          '1. Check my ticker file (offline)\n'
          '2. Download SEC financial candidates (internet required)\n'
          '3. Run my stock list against a prepared scoring snapshot\n'
          '4. Verify inline contexts and construct candidate signals (internet required)\n'
          '5. Build dated ETF peer and sector proxy\n'
          '\nOptions 2, 4 and 5 do not yet produce scores. Peer coverage and financial construction remain required.')
    choice = input('Choose 1, 2, 3, 4 or 5: ').strip()
    if choice not in {'1', '2', '3', '4', '5'}:
        print('No action selected.')
        return 1
    if choice == '4':
        folder = input('Existing preparation folder: ').strip().strip('"')
        if not folder:
            print('A preparation folder is required.')
            return 1
        return run_operation(python, ['verify-contexts', '--preparation', folder])
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
    elif choice == '5':
        output = input('New ETF proxy folder [data/etf-proxy-' + day + ']: ').strip().strip('"')
        holdings = input('Existing dated IVV holdings CSV [Enter to use official latest download or local archive]: ').strip().strip('"')
        arguments = ['resolve-cohort', '--date', day, '--universe', universe,
                     '--output', output or 'data/etf-proxy-' + day]
        if holdings:
            arguments.extend(['--holdings-file', holdings])
    else:
        arguments = ['check-setup' if choice == '1' else 'prepare-data', '--date', day, '--universe', universe]
        if choice == '2':
            output = input('New preparation folder [data/preparation-' + day + ']: ').strip().strip('"')
            arguments.extend(['--output', output or 'data/preparation-' + day])
    return run_operation(python, arguments)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled.')
        raise SystemExit(1)
