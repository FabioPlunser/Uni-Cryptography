#!/usr/bin/env bash

PORT="2222"

if [ "$1" == "generate" ]; then 
    if [ -z "$2" ]; then
        echo "Usage: $0 generate <username>"
        exit 1
    fi

    mkdir -p ./keys

    key_path="./keys/id_rsa_$2"
    ssh-keygen -t rsa -b 4096 -N "" -f "$key_path"
    echo "SSH key pair generated at $key_path"

elif [ "$1" == "connect" ]; then 
    if [ -z "$2" ]; then
        echo "Usage: $0 connect <username>"
        exit 1
    fi

    key_path="./keys/id_rsa_$2"
    ssh -i "$key_path" "$2@localhost" -p "$PORT"

else 
    echo "Invalid command. Use 'generate' or 'connect'."
    echo "Usage:"
    echo "  $0 generate <username> - Generate a key for a username"
    echo "  $0 connect <username> - Connect as a username"
    exit 1
fi

if [ -z "$1" ]; then
    echo "Murmly Test Client"
    echo "Usage:"
    echo "  $0 generate <username> - Generate a key for a username"
    echo "  $0 connect <username> - Connect as a username"
fi