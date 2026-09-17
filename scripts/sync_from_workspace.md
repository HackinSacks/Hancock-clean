# Sync clean rewrite onto Kali

If the agent built the tree on Grok Bot's computer first:

## Option A — GitHub branch

```powershell
wsl -d kali-linux -u root -- bash -lc 'git clone https://github.com/HackinSacks/Hancock-clean.git /root/hancock && bash /root/hancock/scripts/bootstrap_kali.sh'
```

## Option B — copy from Windows path

Place the package under `\\wsl$\kali-linux\root\hancock` then run `bootstrap_kali.sh`.
