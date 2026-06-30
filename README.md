# Windows-Drivers-Update-Blocker

A lightweight Windows utility that allows you to block specific device drivers from being automatically reinstalled or updated through Windows Update.

## Features

* Scan installed devices directly from Windows.
* Display device names, classes and Hardware IDs.
* Filter devices by hardware class for easier navigation.
* Block selected devices from receiving driver updates through Windows Update.
* Unblock selected devices at any time.
* Restore all blocked devices with a single click.
* Refresh Group Policy automatically after changes.
* Displays the current status of each device (`Allowed` or `Blocked`).
* Portable application with no installation required.
* Automatically requests Administrator privileges on startup.

## Why use it?

Windows Update occasionally installs newer or generic drivers that may:

* Reduce hardware performance.
* Introduce compatibility problems.
* Remove manufacturer-specific features.
* Reinstall drivers that were intentionally removed.
* Replace stable drivers with problematic versions.

Windows-Drivers-Update-Blocker allows you to keep control over which device drivers Windows Update is allowed to manage.

## Usage

1. Run the application as Administrator.
2. Click **Scan Devices**.

   > Note: The app may appear to pause or temporarily freeze during scanning. This is normal—please allow a short moment while it reads system devices.

3. Optionally filter devices by type.
4. Select one or more devices from the list.
5. Click **Block Selected** to prevent future Windows Update driver installations.
6. Use **Unblock Selected** to remove restrictions for selected devices.
7. Use **Restore All** to return all settings to default state.

## Compatibility

* Windows 10
* Windows 11
* Home Edition
* Pro Edition
* Enterprise Edition
* LTSC Editions

## Disclaimer

This application modifies Windows Device Installation policies in order to control automatic driver installation behavior.

The tool does not uninstall drivers, modify driver files, or prevent users from manually installing drivers if administrative privileges are available.

Always ensure you have access to a working driver package before blocking updates for critical hardware devices.

## License

Free for personal and educational use.
