#!/bin/bash
cp ./config/.env.example ./config/.env
find ./config -type d -exec cp {}/.env.example {}/.env  \;
