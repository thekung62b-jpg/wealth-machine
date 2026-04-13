#!/bin/bash
cd ~/wealth-machine
while true; do
    if [[ -n $(git status -s commands.json) ]]; then
        git add commands.json
        git commit -m "Auto-Mailer dispatch"
        git push
    fi
    sleep 5
done
