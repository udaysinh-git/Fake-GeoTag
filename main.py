from core.runner import Runner
from cli.interface import print_banner
from core.config import get_settings

def main():
    print_banner()
    config = get_settings()
    runner = Runner(config)
    runner.start()

if __name__ == "__main__":
    main()
