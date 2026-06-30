import ctypes
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import winreg
except ImportError:
    winreg = None

APP_TITLE = "Driver Update Blocker"
REG_PATH = r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions"
REG_BASE = winreg.HKEY_LOCAL_MACHINE if winreg else None

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        '"' + os.path.abspath(__file__) + '"',
        None,
        1
    )

if not is_admin():
    elevate()
    sys.exit()

class DriverBlockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)

        # Center the window on screen
        self.center_window()

        # Set window size after centering
        self.root.geometry("900x600")

        # Device types will be populated after first scan
        self.device_types = ["All Devices"]
        self.current_type_filter = "All Devices"

        # Dictionary to track blocked devices
        self.blocked_devices = {}

        # Dictionary to store all device data
        self.all_devices = {}

        # Main container frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Windows Driver Update Blocker",
            font=('Segoo UI', 18, 'bold')
        )
        title_label.pack(pady=(0, 10))

        # Info text
        info_label = ttk.Label(
            main_frame,
            text="Select devices you want to block from Windows Update.",
            font=('Segoo UI', 10)
        )
        info_label.pack(pady=(0, 20))

        # Filter section
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # Type filter label
        ttk.Label(filter_frame, text="Filter by Type:").pack(side=tk.LEFT, padx=(0, 5))

        # Type filter dropdown
        self.type_var = tk.StringVar(value=self.current_type_filter)
        self.type_dropdown = ttk.OptionMenu(
            filter_frame,
            self.type_var,
            self.current_type_filter,
            *self.device_types,
            command=self.apply_type_filter
        )
        self.type_dropdown.pack(side=tk.LEFT, padx=(0, 10))

        # Control bar (buttons and status)
        control_bar = ttk.Frame(main_frame)
        control_bar.pack(fill=tk.X, pady=(0, 10))

        # Buttons container
        button_container = ttk.Frame(control_bar)
        button_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        buttons = [
            ("Scan Devices", self.scan_devices),
            ("Block Selected", self.block_selected),
            ("Unblock Selected", self.unblock_selected),
            ("Restore All", self.restore_all),
            ("Refresh Policies", self.refresh_policy)
        ]

        for text, command in buttons:
            btn = ttk.Button(button_container, text=text, command=command)
            btn.pack(side=tk.LEFT, padx=5)

        # Status bar container
        status_container = ttk.Frame(control_bar)
        status_container.pack(side=tk.RIGHT, padx=(200, 0))

        self.status = tk.StringVar()
        self.status.set("Ready")

        self.status_label = ttk.Label(
            status_container,
            textvariable=self.status,
            relief="sunken",
            anchor=tk.W,
            width=30
        )
        self.status_label.pack()

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.pack_forget()  # Hide initially

        # Treeview section
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Device", "Class", "Hardware ID", "Status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")

        # Set column headings
        self.tree.heading("Device", text="Device")
        self.tree.heading("Class", text="Class")
        self.tree.heading("Hardware ID", text="Hardware ID")
        self.tree.heading("Status", text="Status")

        # Set column widths
        self.tree.column("Device", width=250)
        self.tree.column("Class", width=120)
        self.tree.column("Hardware ID", width=300)
        self.tree.column("Status", width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load blocked devices from registry on startup
        self.load_blocked_devices()

    def center_window(self):
        """Center the application window on the screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width / 2) - (900 / 2)
        y = (screen_height / 2) - (600 / 2)
        self.root.geometry(f"900x600+{int(x)}+{int(y)}")

    def run_powershell(self, command):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            startupinfo=startupinfo
        )
        return result.stdout.strip()

    def scan_devices(self):
        """Scan devices with progress bar"""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.all_devices.clear()

        # Reset device types list
        self.device_types = ["All Devices"]
        self.current_type_filter = "All Devices"
        self.type_var.set(self.current_type_filter)
        self.type_dropdown['menu'].delete(0, 'end')

        # Show progress bar
        self.status.set("Scanning devices...")
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.start(10)  # Start continuous animation

        # Run the actual scan in a separate function to allow UI updates
        self.root.after(100, self._perform_scan)

    def _perform_scan(self):
        """Perform the actual device scanning"""
        ps = '''
        $devices = Get-PnpDevice -Status OK | Select-Object FriendlyName, Class, InstanceId
        $results = @()
        $types = @()

        foreach ($device in $devices) {
            $hwid = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName "DEVPKEY_Device_HardwareIds" -ErrorAction SilentlyContinue

            if ($hwid) {
                $hwids = $hwid.Data[0].Split('\\')
                $primaryHWID = $hwid.Data[0]  # Use the full HWID instead of just the first part

                $result = [PSCustomObject]@{
                    Name = $device.FriendlyName
                    Class = $device.Class
                    HWID = $primaryHWID
                }
                $results += $result

                # Collect unique device types (filter out empty names)
                if (-not ([string]::IsNullOrWhiteSpace($device.Class)) -and (-not ($types -contains $device.Class))) {
                    $types += $device.Class
                }
            }
        }

        # Output results and types separately
        $results | ConvertTo-Csv -NoTypeInformation
        "$($types -join '|')"
        '''

        output = self.run_powershell(ps)
        lines = output.splitlines()

        # Stop the progress bar animation
        self.progress.stop()
        self.progress['value'] = 0
        self.progress.pack_forget()

        # Process the types first (last line of output)
        if len(lines) > 0:
            type_list = lines[-1].split('|')
            # Filter out any blank or whitespace-only types
            self.device_types = ["All Devices"] + [t for t in type_list if t.strip() != ""]

            # Rebuild the dropdown menu with all device types
            self.type_dropdown['menu'].delete(0, 'end')
            for type_name in self.device_types:
                self.type_dropdown['menu'].add_command(
                    label=type_name,
                    command=tk._setit(self.type_var, type_name, self.apply_type_filter)
                )

        device_count = 0

        # Process devices (all lines except last)
        for line in lines[:-1]:
            try:
                # Clean up the CSV line
                clean_line = line.strip().strip('"')
                parts = [x.strip('"') for x in clean_line.split('","')]

                # Skip if we don't have enough parts or if this is a header row
                if len(parts) < 3:
                    continue

                device = parts[0]
                devclass = parts[1]
                full_hwid = parts[2]

                # Additional validation to filter out invalid entries
                if (device.upper() == "CLASS" and devclass.upper() == "CLASS" and
                    full_hwid.upper() == "HWID"):
                    continue  # Skip the dummy header entry

                # Skip empty or invalid entries
                if not device or not full_hwid or not devclass:
                    continue

                # Determine status based on blocked_devices dictionary
                status = "Blocked" if full_hwid in self.blocked_devices else "Allowed"
                # Create a unique ID for this device
                item_id = f"{device}_{full_hwid}"

                # Only add the device if it doesn't already exist
                if item_id not in self.all_devices:
                    self.all_devices[item_id] = {
                        'values': (device, devclass, full_hwid, status),
                        'visible': True
                    }
                    self.tree.insert("", "end", iid=item_id, values=(device, devclass, full_hwid, status))
                    device_count += 1
                else:
                    # Update the status if it's changed
                    if self.all_devices[item_id]['values'][3] != status:
                        self.tree.set(item_id, "Status", status)
                        self.all_devices[item_id]['values'] = (device, devclass, full_hwid, status)
            except Exception:
                pass

        # Apply the current filter after populating the list
        self.apply_type_filter()

        self.status.set(f"Scan complete. Found {device_count} unique devices")

    def apply_type_filter(self, event=None):
        """Apply the selected type filter to the device list"""
        filter_type = self.type_var.get()
        self.current_type_filter = filter_type

        if not hasattr(self, 'all_devices') or len(self.all_devices) == 0:
            return

        count = 0

        for item_id, device_data in self.all_devices.items():
            device_class = device_data['values'][1]

            if filter_type == "All Devices":
                visible = True
            elif device_class == filter_type or filter_type == "":
                visible = True
            else:
                visible = False

            # Only update visibility if it changed
            if device_data['visible'] != visible:
                self.tree.item(item_id, tags=('hidden',) if not visible else ('shown',))

                # Show or hide the item
                if visible:
                    self.tree.detach(item_id)
                    self.tree.move(item_id, '', 'end')
                else:
                    self.tree.detach(item_id)

                device_data['visible'] = visible

            if visible:
                count += 1

        # Update status
        if filter_type == "All Devices":
            self.status.set(f"Showing all {count} devices")
        else:
            self.status.set(f"Showing {count} {filter_type} devices")

    def load_blocked_devices(self):
        """Load blocked devices from registry"""
        try:
            key = winreg.OpenKey(REG_BASE, REG_PATH + r"\DenyDeviceIDs")
            i = 0
            while True:
                try:
                    value_name, value_data, _ = winreg.EnumValue(key, i)
                    self.blocked_devices[value_data] = True
                    i += 1
                except OSError:
                    break
        except FileNotFoundError:
            pass  # No blocked devices yet

    def ensure_policy_keys(self):
        """Ensure the policy keys exist in registry"""
        try:
            key = winreg.CreateKey(REG_BASE, REG_PATH)
            winreg.SetValueEx(key, "DenyDeviceIDs", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "AllowAdminInstall", 0, winreg.REG_DWORD, 1)

            ids_key = winreg.CreateKey(REG_BASE, REG_PATH + r"\DenyDeviceIDs")
            return key, ids_key
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Failed to create policy keys: {e}")
            return None, None

    def block_selected(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(APP_TITLE, "Select at least one device.")
            return

        _, ids_key = self.ensure_policy_keys()
        if ids_key is None:
            return

        index = 1

        try:
            while True:
                winreg.EnumValue(ids_key, index - 1)
                index += 1
        except OSError:
            pass

        added = 0

        for item_id in selected:
            values = self.tree.item(item_id)["values"]

            if len(values) >= 3:
                hwid = values[2]

                try:
                    winreg.SetValueEx(ids_key, str(index), 0, winreg.REG_SZ, hwid)
                    self.blocked_devices[hwid] = True
                    index += 1
                    added += 1

                    # Update the status in the treeview
                    self.tree.set(item_id, "Status", "Blocked")
                except Exception:
                    pass

        self.refresh_policy()

        messagebox.showinfo(
            APP_TITLE,
            f"Blocked {added} device(s) from Windows Update driver installs."
        )

    def unblock_selected(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(APP_TITLE, "Select at least one device.")
            return

        _, ids_key = self.ensure_policy_keys()
        if ids_key is None:
            return

        try:
            # Get all existing values
            i = 0
            values_to_remove = []
            while True:
                try:
                    value_name, value_data, _ = winreg.EnumValue(ids_key, i)
                    values_to_remove.append((value_name, value_data))
                    i += 1
                except OSError:
                    break
        except Exception:
            messagebox.showerror(APP_TITLE, f"Failed to read policy keys.")
            return None, None

        removed = 0

        for item_id in selected:
            values = self.tree.item(item_id)["values"]
            if len(values) >= 3:
                hwid = values[2]
                if hwid in self.blocked_devices:
                    try:
                        # Remove from registry
                        for name, data in values_to_remove:
                            if data == hwid:
                                winreg.DeleteValue(ids_key, name)
                                break

                        # Remove from our tracking dictionary
                        del self.blocked_devices[hwid]

                        # Update the status in the treeview
                        self.tree.set(item_id, "Status", "Allowed")
                        removed += 1
                    except Exception:
                        pass

        self.refresh_policy()

        messagebox.showinfo(
            APP_TITLE,
            f"Unblocked {removed} device(s) from Windows Update driver installs."
        )

    def restore_all(self):
        confirm = messagebox.askyesno(
            APP_TITLE,
            "Remove all blocked driver policies?"
        )

        if not confirm:
            return

        try:
            winreg.DeleteKey(REG_BASE, REG_PATH + r"\DenyDeviceIDs")
        except:
            pass

        try:
            winreg.DeleteKey(REG_BASE, REG_PATH)
        except:
            pass

        # Clear the blocked devices dictionary
        self.blocked_devices.clear()

        # Update the treeview to show all devices as allowed
        for item_id in self.tree.get_children():
            self.tree.set(item_id, "Status", "Allowed")

        self.refresh_policy()

        messagebox.showinfo(APP_TITLE, "Policies restored.")

    def refresh_policy(self):
        self.status.set("Refreshing group policies...")

        subprocess.run(
            ["gpupdate", "/force"],
            capture_output=True
        )

        self.status.set("Policies refreshed")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        # Try to use system theme
        style = ttk.Style()
        style.theme_use("vista")  # Try to use Windows native theme
    except:
        pass  # Fall back to default theme

    app = DriverBlockerApp(root)
    root.mainloop()