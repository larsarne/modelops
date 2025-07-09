import requests
import json
from pathlib import Path
import os
import swat
import base64
import certifi
import time

class ModelOps:

    projectID: str
    baseURL: str
    retrainingUrl: str
    refresh_token: str
    token: str
    dataSet: str
    dataUri: str

    def __init__(self):
        self.get_config()

    def get_config(self):
        home_directory = os.path.expanduser("~")
        self.baseURL = Path(home_directory+'/baseurl.txt').read_text().replace('\n', '')
        # read refresh_token from a local file 
        self.refresh_token = Path(home_directory+'/refresh_token.txt').read_text().replace('\n', '')        

    def authenticateToViya(self):
        home_directory = os.path.expanduser("~")
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        auth_url = f"{self.baseURL}/SASLogon/oauth/token"
        payload=f'grant_type=refresh_token&refresh_token={self.refresh_token}'
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic c2FzLmNsaTo=',
            }
        response = requests.request("POST", auth_url, headers=headers, data=payload, verify=False)
        self.token = response.json()['access_token']

    def training(self, ID, dataSet):
        self.projectID=ID
        # The data set we want to train this project on
        self.dataUri = "/dataTables/dataSources/cas~fs~cas-shared-default~fs~Public/tables/"+ dataSet
        #Perform Batch Retrain
        self.retrainingUrl = f"{self.baseURL}/dataMiningProjectResources/projects/{self.projectID}/retrainJobs"
        querystring = {"action":"batch", "dataUri":self.dataUri}
        payload = ""
        headers = {
            "Authorization": "Bearer " + self.token,
            "accept": "application/vnd.sas.job.execution.job+json",
        }
        response = requests.request("POST", self.retrainingUrl, data=payload, headers=headers, params=querystring)

    def waitforTrainingToFinish(self):
        #Wait before starting to look for the job
        time.sleep(10)
        #Get Current Retraining Job
        currentRetrainingJobUrl = self.retrainingUrl + "/@currentJob"
        payload = ""
        headers = {
            "Authorization": "Bearer " + self.token,
            "accept": "application/vnd.sas.job.execution.job+json",
            }
        response = requests.request("GET", currentRetrainingJobUrl, data=payload, headers=headers)
        response_txt = response.text
        job = json.loads(response_txt)

        jobLinks = job["links"]

        for link in jobLinks:
            if link["rel"] == "self":
                selfLink = link
            break;

        attempts = 0
        maxAttempts = 300

        while True:
            attempts = attempts + 1
            selfLinkUrl = self.baseURL + selfLink["uri"]
            payload = ""
            headers = {
                "Authorization": "Bearer " + self.token,
                "accept": "application/vnd.sas.job.execution.job+json",
                }
            response = requests.request("GET", selfLinkUrl, data=payload, headers=headers)

            response_txt = response.text
            job = json.loads(response_txt)

            self.jobState = job["state"]
            print("Retraining job state is "+ self.jobState)

            if self.jobState == "completed" or self.jobState == "canceled" or self.jobState == "failed" or self.jobState == "timedOut" or attempts > maxAttempts:
                break;
            #Wait for 10 seconds before polling the job again
            time.sleep(10)

        print("Final retraining job state is " + self.jobState)

    def championModel(self):
        querystring = {"action":"batch", "dataUri":self.dataUri}
        #Get Champion
        if self.jobState == "completed":
            championUri = self.retrainingUrl + "/@lastJob/champion"
            payload = ""
            headers = {
                "Authorization": "Bearer " + self.token,
                "accept": "application/vnd.sas.analytics.data.mining.model+json",
                }
            response = requests.request("GET", championUri, data=payload, headers=headers, params=querystring)
            #If the project has a champion model, it will be printed
            if response.status_code == requests.codes.ok:
                response_txt = response.text
                model = json.loads(response_txt)
                projectChampion = model["name"]
                print("Project champion model is " + projectChampion + " with ID:" + model["id"] )
        

modelops = ModelOps()
modelops.authenticateToViya()
modelops.training("49724711-69c3-4e46-b746-59f04d57ad38", "HMEQ")
modelops.waitforTrainingToFinish()
modelops.championModel()

