from flask import Flask, request, make_response
import requests
import json
import os
from flask_cors import cross_origin
from logger import logger
import webbrowser
from email_templates import template_reader
from SendEmail.sendEmail import EmailSender

import pymongo
from datetime import datetime



app = Flask(__name__)

# geting and sending response to dialogflow
@app.route('/webhook', methods=['POST'])
@cross_origin()

def webhook():

    req = request.get_json(silent=True, force=True)

    res = processRequest(req)

    res = json.dumps(res, indent=4)

    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

# processing the request from dialogflow
def processRequest(req):
    log = logger.Log()

    sessionID=req.get('responseId')

    result = req.get("queryResult")
    user_says=result.get("queryText")
    log.write_log(sessionID, "User Says: " + user_says)

    parameters = result.get("parameters")
    cust_name =parameters.get("cust_name")
    cust_contact = parameters.get("cust_contact")
    cust_email=parameters.get("cust_email")
    pin_code= parameters.get("pin_code")

    intent = result.get("intent").get('displayName')
    if (intent=='CORONA_BY_PINCODE'):

        results = getFrmPincode(pin_code)
        district_name = results[0]["PostOffice"][0]["District"]
        state_name = results[0]["PostOffice"][0]["State"]
        country_name = results[0]["PostOffice"][0]["Country"]

        print(district_name) # delete

        fulfillmentText = " "
        state_data = getStateCovidCases(state_name)
        print(state_data)
        print(len(state_data['districtData']))


        try:
            district_data = getDistrictCovidCases(state_data, district_name)
            if district_data['active'] > 0:
                messageTxt = getCovidDist(district_data)
                fulfillmentText = district_name + '(' + pin_code + ')' + ' -- ' + messageTxt

                print(fulfillmentText)  #delete

                # Store the details to database
                dbConn = pymongo.MongoClient("mongodb://localhost:27017/")  # opening a connection to Mongo
                db = dbConn['covidReqDB']  # connect to the database called covidReqDB
                dateTimeObj = datetime.now()

                mydict = { "Name": cust_name, "Email": cust_email, "Pincode": pin_code, "Contact": cust_contact,
                          "Time_Stamp": dateTimeObj}  # saving that detail to a dictionary

                collection = db[cust_email]
                collection.insert_one(mydict)  # inserting the dictionary



        except Exception as e:
            messageTxt = getCovidState(state_data)
            fulfillmentText = messageTxt

        template= template_reader.TemplateReader()
        email_message = template.read_covid_template()
        email_sender  = EmailSender()
        email_sender.send_email(cust_name,cust_email, email_message, fulfillmentText)

        fulfillmentText += "We have sent the preventive measures of Carona(Covid-19) disease to you via email. Do you have any queries?"

        log.write_log(sessionID, "Bot Says: " + fulfillmentText)
        return {
            "fulfillmentText": fulfillmentText
        }
    else:
        log.write_log(sessionID, "Bot Says: " + result.fulfillmentText)



    if (intent=='CORONA_MAP_INDIA'):
        webbrowser.open('https://www.covid19india.org/')

    if (intent == 'CORONA_BY_WORLD'):
        webbrowser.open('https://news.google.com/covid19/map?hl=en-IN&gl=IN&ceid=IN:en')


# get Data From Pincode
def getFrmPincode(pin_code):
    url = f"https://api.postalpincode.in/pincode/{pin_code}"
    r = requests.get(url).json()
    return r

# get Data From State
def getStateCovidCases(state_name):
    url = f"https://api.covid19india.org/state_district_wise.json"
    r = requests.get(url).json()
    result = r[state_name]
    return result

# get Data From District
def getDistrictCovidCases(r, district_name):
    result = r["districtData"][district_name]
    return result

# get Data in Message from District
def getCovidDist(district_data):
    result = "   Confirmed Cases:" + str(district_data['confirmed']) + \
             "   Active Cases:"    + str(district_data['active'])    + \
             "   Deceased Cases:"  + str(district_data['deceased'])  + \
             "   Recovered Cases:" + str(district_data['recovered']) + '. '
    return result

# get Data in Message from District
def getCovidState(state_data):
    result = "   Confirmed Cases:" + str(district_data['confirmed']) + \
             "   Active Cases:"    + str(district_data['active'])    + \
             "   Deceased Cases:"  + str(district_data['deceased'])  + \
             "   Recovered Cases:" + str(district_data['recovered']) + '. '
    return result


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("Starting app on port %d" % port)
    #app.run(debug=True, port=port, host='0.0.0.0')
    app.run()