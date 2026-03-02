import subprocess
import os
import pwd
sudo_user = os.environ.get("SUDO_USER")
uid = pwd.getpwnam(sudo_user).pw_uid
env = os.environ.copy()
env['XDG_RUNTIME_DIR'] = f"/run/user/{uid}"

print(subprocess.run(["sudo", "-u", sudo_user, "wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True, env=env))
