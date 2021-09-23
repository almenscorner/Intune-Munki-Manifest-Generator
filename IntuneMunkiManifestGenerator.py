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
If more department groups are needed, just add more parameters and add it to the for loop at the end:
- department_X_device_ids = []
- department_X_group_id = ""
- department_X_manifest_name = ""
- department_X_members = makeapirequest(group_endpoint + "/" + department_X_group_id + "/members",token)
- And a for loop to add the ids
   for id in department_X_members['value']:
        deviceId = id['deviceId']
        department_X_device_ids.append(deviceId)

More info:
If want to see the setup step by step, please see this blog post:
LINK
Release notes:
Version 1.0: 2021-09-24 - Original published version.
Many thanks to Shashank Mishra for many of the defs and jbaker10 for the original idea of manifest generation.

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

#Create dicts and objects
devices = []
manifest_dict = {}

#Create department objects, set group ids and derpartment names
department_1_device_ids = []
department_2_device_ids = []
department_1_group_id = ""
department_2_group_id = ""
department_1_manifest_name = ""
department_2_manifest_name = ""

#Set Graph parameters
tenantname = ""
resource = "https://graph.microsoft.com"
endpoint = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
group_endpoint = "https://graph.microsoft.com/v1.0/groups"
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
department_1_members = makeapirequest(group_endpoint + "/" + department_1_group_id + "/members",token)
department_2_members = makeapirequest(group_endpoint + "/" + department_2_group_id + "/members",token)

for id in department_1_members['value']:
    deviceId = id['deviceId']
    department_1_device_ids.append(deviceId)

for id in department_2_members['value']:
    deviceId = id['deviceId']
    department_2_device_ids.append(deviceId)

for i in range(0, len(data['value'])):
    client_dict = {}
    client_dict['deviceName'] = data['value'][i]['deviceName']
    client_dict['serialNumber'] = data['value'][i]['serialNumber']
    client_dict['user'] = data['value'][i]['userPrincipalName']
    client_dict['id'] = data['value'][i]['azureADDeviceId']
    devices.append(client_dict)

for manifest in current_manifests:
    manifest_dict[manifest] = 1

for device in devices:
    if device['serialNumber'] in manifest_dict:
        print("Manifest already exists, skipping device " + device['serialNumber'])
    else:
        print("Creating manifest for device " + device['serialNumber'])
        manifest_template = {}
        manifest_template['catalogs'] = ['Production']
        if device['id'] in department_1_device_ids:
            print("Device found in group, adding department manifest " + department_1_manifest_name)
            manifest_template['included_manifests'] = ['site_default', department_1_manifest_name]
        elif device['id'] in department_2_device_ids:
            print("Device found in group, adding department manifest " + department_2_manifest_name)
            manifest_template['included_manifests'] = ['site_default', department_2_manifest_name]
        else:
            print("Device not found in any group, only adding included manifest site_default")
            manifest_template['included_manifests'] = ['site_default']
        manifest_template['managed_installs'] = []
        manifest_template['optional_installs'] = []
        manifest_template['display_name'] = device['deviceName']
        manifest_template['serialnumber'] = device['serialNumber']
        manifest_template['user'] = device['user']
        create_plist_blob(device['serialNumber'],connection_instance,container_name,manifest_template)
