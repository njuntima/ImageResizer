import json
import boto3
from PIL import Image
from datetime import datetime
import os
import uuid



s3Client = boto3.client('s3')
db_client = boto3.client('dynamodb')

# bucket/table env variables
dest_bucket = os.environ['dest_bucket']
db_table = os.environ['db_table']


def lambda_handler(event, context):
    print(event)
    try:
        for record in event['Records']:   
            s3_event = json.loads(record['body'])
            
            if s3_event.get('eventName') == 's3:TestEvent':
                    print("Test Event")
                    continue     
                
            for s3_record in s3_event['Records']:
                # get src bucket/key
                src_bucket = s3_record['s3']['bucket']['name']
                src_key = s3_record['s3']['object']['key']
                
                # debugging purposes
                print(f'src_bucket:|{src_bucket}|')
                print(f'src_key:|{src_key}|')
                print(f'DynamoDB Table:|{db_table}|')

                # Extract filename from key
                file_name = src_key.split("/")[-1]
                unique_id = str(uuid.uuid4())

                # create temps
                img_download_path= f'/tmp/{unique_id}-{file_name}'
                
                # new paths
                img_new_path = f'/tmp/{unique_id}-{file_name}'
                dest_key = f"{unique_id}-{src_key}"


                # wb = binary - for non text files (images)
                # download file to tmp so lambda can use
                with open(img_download_path, 'wb') as f:
                    s3Client.download_fileobj(src_bucket, src_key, f)


                # resize image
                my_resize(1080, img_download_path, img_new_path)      
                

                #upload to destination bucket
                s3Client.upload_file(img_new_path, dest_bucket, dest_key)


                # Write metadata into DynamoDB
                db_client.put_item(
                    TableName=db_table,
                    Item={
                        'destKey': {'S': dest_key},
                        'srcBucket': {'S': src_bucket},
                        'srcKey': {'S': src_key},
                        'timeUpload': {'S': datetime.now().isoformat()}    
                    }
                    
                )
                print('Succesful DynamoDB write')
        
        
    except Exception as e:
        print(e)

# resize image function
def my_resize(newW, src_path, dest_path):
    
    im = Image.open(src_path)
    im = im.convert('RGBA')
    
    w, h = im.size
    ratio = h/w
    newH = int(ratio* newW)
    
    resizedIm = im.resize((newW, newH),Image.LANCZOS)
    resizedIm.save(dest_path)