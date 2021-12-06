#!/usr/bin/env python3

"""
Author: Tobias Almén (almenscorner.io)
Script: IntuneMunkiManifestGenerator.py
Description:
This script is meant to help generate manifests for devices to use with Munki.
It will generate a manifest with the name of the device serial number and upload
to Azure Storage where the munki repo is.
Configuration:
I set this up to be run from an Azure Automation Account on a schedule, to do that
you have to import the following Python 3 packages:
- azure_core
- azure_storage_blob
- msrest
To call the Graph API and get data, create an Azure AD App Registration with the follwing app permissions granted:
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
If you have "department" manifests in munki, you can add the Azure AD group ID and manifest name of those in the dictionary below, 
if left blank only "site_default" will be added. To include additional "departments", just add them to the dictionary with the same format.
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
More info:
If want to see the setup step by step, please see this blog post:
https://almenscorner.io/munki-what-about-manifests/
Release notes:
Version 1.3: 2021-12-06 - Added check for null AAD device ID, removal of department manifest if device is no longer in group and
removal of manifest if device is no longer in Intune. If you want to do this, un-comment line 300. Run one time first and check output 
to make sure manifests that should not be deleted are touched.
Version 1.2: 2021-10-04 - Improvements in department group handling and clearer output per device.
Version 1.1: 2021-09-28 - The script now checks if included manifests are missing for already created device manifests and adds them.
Version 1.0: 2021-09-24 - Original published version.
Many thanks to journeyofthegeek.com and Shashank Mishra for many of the defs and jbaker10 for the original idea of manifest generation.
The script is provided "AS IS" with no warranties.
"""

import json
import requests
import os
import msrest
import plistlib

from adal import AuthenticationContext
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

## Use Microsoft ADAL module to obtain a bearer token for access to Azure AD and
## create a header to pass in a request

def obtain_accesstoken(tenantname,clientid,clientsecret,resource):
    auth_context = AuthenticationContext('https://login.microsoftonline.com/' +
        tenantname)
    token = auth_context.acquire_token_with_client_credentials(
        resource=resource,client_id=clientid,
        client_secret=clientsecret)
    return token

## Create a valid header using a provided access token and make a request
## of the MS Graph API

def makeapirequest(endpoint,token,q_param=None):
    ## Create a valid header using the provided access token
    ##
        
    headers = {'Content-Type':'application/json', \
    'Authorization':'Bearer {0}'.format(token['accessToken'])}
           
    ## This section handles a bug with the Python requests module which
    ## encodes blank spaces to plus signs instead of %20.  This will cause
    ## issues with OData filters
    
    if q_param != None:
        response = requests.get(endpoint,headers=headers,params=q_param)
    else:
        response = requests.get(endpoint,headers=headers)
    if response.status_code == 200:
        json_data = json.loads(response.text)
            
        ## This section handles paged results and combines the results 
        ## into a single JSON response.  This may need to be modified
        ## if results are too large

        if '@odata.nextLink' in json_data.keys():
            record = makeapirequest(json_data['@odata.nextLink'],token)
            entries = len(record['value'])
            count = 0
            while count < entries:
                json_data['value'].append(record['value'][count])
                count += 1
        return(json_data)
    else:
        raise Exception('Request failed with ',response.status_code,' - ',
            response.text)

#Connect to Azure Storage

def azure_connect_conn_string(source_container_connection_string, source_container_name):
    try:
        blob_source_service_client = BlobServiceClient.from_connection_string(source_container_connection_string)
        source_container_client = blob_source_service_client.get_container_client(source_container_name)
        return source_container_client

    except Exception as ex:
        print ("Error: " + str(ex))

#Get all blobs in specified container
current_manifests = []
def container_content_list(connection_instance, blob_path):
    try:
        source_blob_list = connection_instance.list_blobs(name_starts_with=blob_path)
        for blob in source_blob_list:
            blob_name = blob.name.rsplit('/',1)[1]
            current_manifests.append(blob_name)

    except Exception as ex:
        print ("Error: " + str(ex))

#Create plist for device and upload to azure blob

def create_plist_blob(local_file_name,connection_instance,container_name,manifest_template):
    try:
        local_path = "./"
        upload_file_path = os.path.join(local_path, local_file_name)
        with open(upload_file_path, 'wb') as _f:
            plistlib.dump(manifest_template, _f)
        blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name + "/manifests", blob=local_file_name)
        with open(upload_file_path, "rb") as data:
            blob_client.upload_blob(data)
        os.remove(upload_file_path)

    except Exception as ex:
        print ("Error: " + str(ex))

#Get groups the device is a member of

def get_device_memberOf(azureADDeviceId):
    aad_device_objId = None
    q_param_device = {"$filter":"deviceId eq " + "'" + azureADDeviceId + "'"}
    device_object = makeapirequest(device_group_endpoint,token,q_param_device)
    for id in device_object['value']:
        objId = id['id']
        aad_device_objId = objId
    q_param_group= {"$select":"id,displayName"}
    if aad_device_objId is None:
        print("AAD Device ID is null, skipping device group memberships")
    else:
        memberOf = makeapirequest(device_group_endpoint + "/" + aad_device_objId + "/memberOf",token,q_param_group)
        device_groups = []
        device_groups_name = []
        for group_id in memberOf['value']:
            id = group_id['id']
            device_groups.append(id)
            device_groups_name.append(group_id['displayName'])
        for k in department_groups.keys():
            values = department_groups.get(k)
            if values['id'] in device_groups:
                if values['name'] in manifest_dict:
                    print("Device found in group for " + values['name'] + ", adding included manifest for department")
                    device['manifest_list'].append(values['name'])
                else:
                    print("Device found in group for " + (values['name']) + " but manifest does not exist, skipping")
        return device_groups_name

#Check if device is missing included manifests and add them if any are missing

def update_plist_blob(remote_file_name,connection_instance,container_name,manifest_template,device,member_of):
    try:
        local_path = "./"
        download_file_path = os.path.join(local_path, remote_file_name)
        blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name + "/manifests", blob=remote_file_name)
        with open(download_file_path, "wb") as _f:
            blob_data = blob_client.download_blob()
            data = blob_data.readall()
            plist_data = plistlib.loads(data)
            add_manifests=[]
            remove_manifests=[]
            for manifest in device['manifest_list']:
                if manifest not in plist_data['included_manifests']:
                    add_manifests.append(manifest)
                if manifest not in manifest_dict:
                    print("Manifest " + manifest + " not found, skipping")
                    device['manifest_list'].remove(manifest)
                    add_manifests.remove(manifest)
            for group_manifest in plist_data['included_manifests']:
                if ((group_manifest not in member_of) and (group_manifest != "site_default")):
                    remove_manifests.append(group_manifest)
            if remove_manifests:
                for manifest in remove_manifests:
                    plist_data['included_manifests'].remove(manifest)
                    device['manifest_list'] = plist_data['included_manifests']
            plistlib.dump(manifest_template, _f)

        if add_manifests:
            print("Missing included manifests found adding them...")         
            with open(download_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            os.remove(download_file_path)
        if remove_manifests:
            print("Device is no longer part of " + manifest + ", removing included manifest")         
            with open(download_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            os.remove(download_file_path)

    except Exception as ex:
        print ("Error: " + str(ex))

#Delete manifest

def delete_blob(remote_file_name,container_name):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name + "/manifests", blob=remote_file_name)
        blob_client.delete_blob()
    except Exception as ex:
        print ("Error: " + str(ex))

#Create dicts and objects
devices = []
serials = []
manifest_dict = {}
catalogs = ["Production"]
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

#Set Graph parameters
tenantname = ""
resource = "https://graph.microsoft.com"
endpoint = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
group_endpoint = "https://graph.microsoft.com/v1.0/groups"
device_group_endpoint = "https://graph.microsoft.com/v1.0/devices"
clientid = ""
clientsecret = ""
q_param = {"$filter":"operatingSystem eq 'macOS'"}

#Set Azure Storage parameters
azure_connection_string = ""
container_name = "munki"
blob_path = "manifests/"

#Connect to Azure Storage and get blobs
connection_instance = azure_connect_conn_string(azure_connection_string, container_name)
container_content_list(connection_instance, blob_path)

#Connect to Graph and get devices and group members
token = obtain_accesstoken(tenantname,clientid,clientsecret,resource)
data = makeapirequest(endpoint,token,q_param)

for i in range(0, len(data['value'])):
    manifest_list = ["site_default"]
    client_dict = {}
    client_dict['deviceName'] = data['value'][i]['deviceName']
    client_dict['serialNumber'] = data['value'][i]['serialNumber']
    client_dict['user'] = data['value'][i]['userPrincipalName']
    client_dict['id'] = data['value'][i]['azureADDeviceId']
    client_dict['manifest_list'] = manifest_list
    devices.append(client_dict)

for manifest in current_manifests:
    manifest_dict[manifest] = 1

for sn in devices:
    serials.append(sn['serialNumber'])

#If manifest is not in device serials or department groups and is not site_default, remove manifest
for manifest in manifest_dict:
    groups = []
    for k in department_groups.keys():
        values = department_groups.get(k)
        groups.append(values['name'])
    if ((manifest not in serials) and (manifest not in groups) and (manifest != "site_default")):
        print('Device ' + manifest + ' not found, deleting device manifest')
        #delete_blob(manifest,container_name)

for device in devices:
    if device['serialNumber'] in manifest_dict:
        print("-" * 42 + device['serialNumber'] +  "-" * 42)
        member_of = get_device_memberOf(device['id'])
        manifest_template = {}
        manifest_template['catalogs'] = catalogs
        for name in device['manifest_list']:
            if name not in manifest_dict:
                print("Manifest " + name + " not found, skipping")
                device['manifest_list'].remove(name)
        manifest_template['included_manifests'] = device['manifest_list']
        manifest_template['managed_installs'] = []
        manifest_template['optional_installs'] = []
        manifest_template['display_name'] = device['deviceName']
        manifest_template['serialnumber'] = device['serialNumber']
        manifest_template['user'] = device['user']
        print("Manifest already exists, skipping manifest creation")
        update_plist_blob(device['serialNumber'],connection_instance,container_name,manifest_template,device,member_of)
        print("-" * 96)
    else:
        print("-" * 42 + device['serialNumber'] +  "-" * 42)
        get_device_memberOf(device['id'])
        print("Creating manifest for device")
        manifest_template = {}
        manifest_template['catalogs'] = catalogs
        for name in device['manifest_list']:
            if name not in manifest_dict:
                print("Manifest " + name + " not found, skipping")
                device['manifest_list'].remove(name)
        print("adding following included manifests:")
        for manifest in device['manifest_list']:
            print(manifest)
        manifest_template['included_manifests'] = device['manifest_list']
        manifest_template['managed_installs'] = []
        manifest_template['optional_installs'] = []
        manifest_template['display_name'] = device['deviceName']
        manifest_template['serialnumber'] = device['serialNumber']
        manifest_template['user'] = device['user']
        create_plist_blob(device['serialNumber'],connection_instance,container_name,manifest_template)
        print("-" * 96)
