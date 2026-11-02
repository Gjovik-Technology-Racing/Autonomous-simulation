"""Create and select small, self-contained architecture implementations."""
import json
from pathlib import Path
from components.architecture import architecture_path

ROOT = Path(__file__).resolve().parent
SKELETON = '''"""Stationary architecture skeleton."""


class Controller:
    def __init__(self, config, data_dir):
        self.config = config
        self.data_dir = data_dir

    def start(self):
        pass

    def update(self, observation):
        return None

    def stop(self):
        pass
'''


def list_architectures(root=ROOT):
    base = root / 'architectures'
    return sorted(f'{family.name}/{impl.name}' for family in base.iterdir() if family.is_dir()
                  for impl in family.iterdir() if impl.is_dir()
                  and (impl / 'config.json').is_file() and (impl / 'controller.py').is_file())


def create(name, template=None, root=ROOT):
    target = architecture_path(root, name)
    if target.exists():
        raise FileExistsError(f'{name} already exists')
    if template:
        source = architecture_path(root, template)
        config = json.loads((source / 'config.json').read_text(encoding='utf-8'))
        controller = (source / 'controller.py').read_text(encoding='utf-8')
    else:
        config, controller = {}, SKELETON
    # Exclusive creation ensures existing implementations are never overwritten.
    target.mkdir(parents=True, exist_ok=False)
    (target / 'config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    (target / 'controller.py').write_text(controller, encoding='utf-8')
    (target / 'data').mkdir()
    (target / 'data' / '.gitkeep').touch()


def select(name, root=ROOT):
    path = architecture_path(root, name)
    if not (path / 'config.json').is_file() or not (path / 'controller.py').is_file():
        raise ValueError('Architecture must contain config.json and controller.py')
    config_path = root / 'config.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['architecture'] = name
    config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')


def main():
    while True:
        families = sorted(path.name for path in (ROOT / 'architectures').iterdir() if path.is_dir() and not path.name.startswith('__'))
        print('\nFamilies: ' + (', '.join(families) or '(none)'))
        print('Implementations:')
        for item in list_architectures():
            print('  ' + item)
        print('\n1. Create  2. Select  3. Quit')
        choice = input('Choice: ').strip()
        try:
            if choice == '1':
                name = input('New family/implementation: ').strip()
                template = input('Template family/implementation (blank for skeleton): ').strip() or None
                create(name, template)
                print(f'Created {name}.')
            elif choice == '2':
                name = input('Select family/implementation: ').strip()
                select(name)
                print(f'Selected {name}.')
            elif choice in ('3', 'q', 'quit'):
                return
            else:
                print('Choose 1, 2, or 3.')
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f'Error: {exc}')


if __name__ == '__main__':
    main()
