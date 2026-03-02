import subprocess
import os
import pwd
sudo_user = os.environ.get("SUDO_USER")
uid = pwd.getpwnam(sudo_user).pw_uid
env = os.environ.copy()
env['XDG_RUNTIME_DIR'] = f"/run/user/{uid}"
env['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path=/run/user/{uid}/bus"

print(subprocess.run(["sudo", "-u", sudo_user, "-E", "wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True, env=env))
