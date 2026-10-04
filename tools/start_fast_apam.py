"""Source-checkout launcher. Uses its own folder, venv and argument lists."""
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


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
          '3. Run an already prepared scoring snapshot\n'
          '\nOption 2 does not yet produce scores. Context verification and peer coverage remain required.')
    choice = input('Choose 1, 2 or 3: ').strip()
    if choice not in {'1', '2', '3'}:
        print('No action selected.')
        return 1
    day = input('Model date (YYYY-MM-DD or latest) [latest]: ').strip() or 'latest'
    if choice == '3':
        source = input('Prepared snapshot folder: ').strip().strip('"')
        output = input('New results folder: ').strip().strip('"')
        if not source or not output:
            print('Both folders are required.')
            return 1
        arguments = ['run', '--date', day, '--source', source, '--output', output]
    else:
        universe = input('Ticker CSV path [universe.csv]: ').strip().strip('"') or 'universe.csv'
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
