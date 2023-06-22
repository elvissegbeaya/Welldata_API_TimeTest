#!/usr/bin/python3
#
# welldataAPI.python
#
# Library of WellData Data API functions
from __future__ import annotations

# Copyright (c) 2020 National Oilwell Varco
# All rights reserved
#
# When installing in a new system:
# - apt-get/yum install python36
# - pip3 install --user python-dateutil
# - pip3 install --user requests
# - pip3 install --user python-dateutil
# - pip3 install --user numpy
# - pip3 install --user pyopenssl ndg-httpsclient pyasn1
#

import json
import logging
import os
import os.path
import time
from datetime import datetime
import requests
import sseclient
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from requests.auth import HTTPBasicAuth
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import List, Optional

def storageConfig():
    return {
        'SectionName': 'storage',
        'Parameters': [
            {'type': {'value': '', 'type': 'string', 'default': 'postgresql', 'description': 'Storage DB engine'}},
            {'server': {'value': '', 'type': 'string', 'default': '', 'description': 'DB Host'}},
            {'port': {'value': '', 'type': 'string', 'default': '', 'description': 'DB TCP Port'}},
            {'username': {'value': '', 'type': 'string', 'default': '', 'description': 'DB Username'}},
            {'password': {'value': '', 'type': 'string', 'default': '', 'description': 'DB Password'}},
            {'runMode': {'value': '', 'type': 'string', 'default': '', 'description': 'Debug Flag'}},
        ]
    }

def serverConfig(ServerName='welldata net'):
    return {
        'SectionName': ServerName,
        'Parameters': [
            {'APIUrl': {'value': '', 'type': 'string', 'default': 'https://data.welldata.net/api/v1',
                        'description': 'https://data.welldata.net/api/v1'}},
            {'appID': {'value': '', 'type': 'string', 'default': '',
                       'description': 'App ID provided by WellData Engineering: i.e.: 17147920-2DFB-4E95-B3AB-67ED69D1E02D'}},
            {'username': {'value': '', 'type': 'string', 'default': '', 'description': 'WellData Username'}},
            {'password': {'value': '', 'type': 'string', 'default': '', 'description': 'WellData Password'}}

        ]
    }

def defaultConfig():
    # 20220307 v1.2 RRM Added default for Contractor name
    return {
        'SectionName': 'WellDataDownload',
        'Parameters': [
            # { 'APIUrl':           { 'value': '', 'type': 'string', 'default': 'https://data.welldata.net/api/v1', 'description': 'https://data.welldata.net/api/v1'                                                                                                    } },
            # { 'appID':            { 'value': '', 'type': 'string', 'default': '',                         'description': 'App ID provided by WellData Engineering: i.e.: 17147920-2DFB-4E95-B3AB-67ED69D1E02D'                                         } },
            # { 'username':         { 'value': '', 'type': 'string', 'default': '',                         'description': 'WellData Username'                                                                                                           } },
            # { 'password':         { 'value': '', 'type': 'string', 'default': '',                         'description': 'WellData Password'                                                                                                           } },
            {'ContractorName': {'value': '', 'type': 'string', 'default': '',
                                'description': 'If the Contractor string is empty, all wells are retrieved'}},
            {'OperatorName': {'value': '', 'type': 'string', 'default': '',
                              'description': 'If the Operator string is empty, all wells are retrieved'}},
            # updating to Jobstatus { 'WellStatus':       { 'value': '', 'type': 'string', 'default': 'ActiveOnly',               'description': 'Well Status Filter: All / ActiveOnly'                                                                                        } },
            {'JobStatus': {'value': '', 'type': 'string', 'default': 'ActiveJobs',
                           'description': 'Job Status Filter: AllJobs / ActiveJobs / EndedJobs'}},
            {'FromHours': {'value': '', 'type': 'int', 'default': '0',
                          'description': 'Time Step in seconds. Set to zero for no time log download'}},
            {'ToHours': {'value': '', 'type': 'int', 'default': '0',
                           'description': 'Time Step in seconds. Set to zero for no time log download'}},
            {'CurrentFrequency': {'value': '', 'type': 'int', 'default': '0',
                           'description': 'Time Step in seconds. Set to zero for no time log download'}},
            {'HistoricInterval': {'value': '', 'type': 'int', 'default': '0',
                         'description': 'Time Step in seconds. Set to zero for no time log download'}},
            {'CurrentInterval': {'value': '', 'type': 'int', 'default': '0',
                           'description': 'Time Step in seconds. Set to zero for no time log download'}},
            {'FilterList': {'value': '', 'type': 'list', 'default': '',
                           'description': "List of attributes to filter by.\n\t Leave empty for no filter"}},

            {'ChannelsToOutput': {'value': '', 'type': 'list', 'default': '',
                                  'description': "List of channels to output,\n\tone\n\tper\n\tline.\n\tLeave empty for all channels"}},
        ]
    }

    #######################################################################
    #######################################################################
    # Connecting the API Modules to retrieve data from WellData
    #######################################################################
    #######################################################################

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever

class FilterValue(BaseModel):
    value: int


class FilterRange(BaseModel):
    from_: str
    to: str


class FilterIn(BaseModel):
    values: List[int]


class FilterBetween(BaseModel):
    range: FilterRange


class Filter(BaseModel):
    attributeId: str
    isIn: Optional[FilterIn]
    equals: Optional[FilterValue]
    greaterThan: Optional[FilterValue]
    greaterThanEqual: Optional[FilterValue]
    lessThan: Optional[FilterValue]
    lessThanEqual: Optional[FilterValue]
    hasData: Optional[dict]
    between: Optional[FilterBetween]
    isNull: Optional[dict]



class TimeRange(BaseModel):
    from_: datetime
    to: datetime





class EventTimeRequest(BaseModel):
    outputAttributes: list
    timeRange: TimeRange
    filter: Filter




@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
class HistoricalTimeRequest(BaseModel):
    attributes: list
    fromTime: datetime
    toTime: datetime
    interval: float
    isDifferential: bool = False

class CurrentTimeRequest(BaseModel):
    attributes: list
    frequency: float
    interval: float
    isDifferential: bool = False




# @retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def historical_data_time(job_id: str, payload: HistoricalTimeRequest, token: any):
    """
    args
        job
        payload
    """
    uri = f'https://data.welldata.net/api/v1/jobs/{job_id}/data/time'
    header= {'token': token}
    r = requests.post(uri, data=payload, headers=header)
    print(r.status_code)
    return r.json()

def current_data_time(job_id: str, payload: CurrentTimeRequest, token: any):
    """
    args
        job
        payload
    """
    uri = f'https://data.welldata.net/api/v1/jobs/{job_id}/data/time/current'
    header= {'token': token}
    r = requests.post(uri, data=payload, headers=header)
    print(r.status_code)
    return r.json()

def event_data_time(job_id: str, payload: EventTimeRequest, token: any):
    """
    args
        job
        payload
    """
    uri = f'https://data.welldata.net/api/v1/jobs/{job_id}/data/time/events'
    header= {'token': token}
    r = requests.post(uri, data=payload, headers=header)
    print(r.status_code)
    return r.json()








#API Calls

@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def getToken(URL, appID, username, password, processNumber=""):
    headers = {'ApplicationID': appID, 'accept': 'application/json'}
    params = {}

    # print (headers)
    logging.debug("{} Getting Auth Token from {}".format(processNumber, URL))
    r = requests.get(URL + '/tokens/token?', params=params, headers=headers, auth=HTTPBasicAuth(username, password))
    # TODO: Refactor and use the right URLs when you get a chance -> we want to be able to access URLs['getToken]
    # r = requests.get(URLs['getToken'], params=params, headers=headers, auth=HTTPBasicAuth(username, password))
    if r.status_code != 200:
        logging.error("Error code " + str(r.status_code))
        logging.error("Error code " + str(r.reason))
        os._exit(1)

    # print (r.text)
    # print (r.status_code)
    values = r.json()

    # E- fixed, need to return token lowercase per swagger
    return values['token']

@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def getApiCall(URL, token, CFG, jobId=""):
    # Variables:
    wells = []  # will return number of wells
    r = None
    params = {}
    parsedPath = URL
    retries = 0
    headers = {'Token': token, 'accept': 'application/json'}

    # parsing path
    parsedPath = URL.replace('<jobId>', str(jobId))

    # Checking updated URL
    print(parsedPath)

    # trying to make a connection
    try:
        r = requests.get(parsedPath, params=params, headers=headers)
        print(r)
        if r.status_code == 200:
            successfulRequest = True  # this means we got the data
            values = r.json()
            wells.append(values)

        elif r.status_code != 200 and r.status_code == range(500, 599, 1) or 400:  # bad request:
            # server error, wait and try again
            # take a break for 4 second
            time.sleep(20)
            try:
                r = requests.get(parsedPath, params=params, headers=headers)
                print(r)
                if r.status_code == 200:
                    successfulRequest = True  # this means we got the data
                    values = r.json()
                    wells.append(values)

            except Exception as ex:
                logging.error("Error sending request to server")
                logging.error("Query {}".format(parsedPath))
                logging.error("Parameters {}".format(params))
                logging.error("Headers {}".format(headers))
                logging.error("Response {}".format(r))
                retries = retries + 1
                logging.error("Sleeping for {} seconds".format(retries))

    except Exception as ex:
        logging.error("Error sending request to server")
        logging.error("Query {}".format(parsedPath))
        logging.error("Parameters {}".format(params))
        logging.error("Headers {}".format(headers))
        logging.error("Response {}".format(r))
        retries = retries + 1
        logging.error("Sleeping for {} seconds".format(retries))
        time.sleep(retries)
    return wells

    # Done: only thing missing is AttributeUnits field from swagger

@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def postApiCall(URL, token, CFG, jobId="", data=""):
    # Variables:
    wells = []  # will return number of wells
    params = {}
    r = None
    retries = 0

    # updating the url path
    parsedPath = URL.replace('<jobId>', jobId)
    headers = {'Token': token, 'accept': 'application/json'}

    print(f'This is the parse path: {parsedPath}')
    # trying to make a connection
    try:
        r = requests.post(parsedPath, data=data, headers=headers)
        print(r)
        if r.status_code == 200:

            values = r.json()
            wells.append(values)


        # implement the take and skip functional
        elif r.status_code != 200 and (r.status_code == range(500, 599, 1) or range(400, 410, 1)):  # bad request:
            # server error, wait and try again
            # take a break for 4 second
            time.sleep(20)
            try:
                r = requests.post(parsedPath, data=data, headers=headers)
                print(r)
                if r.status_code == 200:
                    successfulRequest = True  # this means we got the data
                    values = r.json()
                    wells.append(values)

            except Exception as ex:
                logging.error("Error sending request to server")
                logging.error("Query {}".format(parsedPath))
                logging.error("Parameters {}".format(params))
                logging.error("Headers {}".format(headers))
                logging.error("Response {}".format(r))
                retries = retries + 1
                logging.error("Sleeping for {} seconds".format(retries))

    except Exception as ex:
        logging.error("Error sending request to server")
        logging.error("Query {}".format(parsedPath))
        logging.error("Parameters {}".format(params))
        logging.error("Headers {}".format(headers))
        logging.error("Response {}".format(r))
        retries = retries + 1
        logging.error("Sleeping for {} seconds".format(retries))
        time.sleep(retries)

    return wells

    # Done: only thing missing is AttributeUnits field from swagger






@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def getJobs(URL, token, CFG, **kwargs):  # take = 1, skip =0, totalCount = True ,

    # Variables:

    broadcastTimeTo = ""
    broadcastTimeFrom = ""

    Total = True
    totalCheck = False
    wells = []  # will return number of wells
    attrBool = False  # checks to see if attributes taken
    params = {}
    r = None
    currTake = 1
    retries = 0
    successfulRequest = False
    # jobId = "",jobStatus = "ActiveJobs", startDateMin = "", startDateMax = "", endDateMin = "", endDateMax = "", capabilities = False, attributeUnits = "", rigNumber = "", contractor = ""
    jobId = kwargs.get('jobId')
    jobStatus = 'ActiveJobs'
    startDateMin = kwargs.get('startDateMin')  # 2021-07-06 5:13:48 PM
    startDateMax = kwargs.get('startDateMax')  # startDateMin=2021-07-06%205%3A13%3A48%20PM   -> URL Format
    endDateMin = kwargs.get('endDateMin')
    endDateMax = kwargs.get('endDateMax')
    Capabilities = False
    rigNumber = kwargs.get('rigNumber')
    contractor = kwargs.get('contractor')
    operator = kwargs.get('operator')
    take = 1
    skip = 0
    sort = 'id'
    sortOrder = 'asc'
    totalbool = False
    parsedPath = URL
    if kwargs.get('total') is not None:
        totalbool = kwargs.get('total')
    if kwargs.get('skip') is not None:
        skip = kwargs.get('skip')
    if kwargs.get('take') is not None:
        take = kwargs.get('take')
    if kwargs.get('sort') is not None:
        sort = kwargs.get('sort')
    if kwargs.get('sortOrder') is not None:
        sortOrder = kwargs.get('sortOrder')
    if kwargs.get('Capabilities') is not None:
        Capabilities = kwargs.get('Capabilities')
    if kwargs.get('jobStatus') is not None:
        jobStatus = kwargs.get('jobStatus')

    ############################################
    # handling additional constructor arguments
    ############################################

    headers = {'Token': token, 'accept': 'application/json'}

    if jobId is not None:
        parsedPath = URL.replace('jobId', str(jobId))
        parsedPath = parsedPath.replace('(\'', '')
        parsedPath = parsedPath.replace('\',)', '')
    if Capabilities is not None and jobId is None:
        parsedPath = parsedPath.replace('capabilities', f'capabilities={Capabilities}')
        parsedPath = parsedPath.replace('(\'', '')
        parsedPath = parsedPath.replace('\',)', '')

    # Checking updated URL
    print(parsedPath)

    # all but GetJob
    if 'includeCapabilities' not in parsedPath or (jobId is not None and 'includeCapabilities' not in parsedPath):
        # trying to make a connection
        try:
            r = requests.get(parsedPath, params=params, headers=headers)
            print(r)
            if r.status_code == 200:
                successfulRequest = True  # this means we got the data
                values = r.json()
                # wells.append(values)
                # jobid,well name,  contractor, rignumber,startDate, endDate, firstDataDate, lastDataDate
                wells.append(values['id'])
                wells.append(values['name'])
                wells.append(values['assetInfoList'][0]['owner'])
                wells.append(values['assetInfoList'][0]['name'])
                wells.append(values['startDate'])
                wells.append(values['firstDataDate'])
                wells.append(values['lastDataDate'])
                wells.append(values['jobNumber'])


            # implement the take and skip functional
            elif r.status_code != 200 and (r.status_code == range(500, 599, 1) or range(400, 410, 1)):  # bad request:
                # server error, wait and try again
                # take a break for 4 second
                time.sleep(20)
                try:
                    r = requests.get(parsedPath, params=params, headers=headers)
                    print(r)
                    if r.status_code == 200:
                        successfulRequest = True  # this means we got the data
                        values = r.json()
                        # wells.append(values)
                        # jobid,well name,  contractor, rignumber,
                        wells.append(values['id'])
                        wells.append(values['name'])
                        wells.append(values['assetInfoList'][0]['owner'])
                        wells.append(values['assetInfoList'][0]['name'])
                        wells.append(values['startDate'])
                        wells.append(values['firstDataDate'])
                        wells.append(values['lastDataDate'])
                        wells.append(values['jobNumber'])

                except Exception as ex:
                    logging.error("Error sending request to server")
                    logging.error("Query {}".format(parsedPath))
                    logging.error("Parameters {}".format(params))
                    logging.error("Headers {}".format(headers))
                    logging.error("Response {}".format(r))
                    retries = retries + 1
                    logging.error("Sleeping for {} seconds".format(retries))

        except Exception as ex:
            logging.error("Error sending request to server")
            logging.error("Query {}".format(parsedPath))
            logging.error("Parameters {}".format(params))
            logging.error("Headers {}".format(headers))
            logging.error("Response {}".format(r))
            retries = retries + 1
            logging.error("Sleeping for {} seconds".format(retries))
            time.sleep(retries)

        return wells
    # for Get Jobs including take and skips
    else:
        parsedPath = URL.replace('<jobStatus>', jobStatus)
        parsedPath = parsedPath.replace('<take>', str(take))
        parsedPath = parsedPath.replace('<skip>', str(skip))
        parsedPath = parsedPath.replace('<sort>', str(sort))
        parsedPath = parsedPath.replace('<sortOrder>', str(sortOrder))
        parsedPath = parsedPath.replace('<includeCapabilities>', str(Capabilities))
        parsedPath = parsedPath.replace('<total>', str(totalbool))

        if startDateMin is not None:
            # converting DateString into parsepath version:   2021-07-06%205%3A13%3A48%20PM  2021-07-06 5:13:48 PM
            dateString = f'{startDateMin[0:10]}%20{startDateMin[11:13]}%3A{startDateMin[14:16]}%3A{startDateMin[17:19]}%20{startDateMin[20:22]}'
            parsedPath = parsedPath.replace('<startDateMin>', str(dateString))
        else:
            parsedPath = parsedPath.replace('&startDateMin=<startDateMin>', '')
        if startDateMax is not None:
            dateString = f'{startDateMax[0:10]}%20{startDateMax[11:13]}%3A{startDateMax[14:16]}%3A{startDateMax[17:19]}%20{startDateMax[20:22]}'
            parsedPath = parsedPath.replace('<startDateMax>', str(dateString))
        else:
            parsedPath = parsedPath.replace('&startDateMax=<startDateMax>', '')
        if endDateMin is not None:
            dateString = f'{endDateMin[0:10]}%20{endDateMin[11:13]}%3A{endDateMin[14:16]}%3A{endDateMin[17:19]}%20{endDateMin[20:22]}'
            parsedPath = parsedPath.replace('<endDateMin>', str(dateString))
        else:
            parsedPath = parsedPath.replace('&endDateMin=<endDateMin>', '')
        if endDateMax is not None:
            dateString = f'{endDateMax[0:10]}%20{endDateMax[11:13]}%3A{endDateMax[14:16]}%3A{endDateMax[17:19]}%20{endDateMax[20:22]}'
            parsedPath = parsedPath.replace('<endDateMax>', str(dateString))
        else:
            parsedPath = parsedPath.replace('&endDateMax=<endDateMax>', '')

        # Checking updated URL
        print(parsedPath)

        while currTake <= take:
            # trying to make a connection
            try:
                r = requests.get(parsedPath, params=params, headers=headers)
                print(r)
                if r.status_code == 200:
                    successfulRequest = True  # this means we got the data
                    values = r.json()
                    if totalbool is True and totalCheck is False:
                        wells.append(values['total'])
                        totalCheck = True
                    for w in values['jobs']:
                        if contractor is not None or operator is not None:
                            # only append if it meets contractor
                            if contractor is not None and operator is not None:
                                wells.append(w)
                            elif contractor is not None and operator is None:
                                if w['assetInfoList'][0]['owner'] == contractor:
                                    wells.append(w)
                            else:  # contractor is  None and operator is not None:
                                if w['siteInfoList'][0]['owner'] == operator:
                                    wells.append(w)
                        elif rigNumber is not None:
                            if w['assetInfoList'][0]['name'] == rigNumber:
                                wells.append(w)
                        else:
                            wells.append(w)


                # implement the take and skip functional
                elif r.status_code != 200 and r.status_code == range(500, 599, 1) or 400:  # bad request:
                    # server error, wait and try again
                    # take a break for 4 second
                    time.sleep(20)
                    try:
                        r = requests.get(parsedPath, params=params, headers=headers)
                        print(r)
                        if r.status_code == 200:
                            values = r.json()
                            if totalbool == True:
                                wells.append(values['total'])
                            for w in values['jobs']:
                                if contractor is not None or operator is not None:
                                    # only append if it meets contractor
                                    if contractor is not None and operator is not None:
                                        wells.append(w)
                                    elif contractor is not None and operator is None:
                                        if w['assetInfoList'][0]['owner'] == contractor:
                                            wells.append(w)
                                    else:  # contractor is  None and operator is not None:
                                        if w['siteInfoList'][0]['owner'] == operator:
                                            wells.append(w)
                                elif rigNumber is not None:
                                    if w['assetInfoList'][0]['name'] == rigNumber:
                                        wells.append(w)
                                else:
                                    wells.append(w)

                    except Exception as ex:
                        logging.error("Error sending request to server")
                        logging.error("Query {}".format(parsedPath))
                        logging.error("Parameters {}".format(params))
                        logging.error("Headers {}".format(headers))
                        logging.error("Response {}".format(r))
                        retries = retries + 1
                        logging.error("Sleeping for {} seconds".format(retries))

            except Exception as ex:
                logging.error("Error sending request to server")
                logging.error("Query {}".format(parsedPath))
                logging.error("Parameters {}".format(params))
                logging.error("Headers {}".format(headers))
                logging.error("Response {}".format(r))
                retries = retries + 1
                logging.error("Sleeping for {} seconds".format(retries))
                time.sleep(retries)

            #         #got this far the connection is made and we have the value in r, get the values of job
            skip = skip + currTake
            currTake = currTake + take
        # #gets additional record beyond take
        #     if take > totalcount:
        #         take = totalcount-1
        #     elif currTake + take >= totalcount:
        #         take = totalcount - take - 1

        return wells

    #######################################################################
    #######################################################################
    # Customisable API Calls below per specific requests
    #######################################################################
    #######################################################################

@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def postTimeBased(URL, token, CFG, data="", jobId=""):
    # Variables:
    wells = []  # will return number of wells
    params = {}
    r = None
    retries = 0

    # updating the url path
    parsedPath = URL.replace('<jobId>', jobId)
    headers = {'Token': token, 'accept': 'application/json'}

    print(f'This is the parse path: {parsedPath}')
    # trying to make a connection
    try:
        r = requests.post(parsedPath, data=data, headers=headers)
        print(r)
        if r.status_code == 200:

            values = r.json()
            wells.append(values)


        # implement the take and skip functional
        elif r.status_code != 200 and (r.status_code == range(500, 599, 1) or range(400, 410, 1)):  # bad request:
            # server error, wait and try again
            # take a break for 4 second
            time.sleep(20)
            try:
                r = requests.post(parsedPath, data=data, headers=headers)
                print(r)
                if r.status_code == 200:
                    successfulRequest = True  # this means we got the data
                    values = r.json()
                    wells.append(values)

            except Exception as ex:
                logging.error("Error sending request to server")
                logging.error("Query {}".format(parsedPath))
                logging.error("Parameters {}".format(params))
                logging.error("Headers {}".format(headers))
                logging.error("Response {}".format(r))
                retries = retries + 1
                logging.error("Sleeping for {} seconds".format(retries))

    except Exception as ex:
        logging.error("Error sending request to server")
        logging.error("Query {}".format(parsedPath))
        logging.error("Parameters {}".format(params))
        logging.error("Headers {}".format(headers))
        logging.error("Response {}".format(r))
        retries = retries + 1
        logging.error("Sleeping for {} seconds".format(retries))
        time.sleep(retries)

    return wells

@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def postEvents(URL, token, CFG, data="", jobId=""):
    # Variables:

    wells = []  # will return number of wells
    params = {}
    r = None
    retries = 0
    # updating the url path
    parsedPath = URL.replace('<jobId>', jobId)
    headers = {'Token': token, 'accept': 'application/json'}

    print(f'This is the parse path: {parsedPath}')
    # trying to make a connection
    try:
        r = requests.post(parsedPath, data=data, headers=headers)
        print(r)
        if r.status_code == 200:
            values = r.json()
            wells.append(values)

        # catch timeouts and errors
        elif r.status_code != 200 and (r.status_code == range(500, 599, 1) or range(400, 410, 1)):  # bad request:
            # server error, wait and try again
            # take a break for 4 second
            time.sleep(20)
            try:
                r = requests.post(parsedPath, data=data, headers=headers)
                print(r)
                if r.status_code == 200:
                    values = r.json()
                    wells.append(values)

            except Exception as ex:
                logging.error("Error sending request to server")
                logging.error("Query {}".format(parsedPath))
                logging.error("Parameters {}".format(params))
                logging.error("Headers {}".format(headers))
                logging.error("Response {}".format(r))
                retries = retries + 1
                logging.error("Sleeping for {} seconds".format(retries))

    except Exception as ex:
        logging.error("Error sending request to server")
        logging.error("Query {}".format(parsedPath))
        logging.error("Parameters {}".format(params))
        logging.error("Headers {}".format(headers))
        logging.error("Response {}".format(r))
        retries = retries + 1
        logging.error("Sleeping for {} seconds".format(retries))
        time.sleep(retries)

    return wells

# URLS
@retry(stop=stop_after_attempt(4), wait=wait_fixed(2), retry_error_callback=lambda _: print("Retrying..."))
def URLs_v1(serverURL, OperatorName='', JobStatus='ActiveOnly', Since=None):
    # Variables:

    URL = {}
    jobId = ''
    runId = ""
    broadcastTimeTo = ""
    broadcastTimeFrom = ""
    take = 1
    skip = 0
    Total = True
    Format = ""
    attributeId = ""
    summaryReportId = ""
    fileFormatId = ""
    metakey = ""
    classification = ""
    reportGroupId = ""
    swabSurgeType = ""

    ################################################################################################################
    # Various URLs
    ################################################################################################################

    # URL to the API Service to create the authentication token
    URL['getToken'] = serverURL;

    # URL to the API Service to retrieve active well information (Note the filter = ActiveOnly Parameter
    # For all wells, import filter = All

    # TODO: Update these to the new Swagger 2.0, Add the additional ones such as GetJob, see instructions for the ones you need.

    # URL for getting wells/jobs
    # URL['getWells'] = serverURL + '/api/1.0/wells?filter=' + WellStatus + '&sort=WellID%20ASC&take=<take>&skip=<skip>' + AdditionalFilter
    # TODO: don't hard code Total as true
    # URL['getJobs'] = serverURL + '/jobs?JobStatus=' + JobStatus + '&includeCapabilities=false&sort=id%20ASC&take=50&skip=0&total=true'

    # Jobs Header:
    URL['getJobs'] = serverURL + "/jobs?jobStatus=<jobStatus>&startDateMin=<startDateMin>&startDateMax=<startDateMax>&endDateMin=<endDateMin>&endDateMax=<endDateMax>&includeCapabilities=<includeCapabilities>&sort=<sort>%20<sortOrder>&take=<take>&skip=<skip>&total=<total>"  # Fetches all jobs

    URL['getJobsCapabilities'] = serverURL + f'/jobs/capabilities'  # Fetches the capabilities of the jobs endpoint
    URL['getJobsId'] = serverURL + f'/jobs/jobId'  # Fetches a job by its id
    URL['getJobsIdCapabilities'] = serverURL + f'/jobs/jobId/capabilities'  # Fetches the capabilities of a job


    # Attributes
    # ex: https://data.welldata.net/jobs/net_176376/alarm-events?broadcastTimeFrom=2022-01-01T00%3A19%3A00.990Z&broadcastTimeTo=2023-01-01T00%3A00%3A00.990Ztake=1&skip=0&total=true
    URL['getAttributes'] = serverURL + f'/jobs/<jobId>/attributes'  # Fetches the attributes for a single job
    URL[
        'getAttributesCapabilities'] = serverURL + f'/jobs/<jobId>/attributes/capabilities'  # Fetches the attributes capabilities for a single job


    # Time Based
    # ex: https://data.welldata.net/jobs/net_176376/alarm-events?broadcastTimeFrom=2022-01-01T00%3A19%3A00.990Z&broadcastTimeTo=2023-01-01T00%3A00%3A00.990Ztake=1&skip=0&total=true
    URL[
        'getTimeBasedCapabilities'] = serverURL + f'/jobs/<jobId>/data/surveys'  # Rgets all the surveys filtered by the optional parameters approved, unapproved, fromDepth, endDepth
    URL[
        'getCurrentTimeBased'] = serverURL + f'/jobs/<jobId>/data/surveys/capabilities'  # Fetches the capabilities for the historical surveys specified by the Job ID.
    URL[
        'getCurrentTimeBasedCapabilities'] = serverURL + f'/jobs/<jobId>/data/surveys/current/capabilities'  # Fetches the capabilities for the real-time survey specified by the Job ID.
    URL[
        'postTimeBased'] = serverURL + f'/jobs/<jobId>/data/time'  # generates swab/surge tripping model for equivalent mud weights
    URL[
        'postCurrentTimeBased'] = serverURL + f'/jobs/<jobId>/data/time/current'  # generates swab/surge tripping model for equivalent mud weights


    # Events
    # ex: https://data.welldata.net/jobs/net_176376/alarm-events?broadcastTimeFrom=2022-01-01T00%3A19%3A00.990Z&broadcastTimeTo=2023-01-01T00%3A00%3A00.990Ztake=1&skip=0&total=true
    URL['postEvents'] = serverURL + f'/jobs/<jobId>/data/time/events'  # Fetches events for a single job
    URL[
        'getEventsCapabilities'] = serverURL + f'/jobs/<jobId>/data/time/events/capabilities'  # Fetches the Events capabilities for a single job

    # Tokens
    # ex: https://data.welldata.net/jobs/net_176376/alarm-events?broadcastTimeFrom=2022-01-01T00%3A19%3A00.990Z&broadcastTimeTo=2023-01-01T00%3A00%3A00.990Ztake=1&skip=0&total=true
    URL['getTokens'] = serverURL + f'/tokens/token'  # authenticates a user and returns an authentication token.

    # Units
    # ex: https://data.welldata.net/jobs/net_176376/alarm-events?broadcastTimeFrom=2022-01-01T00%3A19%3A00.990Z&broadcastTimeTo=2023-01-01T00%3A00%3A00.990Ztake=1&skip=0&total=true
    URL['getUnits'] = serverURL + f'/units/definitions'  # retrieves unit of measure definitions
    URL['getUnitsCapabilities'] = serverURL + f'/units/definitions/capabilities'  # retrieves capabilities for unit definitions

    # Users
    # ex: https://data.welldata.net/jobs/net_176376/alarm-events?broadcastTimeFrom=2022-01-01T00%3A19%3A00.990Z&broadcastTimeTo=2023-01-01T00%3A00%3A00.990Ztake=1&skip=0&total=true
    URL['getUsers'] = serverURL + f'/users/current'  # Fetches the current user
    URL['getUsersCapabilities'] = serverURL + f'/users/current/capabilities'  # Fetches the capabilities of the current user endpoint



    # return the URL based on the call
    return URL



