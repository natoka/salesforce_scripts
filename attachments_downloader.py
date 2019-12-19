from simple_salesforce import Salesforce
import requests
import logging
import argparse
import os
import sys
import codecs
import re
import time, datetime

ACCOUNT_TO_FILE_CSV = './attachments.csv'

def download_attachments(args):
    session = requests.Session()
    try:
        sf = Salesforce(username=args.get('user'),
                        password=args.get('passwd'),
                        security_token=args.get('token'),
                        session=session)
    except Exception, e:
        logging.error("Failed to connect SFDC: %s", str(e))
        return

    auth_id = 'Bearer ' + sf.session_id
    req_headers = {'Authorization': auth_id}

    if args.get('account_only'):
        query = ("SELECT Id, ParentId, Name, Body FROM Attachment "
                 "WHERE ParentId in (SELECT Id FROM Account)")
    elif args.get('contact_only'):
        query = ("SELECT Id, ParentId, Name, Body FROM Attachment "
                 "WHERE ParentId IN (SELECT Id FROM Contact WHERE Title = 'USA' AND RecordType.Name = 'Etown KON contact record type') ORDER BY Id ASC")
    else:
        query = "SELECT Id, ParentId, Name, Body FROM Attachment"

    result = sf.query(query)

    total_records = result.get('totalSize', 0)
    print 'Total Records: ', total_records

    if not total_records:
        logging.info("No attachments found")
        print 'No attachments found'
        return

    logging.debug("Starting to download %d attachments", total_records)

    acc_to_file = []
    ignore_words = map(str.lower, args.get('ignore', []))
    storage_dir = args.get('storage')
    sf_pod = sf.base_url.replace("https://", "").split('.salesforce.com')[0]

    records = result.get('records', {})
    for record in records:
        body_uri = record.get('Body')
        if not body_uri:
            logging.warning("No body URI for file id %s", record.get('Id', ''))
            continue

        remote_file = record.get('Name')
        remote_file_lower = remote_file.lower()
        if any(w in remote_file_lower for w in ignore_words):
            logging.info("File %s contains a word to ignore", remote_file)
            continue

        remote_path = "https://{0}.salesforce.com{1}".format(sf_pod, body_uri)
        local_file = '%s_%s' % (record.get('Id'), remote_file)

        local_file = re.findall(r'[^\*"/:?\\|<>]', local_file, re.S) 
        local_file = "".join(local_file)
        local_path = os.path.join(storage_dir, local_file)

        print time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(int(time.time()))), ':' , record.get("Id"), ':', remote_file

        logging.info("Downloading %s to %s", remote_file, local_path)
        logging.debug("Remote URL: %s", remote_path)

        resp = session.get(remote_path, headers=req_headers)
        if resp.status_code != 200:
            logging.error("Download failed [%d]", resp.status_code)
            continue
        try:
            with open(local_path, 'wb') as out_file:
                out_file.write(resp.content)
        except: 
            continue

        logging.debug("ParentId: %s", record.get('ParentId'))
        acc_to_file.append((record.get('ParentId'), local_file))

    with codecs.open(ACCOUNT_TO_FILE_CSV, 'wb', 'utf-16') as csv_file:
        csv_file.write('ParentId,FileName\n')
        csv_file.write('\n'.join('"%s","%s"' % l for l in acc_to_file))

if __name__ == "__main__":
    cli_parser = argparse.ArgumentParser(
        description='SFDC Attachments Downloader')
    cli_parser.add_argument('-u',
                            '--user',
                            help='SFDC username',
                            required=True)
    cli_parser.add_argument('-p',
                            '--passwd',
                            help='SFDC password',
                            required=True)
    cli_parser.add_argument('-t',
                            '--token',
                            help='SFDC security token',
                            required=True)
    cli_parser.add_argument('-s',
                            '--storage',
                            help='Path to store attachments',
                            required=True)
    cli_parser.add_argument('--account-only',
                            action='store_true',
                            help='Download Account attachments only')
    cli_parser.add_argument('--contact-only',
                            action='store_true',
                            help='Download Contact attachments only')
    cli_parser.add_argument('--ignore',
                            nargs='*',
                            metavar='word',
                            default=[],
                            help='Ignore filenames containing words')

    args = cli_parser.parse_args()
    if any(v is None for v in vars(args).values()):
        cli_parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.storage):
        print "ERROR: Storage path doesn't exist"
        sys.exit(1)

    if not os.path.isdir(args.storage):
        print "ERROR: Storage path must be a directory"
        sys.exit(1)

    print "Starting downloader..."

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filename='attachments_downloader.log',
                        filemode='w')

    download_attachments(vars(args))

    print "Done."