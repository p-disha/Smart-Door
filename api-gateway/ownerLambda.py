import boto3, random, json, string, uuid
import datetime, time
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal


dynamodb = boto3.resource('dynamodb')
table_passcodes = dynamodb.Table("passcodes")
table_visitors = dynamodb.Table("visitors")

s3_bucket = "face-rek-bucket"


def generate_passcode():
    return random.randint(100001, 999999)


def fill_dynamodb_passcodes(faceId,email, passcode):
    expiry_time = Decimal(time.time() + (60 * 5))
    data = {
        "faceId" : faceId,
        "email" : email,
        "passcode" : passcode,
        "expTime" : expiry_time
    }
    table_passcodes.put_item(Item = data)


def fill_dynamodb_visitors(faceId, name, phoneNumber):
    visitor = table_visitors.query(KeyConditionExpression=Key('faceId').eq(faceId))    
    faceIdPhoto = name + ".jpg"
    currTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data = {
        "faceId" : faceId,
        "name" : name,
        "phoneNumber" : phoneNumber,
        "photos" : [
            {
                "objectKey" : faceIdPhoto,
                "bucket" : s3_bucket,
                "createdTimestamp" : currTime
            }
        ]
    }
    table_visitors.put_item(Item = data)
    msg = "Visitor " + name + " has been added!"
    return msg
    

def respond(err, response=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err if err else json.dumps(response),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def visitorSMS(contact, pin):
    LinkToEnterOTP = "https://face-rek-bucket.s3.amazonaws.com/indexVisitor.html"
    msg = 'Hello there, here is your pin to enter in the apartment. \n PIN : ' + str(pin)+ "\nGo to " + LinkToEnterOTP+" to enter pin. Your pin will expire in 5 minutes."
    sns = boto3.client('sns')
    response = sns.publish(
    PhoneNumber=contact,
    Message=msg # this should include link to submit visitor info
    )


def getCurrentFaceId():
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.query(KeyConditionExpression=Key('faceId').eq("1"))
    return response['Items'][0]['faceIdValue'], response['Items'][0]['bucketFileName'] 


def getBucketFileName():
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.query(KeyConditionExpression=Key('faceId').eq("1"))
    return response['Items'][0]['bucketFileName']


def getFaceIdFromCUrrentUser():
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.query(KeyConditionExpression=Key('faceId').eq("1"))
    return response['Items'][0]['faceIdValue']


def storeVisitorEmail(visitor_phone, faceId):
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.get_item(Key={'faceId': '1'})
    item = response['Item']
    # update
    item['email'] = str(visitor_phone)
    item['faceIdValue'] = str(faceId)
    currentUser.put_item(Item=item)


def index_face(collection_id, bucket, photo):
    client=boto3.client('rekognition')
    response=client.index_faces(CollectionId=collection_id,
                                Image={'S3Object':{'Bucket':bucket,'Name':photo}},
                                ExternalImageId=photo,
                                MaxFaces=1,
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])
    print ('Results for ' + photo)
    print('Faces indexed:')
    for faceRecord in response['FaceRecords']:
         print('  Face ID: ' + faceRecord['Face']['FaceId'])
         print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))

    print('Faces not indexed:')
    for unindexedFace in response['UnindexedFaces']:
        print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
        print(' Reasons:')
        for reason in unindexedFace['Reasons']:
            print('   ' + reason)
    if(len(response['FaceRecords'])>=1):
        return faceRecord['Face']['FaceId']
    else:
        return ""


def visitorNewSMS(email,otp):
    LinkToEnterOTP = "https://face-rek-bucket.s3.amazonaws.com/indexVisitor.html"
    msg = 'Hello there, here is your pin to enter in the apartment. \n PIN : ' + str(otp)+ "\nGo to " + LinkToEnterOTP+" to enter pin. Your pin will expire in 5 minutes."
    sns = boto3.client('sns')
    response = sns.publish(
    TopicArn = 'arn:aws:sns:us-east-1:025289136445:emailTpc',    
    Message=msg)


def saveToPermanentBucket(permImageName):
    s3 = boto3.resource('s3')
    copy_source = {
    'Bucket': 'images-door-bell',
    'Key': 'frame.jpg'
    }
    s3.meta.client.copy(copy_source, 'face-rek-bucket', permImageName)


def lambda_handler(event, context):
    visitor_name = event['message']['name-input']
    visitor_phone = event['message']['phone-input']
    bucketFileName = str(visitor_name)+".jpg"
    saveToPermanentBucket(bucketFileName)
    resp = index_face('faces','face-rek-bucket',bucketFileName)
    print (resp)
    faceId = resp

    storeVisitorEmail(visitor_phone, faceId)
    msg = fill_dynamodb_visitors(faceId, visitor_name, visitor_phone)
    otp = generate_passcode()
    fill_dynamodb_passcodes(faceId,visitor_phone, otp)

    visitorNewSMS(visitor_phone,otp)
    return respond(None, msg)
