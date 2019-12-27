import boto3, random, json, string, uuid
import datetime, time
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal


dynamodb = boto3.resource('dynamodb')
table_passcodes = dynamodb.Table("passcodes")
table_visitors = dynamodb.Table("visitors")

sns = boto3.client('sns')

s3_bucket = "face-rek-bucket"


def get_visitor_name(faceId):
    response = table_visitors.query(KeyConditionExpression=Key('faceId').eq(faceId))
    return {
        "data": response
    }


def get_visitor_passcode(faceId):
    passcode = table_passcodes.query(KeyConditionExpression=Key('faceId').eq(faceId))
    return {
        "passcode": passcode
    }
    

def respond(err, response=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err if err else json.dumps(response),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

def getCurrentFaceId():
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.query(KeyConditionExpression=Key('faceId').eq("1"))
    return response['Items'][0]['faceIdValue']

def emptyCurrentUser():
    print ("In hereeeee")
    dynamodb = boto3.resource('dynamodb')
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.get_item(Key={'faceId': str(1)})
    print ("RESPONSEEEE :" , response)
    item = response['Item']
    # update
    item['email'] = ""
    item['faceIdValue'] = ""
    currentUser.put_item(Item=item)
    
def storeVisitorPhoto(faceId):
    dynamodb = boto3.resource('dynamodb')
    table_visitors = dynamodb.Table("visitors")
    visitor = table_visitors.query(KeyConditionExpression=Key('faceId').eq(faceId))
    s3_bucket = "face-rek-bucket"

    faceIdPhoto = str(visitor['Items'][0]['name']) +"_"+str(len(visitor['Items'][0]['photos']) + 1) +".jpg"
    currTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result = table_visitors.update_item(
        Key = {
            'faceId': faceId
        },
        UpdateExpression = "SET photos = list_append(photos, :i)",
        ExpressionAttributeValues = {
            ':i': [{
                "objectKey" : faceIdPhoto,
                "bucket" : s3_bucket,
                "createdTimestamp" : currTime
            }],
        },
        ReturnValues="UPDATED_NEW"
    )
    msg = "Visitor " + str(visitor['Items'][0]['name']) + "'s photo has been added!"

def clearDBS3ExecutedLambda():
    dynamodb = boto3.resource('dynamodb')
    currentEntry = dynamodb.Table("DBS3Executed")
    response = currentEntry.get_item(Key={'ID': '1'})
    item = response['Item']
    # update
    item['executed'] = 0
    
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.get_item(Key={'faceId': '1'})
    print (response)
    item = response['Item']
    # update
    item['email'] = str(visitor_phone)
    
    
def lambda_handler(event, context):
    faceId = getCurrentFaceId()
    passcode_response = get_visitor_passcode(faceId)
    print (passcode_response)
    faceId = passcode_response["passcode"]["Items"][0]["faceId"]
    visitor_response = get_visitor_name(faceId)
    
    if str(passcode_response["passcode"]["Items"][0]["passcode"]) == str(event["message"]["passcode-input"]):
        visitor_name = visitor_response["data"]["Items"][0]["name"]
        return respond(None, "Hello " + visitor_name + ", you are welcomed!")
    else:
        return respond(None, "Permission is denied for the visitor")
