# -*- coding:utf-8 -*-
import urllib2
from xml.dom import minidom
from xml.parsers import expat
import logging


from nasaQuery import NASAQuery, NASAQueryException
import NASAparserconfig


class NASAQueryMercury(NASAQuery):

    """ NASAQuery class sets all the parameters needed for the query.
    Ables to perform the query and to return the results.
    NASAQueryMercury class specific for the mercury target

    Available ihid, and iid set in the NASAparserconfig

    Mandatory Attributes:
      ihid (str): ID
      iid (str): instrument ID
    """

    def __init__(self, ihid=None, iid=None, **parameters):
        """
        Defines mandatory parameters for the observation
        :param ihid: ihid (ID) of the observation
        :param iid: iid (instrument ID) of the observation
        """

        super(NASAQuery, self).__init__()
        self.target = 'mercury'


    def fetchImageFiles(self, pt, iid):

        """
        Open the connection to the NASA Rest interface and  to find all the
        files to download.
        A file is indentified by the following sequence:
        <type_of_file><ID>_<freq>_<file_version>.<type of the file>
        e.g is CN0266147010M_IF_4.IMG

        Return:

          a dictionary with metadata information and files url.
          in case of analysis of the geometry xml, only the information regarding
          the file_path is saved

        """

        info_files = {}
        files = None
        try:
            xmlNASA = urllib2.urlopen(self.composeURL(pt))
            xmldoc = minidom.parseString(xmlNASA.read())
            products = xmldoc.getElementsByTagName('Product')
            img_type = NASAparserconfig.configurations_mercury[iid]['IMG_TYPE']

            for a_tag in products:

                pdsid = self.read_nodelist(a_tag.getElementsByTagName('pdsid'))
                observation_id = pdsid[2:pdsid.find('_')]
                type_of_file = pdsid[pdsid.find('_')+1:-2]

                metadata = self.readMetadata(a_tag)

                if img_type == type_of_file:
                        files = self.read_nodelist(a_tag.getElementsByTagName('LabelURL'))
                        info_files.setdefault(observation_id, {}).update({'metadata': metadata,
                                                                          'files': files})

            #no result: two options
            #1- NASA page returns error
            #2- query didn't produce output
            if not files:
                #check if there was an error
                error = xmldoc.getElementsByTagName('Error')
                if error:
                    logging.critical("Error retrieving data for URL %s: \n" % self.composeURL(pt) +
                                     self.read_nodelist(error))
                else:
                    logging.critical("Query didn't produce any files. Please check parameters")
                raise NASAQueryException

        except urllib2.URLError as e:
            logging.critical(e)
        except expat.ExpatError as e:
            logging.critical(e)

        return info_files


    def fetchGeometriesFiles(self, pt, result):

        """
        TODO

        """

        try:
            xmlNASA = urllib2.urlopen(self.composeURL(pt))
            xmldoc = minidom.parseString(xmlNASA.read())
            products = xmldoc.getElementsByTagName('Product')

            for a_tag in products:
                geometry_files = []
                pdsid = self.read_nodelist(a_tag.getElementsByTagName('pdsid'))
                observation_id = pdsid[2:pdsid.find('_')]

                if observation_id in result:
                    geometry_files.append(self.read_nodelist(a_tag.getElementsByTagName('LabelURL')))
                    result[observation_id]['geometry_files'] = geometry_files
        except urllib2.URLError as e:
            logging.critical(e)
        except expat.ExpatError as e:
            logging.critical(e)

        return result

    def combineData(self, iid):
        """
        Call the fetch data for all the composed URLs
        fetch all information and associate the files to a unique ID
        Return:
           Dictionary key -> observation ID
                      values -> associate files
        """
        result = {}

        try:

           result = self.fetchImageFiles(NASAparserconfig.mercury_files_pt, iid)
           #now fetchng the associate geometries
           result = self.fetchGeometriesFiles(NASAparserconfig.mercury_geometry_pt, result)

        except NASAQueryException as e:
            logging.critical(e)

        return result

def add_required_arguments(parser):
    """
    set specific  parameters to the command line parser
    :param parser:
    :return:
    """

    requiredNamed = parser.add_argument_group('required  arguments')
    requiredNamed.add_argument('--ihid', dest='ihid', help="instrument host ID", choices=NASAparserconfig.ihid_mercury,
                               required=True)
    requiredNamed.add_argument('--iid', dest='iid', help="instrument  ID", choices=NASAparserconfig.iid_mercury,
                               required=True)


def main(parser):

     #creates the NASAQueryMercury obj
    nq = NASAQueryMercury()
    # Parse the arguments and directly load in the NASAQueryMercury namespace
    args = parser.parse_args(namespace=nq)
    #we will use this only internally to know what type of query to perform
    iid = nq.iid
    #change the iid accordingly with the configuration file
    nq.iid = NASAparserconfig.configurations_mercury[iid]['iid']

    #setup the logging
    log_format = "%(message)s"
    if args.log:
        logging.basicConfig(filename=args.log, filemode='w',
                            format=log_format, level=logging.INFO)
    else:
        logging.basicConfig(format=log_format, level=logging.INFO)

    info_files = nq.combineData(iid)
    nq.print_info(info_files, logging)


if __name__ == "__main__":

    parser = NASAparserconfig.argumentParser('Matisse Nasa query for the Mercury target')
    add_required_arguments(parser)
    main(parser)



