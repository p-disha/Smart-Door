from __future__ import print_function

import base64
import json
import boto3
import cv2
import time
import sys
import datetime
from random import randint
from boto3.dynamodb.conditions import Key, Attr
import json


def face_check(face_search):
    if face_search['DetectedFace']:
        if face_search['MatchedFaces'] == []:
            return False
        else:
            return True
    return False


def extract_frame(fragments):
    return get_frame(fragments)


def get_face_id(face_search):
    return face_search['MatchedFaces'][0]['Face']['FaceId']


def face_handler(face_search, frag_num):
    if face_check(face_search) == True:
        face_id = get_face_id(face_search)
        extract_frame(frag_num)
        print("face id = " + face_id)        
    else:
        if face_search['DetectedFace'] == []:
            print("No face detected!")
            return None 
        else:
            print("getting the frame")
            
            
def index_face(collection_id, bucket_name, bucket_file_name):

    print("Indexing[" + bucket_name + ":" + bucket_file_name +
          "] into collection[" + collection_id + "]")
    client = boto3.client('rekognition')
    response = client.index_faces(CollectionId=collection_id,
                                  Image={'S3Object': {
                                      'Bucket': bucket_name, 'Name': bucket_file_name}},
                                  ExternalImageId=bucket_file_name.split(
                                      "/")[1],
                                  DetectionAttributes=())

    print("Index Face Response - ")
    for faceRecord in response['FaceRecords']:
        print ("  FaceId : {} and ExternalImageId : {}".format(
            faceRecord['Face']['FaceId'], faceRecord['Face']['ExternalImageId']))

    if len(response['FaceRecords']) > 0:
        return response['FaceRecords']
    else:
        print("No Faces Found in image")
        return None
            

def ownerRequestAccessSMS(contact,visitorImageLink, webpageLink):
    msg = 'Hi, someone is at your apartment front-door.\n View Picture of visitor : ' +visitorImageLink+ '\nApprove/ Deny Entry : ' + webpageLink
    sns = boto3.client('sns')
    response = sns.publish(
    PhoneNumber=contact,
    Message=msg # this should include link to submit visitor info
    )


def visitorSMS(contact, pin):
    LinkToEnterOTP = "https://face-rek-bucket.s3.amazonaws.com/indexVisitor.html"
    msg = 'Hello there, here is your pin to enter in the apartment. \n PIN : ' + str(pin)+ "\nGo to " + LinkToEnterOTP+" to enter pin. Your pin will expire in 5 minutes."
    sns = boto3.client('sns')
    response = sns.publish(
    PhoneNumber=contact,
    Message=msg # this should include link to submit visitor info
    )

   
def updateCurrentUser(faceId, s3ImageLink):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('currentUser')
    
    response = table.get_item(Key={'faceId': '1'})
    print (response)
    item = response['Item']
    
    # update
    item['faceIdValue'] = str(faceId)
    item['bucketFileName'] = str(s3ImageLink)    
    table.put_item(Item=item)


def ownerSMS(ownersContact,visitorImageLink, ownerWebpageLink):
    msg = 'Hi, someone is at your apartment front-door.\n View Picture of visitor : ' +visitorImageLink+ '\nApprove/ Deny Entry : ' + ownerWebpageLink
    sns = boto3.client('sns')
    response = sns.publish(
    TopicArn = 'arn:aws:sns:us-east-1:025289136445:ownerTpc',    
    Message=msg)


def visitorNewSMS(email,otp):
    LinkToEnterOTP = "https://face-rek-bucket.s3.amazonaws.com/indexVisitor.html"
    msg = 'Hello there, here is your pin to enter in the apartment. \n PIN : ' + str(otp)+ "\nGo to " + LinkToEnterOTP+" to enter pin. Your pin will expire in 5 minutes."
    sns = boto3.client('sns')
    response = sns.publish(
    TopicArn = 'arn:aws:sns:us-east-1:025289136445:emailTpc',    
    Message=msg)


def saveBucketKeyToCurrentUser(bucket_key):
    dynamodb = boto3.client('dynamodb')
    currentUser = dynamodb.Table("currentUser")
    response = currentUser.get_item(Key={'faceId': '1'})
    print (response)
    item = response['Item']
    # update
    item['bucketFileName'] = bucket_key
    currentUser.put_item(Item=item)


def addVisitorsPhotoToDb(faceId):
    dynamodb = boto3.resource('dynamodb')
    table_visitors = dynamodb.Table("visitors")
    visitor = table_visitors.query(KeyConditionExpression=Key('faceId').eq(faceId))
    faceIdPhoto = visitor['Items'][0]['name']+".jpg"
    currTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    msg = "Visitor " + visitor['Items'][0]['name'] + "'s photo has been added!"


def addVisitorsPhotoToS3(faceId):
    dynamodb = boto3.resource('dynamodb')
    table_visitors = dynamodb.Table("visitors")
    visitor = table_visitors.query(KeyConditionExpression=Key('faceId').eq(faceId))
    faceIdPhoto = visitor['Items'][0]['name']+".jpg"
    s3 = boto3.resource('s3')
    copy_source = {
    'Bucket': 'images-door-bell',
    'Key': 'frame.jpg'
    }
    s3.meta.client.copy(copy_source, 'face-rek-bucket', faceIdPhoto)

def lambda_handler(event, context):
    ownersContact = "+17029696238"
    ownerWebpageLink = "https://face-rek-bucket.s3.amazonaws.com/index.html"
    personDetected = False
    streamName = "myStream"
    for record in event['Records']:        
        if personDetected is True:
            break
        payload = base64.b64decode(record['kinesis']['data'])
        result = json.loads(payload.decode('utf-8'))
        print(result['InputInformation'])
        if len(result['FaceSearchResponse']) > 0:
            personDetected = True
            print("FaceSearchResponse not empty =" +
                  json.dumps(result['FaceSearchResponse']))
        else:
            continue
        faceResponse = result['FaceSearchResponse']
        frag_id = result['InputInformation']['KinesisVideo']['FragmentNumber']
        print("frag_id =", frag_id)

        kvs = boto3.client("kinesisvideo")
        # Grab the endpoint from GetDataEndpoint
        endpoint = kvs.get_data_endpoint(
            APIName="GET_HLS_STREAMING_SESSION_URL",
            StreamName=streamName
        )['DataEndpoint']

        # # Grab the HLS Stream URL from the endpoint
        kvam = boto3.client("kinesis-video-archived-media",
                            endpoint_url=endpoint)
        url = kvam.get_hls_streaming_session_url(
            StreamName=streamName,
            PlaybackMode="LIVE_REPLAY",
            HLSFragmentSelector={
                'FragmentSelectorType': 'SERVER_TIMESTAMP',
                'TimestampRange': {
                    'StartTimestamp': result['InputInformation']['KinesisVideo']['ServerTimestamp']
                }
            }
        )['HLSStreamingSessionURL']
        
        vcap = cv2.VideoCapture(url)
        final_key = 'frame.jpg'
        s3_client = boto3.client('s3')
        bucket = "images-door-bell"
        while(True):
            # Capture frame-by-frame
            ret, frame = vcap.read()

            if frame is not None:
                # Display the resulting frame
                vcap.set(1, int(vcap.get(cv2.CAP_PROP_FRAME_COUNT) / 2) - 1)
                cv2.imwrite('/tmp/' + final_key, frame)
                s3_client.upload_file('/tmp/' + final_key, bucket, final_key)
                vcap.release()
                print('Image uploaded')
                break
            else:
                print("Frame is None")
                break

        # When everything done, release the capture
        vcap.release()
        cv2.destroyAllWindows()
        
        location = boto3.client('s3').get_bucket_location(
            Bucket=bucket)['LocationConstraint']
        s3ImageLink = "https://%s.s3.amazonaws.com/%s" % (
            bucket, final_key)
        print("s3ImageLink ====" + s3ImageLink)
        
        # db and sns
        snsClient = boto3.client('sns')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        visitorsTable = dynamodb.Table('visitors')
        
        unknownFace = True
        for face in faceResponse:
            for matchedFace in face["MatchedFaces"]:
                print("matchedFace ===")
                print(matchedFace)
                print(matchedFace['Face']['FaceId'])
                faceId = matchedFace['Face']['FaceId']
                
                print ("FaceID =============")
                print ("faceId :", faceId)
                #get the faceid from db 
                response = visitorsTable.query(
                    KeyConditionExpression=Key('faceId').eq(faceId))
                    
                # updateCurrentUser
                updateCurrentUser(faceId, final_key)
                
                print("response =====")
                print(response['Items'])
                if len(response['Items']) > 0:
                    
                    phoneNumber = response['Items'][0]['phoneNumber']
                    passcodeTable = dynamodb.Table('passcodes')
                    
                    currentEpochTime = int(time.time())
                    print("currentEpochTime ============")
                    print(currentEpochTime)
                    
                    passcodeResponse = passcodeTable.query(KeyConditionExpression=Key(
                        'faceId').eq(faceId))
                    if len(passcodeResponse['Items']) > 0:
                        if passcodeResponse['Items'][0]['expTime'] < currentEpochTime: #generate new otp
                            otp = randint(100001, 999999)
                        else:
                            otp = passcodeResponse['Items'][0]['passcode']
                    else:
                        otp = randint(100001, 999999)
                    response = passcodeTable.put_item(
                        Item={
                            "faceId" : faceId,
                            "passcode": otp,
                            "expTime": int(time.time() + 5 * 60)
                        })
                    visitorNewSMS(phoneNumber, otp)
                    
                    addVisitorsPhotoToS3(faceId)
                    unknownFace = False
                break
        if unknownFace:
            print("unknownFace =")
            visitorImageLink = s3ImageLink
            ownerSMS(ownersContact,visitorImageLink, ownerWebpageLink)
        
    return 'Successfully processed {} records.'.format(len(event['Records']))
