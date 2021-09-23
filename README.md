# Intune-Munki-Manifest-Generator
A Python helper to generate Munki manifests for devices managed in Intune

# Description
This script is meant to help generate manifests for devices to use with Munki.
It will generate a manifest with the name of the device serial number and upload
to Azure Storage where the munki repo is.

# Configuration
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

Update the following parameters with info from your environment:
- department_1_device_ids = []
- department_2_device_ids = []
- department_1_group_id = ""
- department_2_group_id = ""
- department_1_manifest_name = ""
- department_2_manifest_name = ""
- tenantname = ""
- clientid = "" (from app registration)
- clientsecret = "" (from app registration)
- azure_connection_string = ""
- container_name = "munki" (if your private container is not named munki)
If more department groups are needed, just add more parameters and add it to the for look at the end:
- department_X_device_ids = []
- department_X_group_id = ""
- department_X_manifest_name = ""
- department_X_members = makeapirequest(group_endpoint + "/" + department_X_group_id + "/members",token)

# More info
If want to see the setup step by step, please see this blog post:
LINK
Release notes:
Version 1.0: 2021-09-24 - Original published version.
Many thanks to Shashank Mishra for many of the defs and jbaker10 for the original idea of manifest generation.
