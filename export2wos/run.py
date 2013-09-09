from datetime import datetime
import os

import tools
import config
from lxml import etree

# Setup a connection to SciELO Network Collection
coll = tools.get_collection(config.MONGODB_HOST)
now = datetime.now().isoformat()[0:10]
remove_origin = False
index_issn = 0

# Syncing XML status
print "Loading keepinto.txt ISSN's file from FTP controller directory"
tools.get_kee_into_file_from_ftp(ftp_host=config.FTP_HOST,
                                 user=config.FTP_USER,
                                 passwd=config.FTP_PASSWD)
issns = tools.load_journals_list(journals_file='controller/keepinto.txt')

# Syncing XML status
print "Syncing XML's status according to WoS validated files"
tools.get_sync_file_from_ftp(ftp_host=config.FTP_HOST,
                                user=config.FTP_USER,
                                passwd=config.FTP_PASSWD)
tools.sync_validated_xml(coll)

# Syncing XML status
print "Creating file with a list of documents to be removed from WoS"
tools.get_take_off_files_from_ftp(ftp_host=config.FTP_HOST,
                                user=config.FTP_USER,
                                passwd=config.FTP_PASSWD,
                                remove_origin=remove_origin)
tools.load_pids_list_to_be_removed(coll)
tools.send_take_off_files_to_ftp(ftp_host=config.FTP_HOST,
                            user=config.FTP_USER,
                            passwd=config.FTP_PASSWD,
                            remove_origin=remove_origin)

# Loading XML files
for issn in issns:
    index_issn = index_issn + 1

    documents = tools.not_send(coll, issn, publication_year=2002)

    if documents.count() == 0:
        continue

    print "validating {0} xml's for {1}".format(documents.count(), issn)
    print "Loading documents to be validated"

    if not os.path.exists('tmp/xml'):
        os.makedirs('tmp/xml')

    xml_file_name = "tmp/xml/SciELO_{0}_{1}.xml".format(now, issn)

    xml = ''
    xmlr = ''
    if not os.path.exists(xml_file_name):
        index_document = 0
        for document in documents:
            index_document = index_document + 1
            xml = tools.validate_xml(coll, document['code'], issn, api_host=config.MONGODB_HOST)
            if xml:
                parser = etree.XMLParser(remove_blank_text=True)
                root = etree.fromstring(xml, parser)
                xmlr = xmlr + etree.tostring(root.getchildren()[0])

        if xml:
            xml_file = open(xml_file_name, 'w')
            xml_file.write('<articles xmlns:xlink="http://www.w3.org/1999/xlink" '\
                           'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '\
                           'xsi:noNamespaceSchemaLocation="ThomsonReuters_publishing_1.06.xsd" '\
                           'dtd-version="1.06">')
            xml_file.write(xmlr)
            xml_file.write("</articles>")
            xml_file.close()

    else:
        print "File {0} already exists".format(xml_file_name)

#zipping files
files = os.listdir('tmp/xml')
zipped_file_name = tools.packing_zip(files)

#sending to ftp.scielo.br
tools.send_to_ftp(zipped_file_name,
                        ftp_host=config.FTP_HOST,
                        user=config.FTP_USER,
                        passwd=config.FTP_PASSWD)
