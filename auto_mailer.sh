#!/bin/bash
cd ~/wealth-machine
git config pull.rebase true
while true; do
    if [[ -n $(git status -s) ]]; then
        git add .
        git commit -m "Cloud Write"
    fi
    git pull origin master > /dev/null 2>&1
    git push origin master > /dev/null 2>&1
    sleep 3
done
