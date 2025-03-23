from cli import CLIManager, Config
from encrypt import Encryptor

def main():
    cli = CLIManager()
    config: Config = cli.get_information()
    enc = Encryptor()

    # we want to encrypt
    if config.encrypt:
        enc.compress_and_encrypt(
            folder_path=config.path,
            pwd=config.key,
            delete_original=not config.keep_folder
        )

    else:
        enc.decrypt_and_uncompress(
            file_path=config.path,
            pwd=config.key
        )
        
    print("Done!")


if __name__ == '__main__':
    main()