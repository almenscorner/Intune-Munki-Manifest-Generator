# Intune Munki Manifest Generator
A Python helper to generate Munki manifests for devices managed in Intune

## Example run output
Azure Automation Output

![Screenshot 2021-09-24 at 14 26 37](https://user-images.githubusercontent.com/78877636/134675584-1ce3a8a7-4c66-4e79-bf02-6225a40fcb7d.png)

If a manifest is not found in the repository it will be skipped

![Screenshot 2021-09-24 at 14 29 22](https://user-images.githubusercontent.com/78877636/134675636-b2bed091-178e-48e5-b2ca-67970798bc6c.png)

Repository manifests

![Screenshot 2021-09-24 at 14 40 41](https://user-images.githubusercontent.com/78877636/134675777-43b52372-7e38-4b14-8b80-1630661f0c27.png)

Manifest content
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>catalogs</key>
	<array>
		<string>Production</string>
	</array>
	<key>display_name</key>
	<string>tobias’s Mac mini</string>
	<key>included_manifests</key>
	<array>
		<string>site_default</string>
		<string>Department 2</string>
	</array>
	<key>managed_installs</key>
	<array/>
	<key>optional_installs</key>
	<array/>
	<key>serialnumber</key>
	<string>C07XXXXXXXXX</string>
	<key>user</key>
	<string>almen@almens365.onmicrosoft.com</string>
</dict>
</plist>
```

## Description
This script is meant to help generate manifests for devices to use with Munki.
It will generate a manifest with the name of the device serial number and upload
to Azure Storage where the munki repo is.

## Configuration
I set this up to be run from an Azure Automation Account on a schedule, to do that
you have to import the following Python 3 packages:
- azure_core
- azure_storage_blob
- msrest

To call the Graph API and get data, create an Azure AD App Registration with the
follwing app permissions granted:
- DeviceManagementConfiguration.Read.All
- DeviceManagementManagedDevices.Read.All
- DeviceManagementServiceConfig.Read.All
- Directory.Read.All
- Group.Read.All
- GroupMember.Read.All

You also have to generate a connection string for your storage account.

Required parameters to update are the following, add info from your environment:
- tenantname = ""
- clientid = "" (from app registration)
- clientsecret = "" (from app registration)
- azure_connection_string = ""
- container_name = "munki" (if your private container is not named munki)

If you have "department" manifests in munki, you can add the Azure AD group ID and
manifest name of those in the dictionary below, if left blank only "site_default" will be added.
To include additional "departments", just add them to the dictionary with the same format.
```python
department_groups = {
    "Department1": {
        "id": "",
        "name": ""
    },
    "Department2": {
        "id": "",
        "name":""
    }
}
```

## More info
If want to see the setup step by step, please see this blog post:
https://almenscorner.io/munki-what-about-manifests/

Release notes:
Version 1.1: 2021-09-28 - The script now checks if included manifests are missing for already created device manifests and adds them.
Version 1.0: 2021-09-24 - Original published version.

Many thanks to journeyofthegeek.com and Shashank Mishra for many of the defs and jbaker10 for the original idea of manifest generation.
