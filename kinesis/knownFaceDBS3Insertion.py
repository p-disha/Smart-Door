import base64
import json
import boto3
import time
import sys
import datetime
from random import randint
from boto3.dynamodb.conditions import Key, Attr
import json


def addVisitorsPhotoToDb(faceId):
    dynamodb = boto3.resource('dynamodb')
    table_visitors = dynamodb.Table("visitors")
    visitor = table_visitors.query(KeyConditionExpression=Key('faceId').eq(faceId))
    faceIdPhoto = faceId +"_"+str(len(visitor['Items'][0]['photos']) + 1) +".jpg"
    currTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result = table_visitors.update_item(
        Key = {
            'faceId': faceId
        },
        UpdateExpression = "SET photos = list_append(photos, :i)",
        ExpressionAttributeValues = {
            ':i': [{
                "objectKey" : faceIdPhoto,
                "bucket" : "face-rek-bucket",
                "createdTimestamp" : currTime
            }],
        },
        ReturnValues="UPDATED_NEW"
    )
    msg = "Visitor " + visitor['Items'][0]['name'] + "'s photo has been added!"


def addVisitorsPhotoToS3(faceId):
    dynamodb = boto3.resource('dynamodb')
    table_visitors = dynamodb.Table("visitors")
    visitor = table_visitors.query(KeyConditionExpression=Key('faceId').eq(faceId))
    faceIdPhoto = visitor['Items'][0]['name'] +"_"+str(len(visitor['Items'][0]['photos']) + 1) +".jpg"
    s3 = boto3.resource('s3')
    copy_source = {
    'Bucket': 'images-door-bell',
    'Key': 'frame.jpg'
    }
    s3.meta.client.copy(copy_source, 'face-rek-bucket', faceIdPhoto)


def setDBS3ValueToOne():
    dynamodb = boto3.resource('dynamodb')
    currentEntry = dynamodb.Table("DBS3Executed")
    response = currentEntry.get_item(Key={'ID': '1'})
    print ("RESPONSE :",response)
    item = response['Item']
    # update
    item['executed'] = 1
    

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    entry_check_table = dynamodb.Table("DBS3Executed")
    ID = "1"
    db_entry = entry_check_table.query(KeyConditionExpression=Key('ID').eq(ID))
    print ("Check from heree===============")
    print (db_entry)
    print (db_entry['Items'][0]['executed'])
    print(type(db_entry['Items'][0]['executed']))
    if (db_entry['Items'][0]['executed']) == 0:
        addVisitorsPhotoToDb(event['faceId'])
        addVisitorsPhotoToS3(event['faceId'])
        setDBS3ValueToOne()
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
