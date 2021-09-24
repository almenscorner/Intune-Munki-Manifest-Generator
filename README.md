# Intune Munki Manifest Generator
A Python helper to generate Munki manifests for devices managed in Intune

## Example run output
Azure Automation Output

![Screenshot 2021-09-23 at 17 04 56](https://user-images.githubusercontent.com/78877636/134533249-a173d2f1-1723-400d-853c-1eef556f75e8.png)

Repository manifests

![Screenshot 2021-09-23 at 17 10 59](https://user-images.githubusercontent.com/78877636/134534149-76b1df1d-fd68-4724-b2e2-98ae8a881079.png)

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
LINK

Release notes:
Version 1.0: 2021-09-24 - Original published version.

Many thanks to journeyofthegeek.com and Shashank Mishra for many of the defs and jbaker10 for the original idea of manifest generation.
