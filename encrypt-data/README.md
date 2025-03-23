# Encrypt your data

by Fabio Plunser & Cedric Sillaber

## Run the code

### Installation
Only dependency is the `Cryptography` python package, which can be installed using `pip install cryptography`. 

### Usage
To use the CLI tool, simpy run the script using
```bash
python3 src/main.py
```
Then the cli tool will prompt you for the necessary input.


**Example input**:

```bash
Welcome to the CLI Manager, write 'help' to see the available commands
Encrypt(1) or Decrypt(2)?
>>1
Enter the path of the file to encrypt/decrypt
res/testdir
Do you want to keep the folder (1) or delete it (2)?
>>1
Enter the key of length 16
>>****************
```

*Note*: Run the code from the root directory, not from `src`!
