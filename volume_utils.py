import os
import subprocess
import re
import pwd

def get_system_volume():
    """
    Fetches the current system volume using wpctl or amixer.
    Returns: int (0-100 fallback 50 on error)
    """
    
    sudo_user = os.environ.get("SUDO_USER")
    
    def run_cmd(cmd_list):
        if sudo_user:
            try:
                uid = pwd.getpwnam(sudo_user).pw_uid
                env = os.environ.copy()
                env['XDG_RUNTIME_DIR'] = f"/run/user/{uid}"
                env['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path=/run/user/{uid}/bus"
                
                sudo_cmd = ["sudo", "-u", sudo_user, "-E"] + cmd_list
                return subprocess.run(sudo_cmd, capture_output=True, text=True, timeout=1, env=env)
            except Exception:
                pass
        
        return subprocess.run(cmd_list, capture_output=True, text=True, timeout=1)

    try:
        # Try pipewire first
        res = run_cmd(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        if res.returncode == 0:
            # Example output: "Volume: 0.50" or "Volume: 0.50 [MUTED]"
            # Use regex to find strictly the decimal number
            match = re.search(r"Volume:\s*([\d\.]+)", res.stdout)
            if match:
                vol_float = float(match.group(1))
                return int(vol_float * 100)
    except Exception as e:
        print(f"wpctl error: {e}")
        pass
    
    try:
        # Try ALSA second
        res = run_cmd(["amixer", "sget", "Master"])
        if res.returncode == 0:
            match = re.search(r"\[(\d+)%\]", res.stdout)
            if match:
                return int(match.group(1))
    except Exception:
        pass
        
    return 50 # Fallback
