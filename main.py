# Main Place to do case scenarios
#
#
#
#
#

import json
import logging
from datetime import datetime, timedelta
import pandas as pd
from pydantic import BaseModel
import SampleHelper
import Sample_WD_API
import time

class UnitV1(BaseModel):
    id: str
    name: str
    abbreviation: str


class Attribute(BaseModel):
    id: str
    mode: str

logging.basicConfig(filename='API_TimeTest.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


def make_api_call(counter):
    logging.info('Starting script')
    #######################################################################
    # Setup
    #######################################################################

    #SampleHelper file is used to setup the configuration
    SampleHelper.SetupLogging(logging, logging.DEBUG)
    SampleHelper.SetupLocale()

    SampleHelper.VersionCheck()

    # WellData Config
    configFile = SampleHelper.SetConfigFile(Sample_WD_API.defaultConfig())

    CFGdefault = SampleHelper.readConfig(configFile, Sample_WD_API.defaultConfig())

    #parses the api request -> this currently uses the SampleData as the config file
    CFG = SampleHelper.readConfig(configFile, Sample_WD_API.serverConfig('welldata net'))
    CFG.update(CFGdefault)

    # Process Name, used for stateless process control
    processName = 'PlusPetroRealTimeData'

    DataSource = None
    if CFG['APIUrl'] == 'https://data.welldata.net/api/v1':
        DataSource = 'WellData Data API .NET'
    else:
        logging.error("Unknown Datasource {}. Aborting".format(DataSource))
        quit()

    #setting up URL call
    URLs_v1 = Sample_WD_API.URLs_v1(CFG['APIUrl'], CFG['ContractorName'], CFG['OperatorName'],  CFG['JobStatus'])

    # Start the timer
    start_time = time.time()


    # Generates Token for Header
    token = Sample_WD_API.getToken(CFG['APIUrl'], CFG['appID'], CFG['username'], CFG['password'])

    getTokenTimes = []
    issueJobs = []

    # Calculate the elapsed time
    getToken_time = time.time() - start_time
    getTokenTimes.append(getToken_time)
    if getToken_time > 5:
        issueJobs.append(["token",getToken_time])


    #######################################################################
    # Main Code
    #######################################################################



    #variables
    ################################

    # Containers
    jobsList = []
    jobsAttr = []
    jobsTimeBased = []
    # jobsCurrTime = []
    # jobEvents = []

    allJobsTimes = []
    singleJobsIdTimes = []
    attributesTimes = []
    histPullTimes = []
    script_processTimes = []


    #Getting a list of all Sample Jobs
    tmpJobList = Sample_WD_API.getJobs(URLs_v1['getJobs'], token, CFG, take=1000, total=False,jobStatus=CFG["JobStatus"])

    # Calculate the elapsed time
    allJobs_time = time.time() - getToken_time
    allJobsTimes.append(allJobs_time)
    if allJobs_time > 5:
        issueJobs.append(["GetJobsAPI",allJobs_time])
    # Time to begin the next iteration
    beginning_time = time.time()

    expectedAttr = CFG['FilterList']


    for w in tmpJobList:
        try:
            # Time historical example of using it
            well = w['id']  # Enter Well ID here
            holder = []

            # list to attribute  UnitV1  Attribute
            attsLst = []

            # Start the timer
            beginning_time = time.time()

            # 1 getting Job,
            j = Sample_WD_API.getJobs(URLs_v1['getJobsId'], token, CFG, take=1000, jobId=w['id'], jobStatus=CFG['JobStatus']  ) #jobStatus="ActiveJobs"
            # Calculate the elapsed time
            singleJobs_time = time.time() - beginning_time
            singleJobsIdTimes.append(singleJobs_time)
            if singleJobs_time > 5:
                issueJobs.append([well, singleJobs_time])

            jobsList.append(j)

            # Get attributes, and store them in list
            q = Sample_WD_API.getApiCall(URLs_v1['getAttributes'], token, CFG, jobId=w['id'])

            # Getting All attributes with Data
            for c in q[0]['attributes']:
                if c['hasData'] == True:
                    jobsAttr.append([w['id'], c])
                    holder.append(c)
                    attr = Attribute(id=c['id'], mode='Last')
                    attsLst.append(attr)
                    # if c['id'] in expectedAttr:

            # Gets time for Retrieving all attributes that has data
            attributes_time = time.time() - singleJobs_time
            attributesTimes.append(attributes_time)
            if attributes_time > 5:
                issueJobs.append([well, attributes_time])




            # Variables
            if len(attsLst) == 0:
                continue
            to_time = datetime.now() - timedelta(hours=CFG['ToHours'])
            from_time = datetime.now() - timedelta(hours=CFG['FromHours'])
            time_Range= Sample_WD_API.TimeRange(from_=from_time, to=to_time)
            filter_att= Sample_WD_API.Filter(attributeId=attsLst[0].id, greaterThanEqual={"value": 0})

            curr_frequency = 1
            hist_interval = 43200  # 6hrs- 21600, 12 hrs - 43200, 24hrs - 86400
            curr_interval = 0

            # Creating Payloads
            hist_payload = Sample_WD_API.HistoricalTimeRequest(attributes=attsLst, toTime=to_time, fromTime=from_time, interval=hist_interval)

            curr_payload = Sample_WD_API.CurrentTimeRequest(attributes=attsLst, frequency=curr_frequency, interval=curr_interval)
            event_payload = Sample_WD_API.EventTimeRequest(outputAttributes=attsLst , timeRange= time_Range, filter=filter_att)


            # Post request
            hist = Sample_WD_API.historical_data_time(well, hist_payload.json(exclude_unset=True), token=token)
            print(hist)

            # Gets time for Retrieving all attributes that has data
            histpull_time = time.time() - singleJobs_time
            histPullTimes.append(histpull_time)
            if histpull_time > 5:
                issueJobs.append([well, histpull_time])


            # curr = Sample_WD_API.current_data_time(well, curr_payload.json(exclude_unset=True), token=token)
            # print(curr)
            # events = Sample_WD_API.event_data_time(well, event_payload.json(exclude_unset=True), token=token)
            # print(curr)
            # Saving to containers
            jobsTimeBased.append([well, hist])
            # jobsCurrTime.append([well, curr])
            # jobEvents.append([well, events])

            process_time = time.time() - start_time
            script_processTimes.append(process_time)
            if process_time > 5:
                issueJobs.append([well, process_time])

        except Exception as ex:
            print(well)
            logging.error("Error sending request")
            logging.error(f"Exception: {ex}")
            pass

    # Writing DataFrame to Excel sheet
    writer = pd.ExcelWriter(f' {counter} - API Time Tester-interval({hist_interval}).xlsx', engine='openpyxl')
    header = ['jobid', 'well name', 'contractor', 'rignumber', 'startDate', 'firstDataDate', 'lastDataDate', '']
    df = pd.DataFrame(jobsList)
    df.to_excel(writer, sheet_name='JobsID', index=False, header=header)
    df = pd.DataFrame(jobsAttr)
    df.to_excel(writer, sheet_name='Attributes', index=False, header=["Job ID", "Attribute Data"])
    df = pd.DataFrame(jobsTimeBased)
    df.to_excel(writer, sheet_name='TimeBased', index=False, header=["Job ID", "Historical Data"])
    df = pd.DataFrame(getTokenTimes)
    df.to_excel(writer, sheet_name='Token Time', index=False, header=["Get Token Time Data"])
    df = pd.DataFrame(allJobsTimes)
    df.to_excel(writer, sheet_name='All Jobs Time', index=False, header=["All Jobs Time Data"])
    df = pd.DataFrame(singleJobsIdTimes)
    df.to_excel(writer, sheet_name='Job_Id Time', index=False, header=["Job by Id Time"])
    df = pd.DataFrame(attributesTimes)
    df.to_excel(writer, sheet_name='AttribPull Time', index=False, header=["All Attrib with data Time"])
    df = pd.DataFrame(histPullTimes)
    df.to_excel(writer, sheet_name='Hist_Pull Time', index=False, header=["Historic Pull Time- 'time/Data'"])
    df = pd.DataFrame(script_processTimes)
    df.to_excel(writer, sheet_name='Total Process Time', index=False, header=["Total Process Time"])
    df = pd.DataFrame(issueJobs)
    df.to_excel(writer, sheet_name='IssueJobs', index=False, header=["JobID", "Time"])

    writer.close()




def main():
    for i in range(1, 4):  # Range from 1 to 4 for three calls
        try:
            result = make_api_call(i)
            # Process the result

        except Exception as e:
            print(f"Error occurred: {str(e)}")

main()