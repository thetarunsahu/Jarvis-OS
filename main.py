from dotenv import load_dotenv

load_dotenv()

from core.jarvis import Jarvis


def main():
    jarvis = Jarvis()
    jarvis.start()


if __name__ == "__main__":
    main()
    
    